"""Telegram Quiz Bot -- aiogram 3.x

Admins upload an .xlsx file to create a quiz, quizzes persist in SQLite,
answers are tracked via poll_answer updates for a per-chat leaderboard,
and a Telegram Stars payment unlocks the unlimited "Pro" tier.
"""

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PollAnswer,
    PreCheckoutQuery,
)

import db
from auth import derive_password, hash_password
from config import (
    ADMIN_CONTACT_USERNAME,
    ADMIN_IDS,
    BOT_TOKEN,
    FREE_MAX_QUESTIONS,
    FREE_MAX_QUIZZES,
    POLL_OPEN_PERIOD,
    PRO_UPGRADE_STARS,
    WEB_CREDENTIAL_SECRET,
    WEB_URL,
)
from excel_parser import ExcelParseError, parse_quiz_excel
from translations import LANGUAGE_NAMES, t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

BASE_DIR = Path(__file__).parent
TEMPLATE_PATH = BASE_DIR / "quiz_template.xlsx"

MISS_STREAK_TO_PAUSE = 4


class QuizUpload(StatesGroup):
    waiting_file = State()
    waiting_name = State()


class QuizRunner:
    """Runtime state for one quiz session running in a chat (pausable)."""

    def __init__(self, chat_id: int, session_id: int, quiz_name: str, questions: list[dict], owner_id: int, lang: str):
        self.chat_id = chat_id
        self.session_id = session_id
        self.quiz_name = quiz_name
        self.questions = questions
        self.owner_id = owner_id
        self.lang = lang
        self.index = 0
        self.miss_streak = 0
        self.running = asyncio.Event()
        self.running.set()
        self.stopped = False


RUNNING_SESSIONS: dict[int, QuizRunner] = {}
BOT_USERNAME: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TG_QUESTION_LIMIT = 300
TG_OPTION_LIMIT = 100
TG_EXPLANATION_LIMIT = 200


def _truncate(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _build_poll_options(question: dict) -> tuple[list[str], int]:
    """Returns (options, correct_index) filtering out empty C/D slots."""
    raw_options = [
        question["option_a"],
        question["option_b"],
        question["option_c"],
        question["option_d"],
    ]
    options: list[str] = []
    correct_index = 0
    for i, opt in enumerate(raw_options):
        if opt:
            if i == question["correct_option"]:
                correct_index = len(options)
            options.append(_truncate(opt, TG_OPTION_LIMIT))
    return options, correct_index


async def _lang(user_id: int) -> str:
    return await db.get_language(user_id) or "uz"


def _not_a_command(message: Message) -> bool:
    """True unless the message text looks like a /command.

    Used to keep FSM catch-all handlers from swallowing commands such as
    /cancel or /upgrade while an upload is in progress.
    """
    return not (message.text and message.text.startswith("/"))


async def _require_owner(message: Message, quiz: dict | None, lang: str) -> bool:
    if quiz is None:
        await message.answer(t("quiz_not_found", lang))
        return False
    if quiz["owner_id"] != message.from_user.id:
        await message.answer(t("not_owner_start", lang))
        return False
    return True


def _quiz_list_keyboard(quizzes: list[dict], action: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{q['name']} ({q['question_count']}q)",
                callback_data=f"{action}:{q['quiz_id']}",
            )
        ]
        for q in quizzes
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _language_keyboard(mode: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=name, callback_data=f"setlang:{code}:{mode}")]
        for code, name in LANGUAGE_NAMES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _resume_keyboard(chat_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("resume_button", lang), callback_data=f"resume:{chat_id}")]]
    )


def _stop_keyboard(chat_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("stop_button", lang), callback_data=f"stopquiz:{chat_id}")]]
    )


def _add_to_group_keyboard(lang: str) -> InlineKeyboardMarkup | None:
    if not BOT_USERNAME:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("add_to_group", lang), url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
        ]
    )


async def _send_welcome(bot: Bot, chat_id: int, lang: str) -> None:
    await bot.send_message(
        chat_id,
        t("welcome", lang, max_quizzes=FREE_MAX_QUIZZES, max_questions=FREE_MAX_QUESTIONS),
        reply_markup=_add_to_group_keyboard(lang),
    )
    if TEMPLATE_PATH.exists():
        await bot.send_document(
            chat_id,
            FSInputFile(TEMPLATE_PATH),
            caption=t("template_caption", lang),
        )


async def _pause_quiz(bot: Bot, runner: QuizRunner, message_key: str, **kwargs: object) -> None:
    runner.running.clear()
    runner.miss_streak = 0
    await bot.send_message(
        runner.chat_id,
        t(message_key, runner.lang, **kwargs),
        reply_markup=_resume_keyboard(runner.chat_id, runner.lang),
    )


async def _issue_web_login(bot: Bot, user_id: int, lang: str) -> None:
    """(Re)issues web-portal credentials for a Pro user and DMs them the login.

    Both the username and password are derived deterministically from the
    user_id (and a server secret), so calling this again -- another
    /grantpro, a repeat /webportal, a second Stars payment -- always
    reproduces the exact same login. Nothing is invalidated or rotated.
    """
    if not WEB_URL:
        return

    login = f"user{user_id}"
    password = derive_password(WEB_CREDENTIAL_SECRET, user_id)
    await db.set_web_credentials(user_id, login, hash_password(password))

    try:
        await bot.send_message(
            user_id,
            t("web_login_issued", lang, url=WEB_URL, username=login, password=password),
        )
    except Exception:
        logger.warning("Could not DM web login to user %s (they may not have started the bot)", user_id)


# ---------------------------------------------------------------------------
# Language selection
# ---------------------------------------------------------------------------


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    lang = await db.get_language(message.from_user.id)
    if lang is None:
        await message.answer(t("choose_language", "en"), reply_markup=_language_keyboard("start"))
        return
    await _send_welcome(message.bot, message.chat.id, lang)


@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    lang = await _lang(message.from_user.id)
    await message.answer(t("choose_language", lang), reply_markup=_language_keyboard("switch"))


@router.callback_query(F.data.startswith("setlang:"))
async def cb_set_language(callback: CallbackQuery) -> None:
    _, code, mode = callback.data.split(":", 2)
    await db.set_language(callback.from_user.id, code)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    if mode == "start":
        await _send_welcome(callback.bot, callback.message.chat.id, code)
    else:
        await callback.message.answer(t("language_changed", code))


# ---------------------------------------------------------------------------
# /newquiz upload flow
# ---------------------------------------------------------------------------


@router.message(Command("newquiz"))
async def cmd_newquiz(message: Message, state: FSMContext) -> None:
    await db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    lang = await _lang(message.from_user.id)

    if not await db.is_premium(message.from_user.id):
        existing = await db.count_quizzes_by_owner(message.from_user.id)
        if existing >= FREE_MAX_QUIZZES:
            await message.answer(t("limit_quizzes", lang, max_quizzes=FREE_MAX_QUIZZES))
            return

    await state.set_state(QuizUpload.waiting_file)
    await message.answer(t("send_file", lang))


@router.message(QuizUpload.waiting_file, F.document)
async def receive_quiz_file(message: Message, state: FSMContext, bot: Bot) -> None:
    lang = await _lang(message.from_user.id)
    document = message.document
    if not document.file_name.lower().endswith(".xlsx"):
        await message.answer(t("not_xlsx", lang))
        return

    file = await bot.get_file(document.file_id)
    file_bytes_io = await bot.download_file(file.file_path)
    file_bytes = file_bytes_io.read()

    try:
        questions = parse_quiz_excel(file_bytes)
    except ExcelParseError as exc:
        await message.answer(t("parse_error", lang, error=str(exc)))
        return

    if not await db.is_premium(message.from_user.id) and len(questions) > FREE_MAX_QUESTIONS:
        await message.answer(t("question_limit", lang, max_questions=FREE_MAX_QUESTIONS, got=len(questions)))
        return

    default_name = document.file_name.rsplit(".", 1)[0][:50]
    await state.update_data(questions=questions, default_name=default_name)
    await state.set_state(QuizUpload.waiting_name)
    await message.answer(t("parsed_ok", lang, count=len(questions), default_name=default_name))


@router.message(QuizUpload.waiting_file, _not_a_command)
async def receive_quiz_file_invalid(message: Message) -> None:
    lang = await _lang(message.from_user.id)
    await message.answer(t("send_valid_file", lang))


@router.message(QuizUpload.waiting_name, Command("skip"))
async def skip_quiz_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await _save_quiz(message, state, data["default_name"], data["questions"])


@router.message(QuizUpload.waiting_name, F.text, _not_a_command)
async def receive_quiz_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()[:50]
    if not name:
        await message.answer(t("send_file", await _lang(message.from_user.id)))
        return
    data = await state.get_data()
    await _save_quiz(message, state, name, data["questions"])


async def _save_quiz(message: Message, state: FSMContext, name: str, questions: list[dict]) -> None:
    lang = await _lang(message.from_user.id)
    owner_id = message.from_user.id
    if await db.quiz_name_exists(owner_id, name):
        name = f"{name} ({len(questions)}q)"

    await db.create_quiz(owner_id, name, questions)
    await state.clear()
    await message.answer(t("quiz_saved", lang, name=name, count=len(questions)))


@router.message(Command("cancel"), QuizUpload.waiting_file)
@router.message(Command("cancel"), QuizUpload.waiting_name)
async def cancel_upload(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t("cancelled", await _lang(message.from_user.id)))


# ---------------------------------------------------------------------------
# /myquizzes
# ---------------------------------------------------------------------------


@router.message(Command("myquizzes"))
async def cmd_myquizzes(message: Message) -> None:
    lang = await _lang(message.from_user.id)
    quizzes = await db.list_quizzes_by_owner(message.from_user.id)
    if not quizzes:
        await message.answer(t("myquizzes_empty", lang))
        return

    suffix = t("questions_suffix", lang)
    lines = [f"• {q['name']} — {q['question_count']} {suffix}" for q in quizzes]
    await message.answer(t("myquizzes_header", lang) + "\n" + "\n".join(lines))


# ---------------------------------------------------------------------------
# /startquiz
# ---------------------------------------------------------------------------


@router.message(Command("startquiz"))
async def cmd_startquiz(message: Message, command: CommandObject, bot: Bot) -> None:
    lang = await _lang(message.from_user.id)

    if message.chat.id in RUNNING_SESSIONS:
        await message.answer(t("quiz_already_running", lang))
        return

    if command.args:
        quiz = await db.get_quiz_by_name(message.from_user.id, command.args.strip())
        if not await _require_owner(message, quiz, lang):
            return
        await _run_quiz(bot, message.chat.id, message.from_user.id, quiz, lang)
        return

    quizzes = await db.list_quizzes_by_owner(message.from_user.id)
    if not quizzes:
        await message.answer(t("myquizzes_empty", lang))
        return
    await message.answer(t("pick_quiz_start", lang), reply_markup=_quiz_list_keyboard(quizzes, "startquiz"))


@router.callback_query(F.data.startswith("startquiz:"))
async def cb_startquiz(callback: CallbackQuery, bot: Bot) -> None:
    lang = await _lang(callback.from_user.id)
    if callback.message.chat.id in RUNNING_SESSIONS:
        await callback.answer(t("quiz_already_running", lang), show_alert=True)
        return

    quiz_id = int(callback.data.split(":", 1)[1])
    quiz = await db.get_quiz_by_id(quiz_id)
    if quiz is None or quiz["owner_id"] != callback.from_user.id:
        await callback.answer(t("not_owner_start", lang), show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await _run_quiz(bot, callback.message.chat.id, callback.from_user.id, quiz, lang)


async def _run_quiz(bot: Bot, chat_id: int, started_by: int, quiz: dict, lang: str) -> None:
    questions = await db.get_questions(quiz["quiz_id"])
    if not questions:
        await bot.send_message(chat_id, t("quiz_no_questions", lang))
        return

    session_id = await db.create_session(quiz["quiz_id"], chat_id, started_by)
    runner = QuizRunner(chat_id, session_id, quiz["name"], questions, started_by, lang)
    RUNNING_SESSIONS[chat_id] = runner

    await bot.send_message(
        chat_id,
        t("quiz_starting", lang, name=quiz["name"], count=len(questions)),
        reply_markup=_stop_keyboard(chat_id, lang),
    )
    try:
        await bot.send_dice(chat_id, emoji="🎯")
    except Exception:
        logger.debug("send_dice flair failed", exc_info=True)

    asyncio.create_task(_run_quiz_loop(bot, runner))


async def _run_quiz_loop(bot: Bot, runner: QuizRunner) -> None:
    # Guarantee RUNNING_SESSIONS is always cleaned up, even on an unexpected
    # crash -- otherwise the chat would get permanently stuck refusing new
    # /startquiz calls with "a quiz is already running".
    try:
        while runner.index < len(runner.questions):
            await runner.running.wait()
            if runner.stopped:
                return

            question = runner.questions[runner.index]
            options, correct_index = _build_poll_options(question)
            try:
                poll_message = await bot.send_poll(
                    chat_id=runner.chat_id,
                    question=_truncate(question["question_text"], TG_QUESTION_LIMIT),
                    options=options,
                    type="quiz",
                    correct_option_id=correct_index,
                    is_anonymous=False,
                    open_period=POLL_OPEN_PERIOD,
                    explanation=_truncate(question["explanation"], TG_EXPLANATION_LIMIT),
                )
            except Exception:
                logger.exception("Failed to send poll for question %s", question["question_id"])
                runner.index += 1
                continue

            await db.save_poll_map(
                poll_id=poll_message.poll.id,
                session_id=runner.session_id,
                question_id=question["question_id"],
                correct_option=correct_index,
                chat_id=runner.chat_id,
            )
            runner.index += 1

            await asyncio.sleep(POLL_OPEN_PERIOD + 2)
            if runner.stopped:
                return

            if await db.poll_has_answers(poll_message.poll.id):
                runner.miss_streak = 0
            else:
                runner.miss_streak += 1
                if runner.miss_streak >= MISS_STREAK_TO_PAUSE and runner.index < len(runner.questions):
                    streak = runner.miss_streak
                    await _pause_quiz(bot, runner, "quiz_paused_auto", streak=streak)

        await db.finish_session(runner.session_id)
        try:
            await bot.send_dice(runner.chat_id, emoji="🎉")
        except Exception:
            pass
        await bot.send_message(runner.chat_id, t("quiz_finished", runner.lang))
    except Exception:
        logger.exception("Quiz loop crashed for chat %s", runner.chat_id)
        try:
            await bot.send_message(runner.chat_id, t("quiz_error", runner.lang))
        except Exception:
            pass
    finally:
        RUNNING_SESSIONS.pop(runner.chat_id, None)


# ---------------------------------------------------------------------------
# /stop and resume
# ---------------------------------------------------------------------------


@router.message(Command("stop"))
async def cmd_stop(message: Message, bot: Bot) -> None:
    lang = await _lang(message.from_user.id)
    runner = RUNNING_SESSIONS.get(message.chat.id)
    if runner is None:
        await message.answer(t("no_active_quiz", lang))
        return
    if runner.owner_id != message.from_user.id:
        await message.answer(t("not_owner_stop", lang))
        return

    await _pause_quiz(bot, runner, "quiz_paused_manual")


@router.callback_query(F.data.startswith("stopquiz:"))
async def cb_stopquiz(callback: CallbackQuery, bot: Bot) -> None:
    lang = await _lang(callback.from_user.id)
    chat_id = int(callback.data.split(":", 1)[1])
    runner = RUNNING_SESSIONS.get(chat_id)
    if runner is None:
        await callback.answer(t("no_active_quiz", lang), show_alert=True)
        return
    if runner.owner_id != callback.from_user.id:
        await callback.answer(t("not_owner_stop", lang), show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await _pause_quiz(bot, runner, "quiz_paused_manual")


@router.callback_query(F.data.startswith("resume:"))
async def cb_resume(callback: CallbackQuery) -> None:
    lang = await _lang(callback.from_user.id)
    chat_id = int(callback.data.split(":", 1)[1])
    runner = RUNNING_SESSIONS.get(chat_id)
    if runner is None:
        await callback.answer(t("no_active_quiz", lang), show_alert=True)
        return
    if runner.owner_id != callback.from_user.id:
        await callback.answer(t("not_owner_resume", lang), show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    runner.miss_streak = 0
    runner.running.set()
    await callback.message.answer(t("quiz_resumed", runner.lang))


# ---------------------------------------------------------------------------
# /deletequiz
# ---------------------------------------------------------------------------


@router.message(Command("deletequiz"))
async def cmd_deletequiz(message: Message, command: CommandObject) -> None:
    lang = await _lang(message.from_user.id)

    if command.args:
        quiz = await db.get_quiz_by_name(message.from_user.id, command.args.strip())
        if quiz is None:
            await message.answer(t("quiz_not_found", lang))
            return
        if quiz["owner_id"] != message.from_user.id:
            await message.answer(t("not_owner_delete", lang))
            return
        await db.delete_quiz(quiz["quiz_id"])
        await message.answer(t("deleted_quiz", lang, name=quiz["name"]))
        return

    quizzes = await db.list_quizzes_by_owner(message.from_user.id)
    if not quizzes:
        await message.answer(t("myquizzes_empty", lang))
        return
    await message.answer(t("pick_quiz_delete", lang), reply_markup=_quiz_list_keyboard(quizzes, "deletequiz"))


@router.callback_query(F.data.startswith("deletequiz:"))
async def cb_deletequiz(callback: CallbackQuery) -> None:
    lang = await _lang(callback.from_user.id)
    quiz_id = int(callback.data.split(":", 1)[1])
    quiz = await db.get_quiz_by_id(quiz_id)
    if quiz is None or quiz["owner_id"] != callback.from_user.id:
        await callback.answer(t("not_owner_delete", lang), show_alert=True)
        return
    await db.delete_quiz(quiz_id)
    await callback.answer()
    await callback.message.edit_text(t("deleted_quiz", lang, name=quiz["name"]))


# ---------------------------------------------------------------------------
# /leaderboard
# ---------------------------------------------------------------------------


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message) -> None:
    lang = await _lang(message.from_user.id)
    rows = await db.get_leaderboard(message.chat.id)
    if not rows:
        await message.answer(t("leaderboard_empty", lang))
        return

    medals = ["🥇", "🥈", "🥉"]
    correct_word = t("correct_suffix", lang)
    lines = []
    for i, row in enumerate(rows):
        prefix = medals[i] if i < len(medals) else f"{i + 1}."
        name = row["username"] or f"user {row['user_id']}"
        lines.append(f"{prefix} {name} — {row['correct_count']}/{row['total_answered']} {correct_word}")

    await message.answer(t("leaderboard_header", lang) + "\n" + "\n".join(lines))


# ---------------------------------------------------------------------------
# Telegram Stars payment (/upgrade)
# ---------------------------------------------------------------------------


@router.message(Command("upgrade"))
async def cmd_upgrade(message: Message, bot: Bot) -> None:
    lang = await _lang(message.from_user.id)
    if await db.is_premium(message.from_user.id):
        await message.answer(t("already_pro", lang))
        return

    await bot.send_invoice(
        chat_id=message.chat.id,
        title=t("pro_title", lang),
        description=t("pro_description", lang, stars=PRO_UPGRADE_STARS),
        payload=f"pro_upgrade:{message.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label=t("pro_title", lang), amount=PRO_UPGRADE_STARS)],
        provider_token="",
    )

    if ADMIN_CONTACT_USERNAME:
        await message.answer(t("upgrade_alt_payment", lang, admin=ADMIN_CONTACT_USERNAME))


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot) -> None:
    lang = await _lang(message.from_user.id)
    payment = message.successful_payment
    await db.set_premium(message.from_user.id)
    await db.record_payment(
        user_id=message.from_user.id,
        stars_amount=payment.total_amount,
        telegram_charge_id=payment.telegram_payment_charge_id,
    )
    await message.answer(t("payment_success", lang))
    await _issue_web_login(bot, message.from_user.id, lang)


# ---------------------------------------------------------------------------
# Manual Pro activation for out-of-band payment (cash, Click, Payme, etc.)
# ---------------------------------------------------------------------------


@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    lang = await _lang(message.from_user.id)
    await message.answer(t("myid_reply", lang, id=message.from_user.id))


async def _resolve_target_user(message: Message, command: CommandObject) -> tuple[int | None, str | None]:
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        return target.id, target.username or target.first_name
    if command.args:
        arg = command.args.strip()
        if arg.startswith("@"):
            row = await db.get_user_by_username(arg[1:])
            if row:
                return row["user_id"], row["username"] or str(row["user_id"])
            return None, None
        if arg.lstrip("-").isdigit():
            return int(arg), arg
    return None, None


@router.message(Command("grantpro"))
async def cmd_grantpro(message: Message, command: CommandObject, bot: Bot) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    lang = await _lang(message.from_user.id)
    user_id, label = await _resolve_target_user(message, command)
    if user_id is None:
        await message.answer(t("grantpro_usage", lang))
        return
    await db.set_premium(user_id)
    await message.answer(t("grantpro_done", lang, target=label or user_id))
    await _issue_web_login(bot, user_id, await _lang(user_id))


@router.message(Command("webportal"))
async def cmd_webportal(message: Message, bot: Bot) -> None:
    lang = await _lang(message.from_user.id)
    if not await db.is_premium(message.from_user.id):
        await message.answer(t("webportal_not_premium", lang))
        return
    await _issue_web_login(bot, message.from_user.id, lang)


@router.message(Command("revokepro"))
async def cmd_revokepro(message: Message, command: CommandObject) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    lang = await _lang(message.from_user.id)
    user_id, label = await _resolve_target_user(message, command)
    if user_id is None:
        await message.answer(t("grantpro_usage", lang))
        return
    await db.revoke_premium(user_id)
    await message.answer(t("revokepro_done", lang, target=label or user_id))


@router.message(F.document)
async def receive_stray_document(message: Message) -> None:
    """A file sent without first starting /newquiz -- previously silently
    ignored (no handler matched), which looked like the bot was broken."""
    lang = await _lang(message.from_user.id)
    await message.answer(t("stray_document", lang))


# ---------------------------------------------------------------------------
# Leaderboard tracking via poll_answer updates
# ---------------------------------------------------------------------------


@router.poll_answer()
async def on_poll_answer(poll_answer: PollAnswer) -> None:
    mapping = await db.get_poll_map(poll_answer.poll_id)
    if mapping is None:
        return
    if not poll_answer.option_ids:
        return

    is_correct = poll_answer.option_ids[0] == mapping["correct_option"]
    user = poll_answer.user
    username = user.username or user.first_name or str(user.id)
    await db.record_answer(
        poll_id=poll_answer.poll_id,
        session_id=mapping["session_id"],
        chat_id=mapping["chat_id"],
        user_id=user.id,
        username=username,
        is_correct=is_correct,
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

    await db.init_db()

    bot = Bot(token=BOT_TOKEN)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)

    global BOT_USERNAME
    me = await bot.get_me()
    BOT_USERNAME = me.username

    # False, not True: a brief restart (e.g. a Render deploy) shouldn't
    # silently drop messages people sent while the bot was momentarily down.
    await bot.delete_webhook(drop_pending_updates=False)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
