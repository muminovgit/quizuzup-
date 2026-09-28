"""Telegram Quiz Bot -- aiogram 3.x

Admins upload an .xlsx file to create a quiz, quizzes persist in SQLite,
answers are tracked via poll_answer updates for a per-chat leaderboard,
and a Telegram Stars payment unlocks the unlimited "Pro" tier.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PollAnswer,
    PreCheckoutQuery,
)

import db
from config import BOT_TOKEN, FREE_MAX_QUESTIONS, FREE_MAX_QUIZZES, POLL_OPEN_PERIOD, PRO_UPGRADE_STARS
from excel_parser import ExcelParseError, parse_quiz_excel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


class QuizUpload(StatesGroup):
    waiting_file = State()
    waiting_name = State()


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


async def _require_owner(message: Message, quiz: dict | None) -> bool:
    if quiz is None:
        await message.answer("I couldn't find a quiz with that name. Check /myquizzes.")
        return False
    if quiz["owner_id"] != message.from_user.id:
        await message.answer("Only the admin who uploaded this quiz can do that.")
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


# ---------------------------------------------------------------------------
# Basic commands
# ---------------------------------------------------------------------------


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        "👋 Welcome to Quiz Bot!\n\n"
        "/newquiz — upload an .xlsx file to create a quiz\n"
        "/myquizzes — list your saved quizzes\n"
        "/startquiz [name] — run a saved quiz in this chat\n"
        "/deletequiz [name] — remove one of your quizzes\n"
        "/leaderboard — top scorers in this chat\n"
        "/upgrade — go Pro with Telegram Stars (unlimited quizzes & questions)\n\n"
        f"Free tier: up to {FREE_MAX_QUIZZES} quizzes, {FREE_MAX_QUESTIONS} questions each."
    )


# ---------------------------------------------------------------------------
# /newquiz upload flow
# ---------------------------------------------------------------------------


@router.message(Command("newquiz"))
async def cmd_newquiz(message: Message, state: FSMContext) -> None:
    await db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.first_name)

    if not await db.is_premium(message.from_user.id):
        existing = await db.count_quizzes_by_owner(message.from_user.id)
        if existing >= FREE_MAX_QUIZZES:
            await message.answer(
                f"You've reached the free tier limit of {FREE_MAX_QUIZZES} quizzes.\n"
                "Use /deletequiz to remove one, or /upgrade to go Pro for unlimited quizzes."
            )
            return

    await state.set_state(QuizUpload.waiting_file)
    await message.answer("Send me the .xlsx file for your new quiz (use the quiz_template.xlsx format).")


@router.message(QuizUpload.waiting_file, F.document)
async def receive_quiz_file(message: Message, state: FSMContext, bot: Bot) -> None:
    document = message.document
    if not document.file_name.lower().endswith(".xlsx"):
        await message.answer("That doesn't look like an .xlsx file. Please send a valid Excel file.")
        return

    file = await bot.get_file(document.file_id)
    file_bytes_io = await bot.download_file(file.file_path)
    file_bytes = file_bytes_io.read()

    try:
        questions = parse_quiz_excel(file_bytes)
    except ExcelParseError as exc:
        await message.answer(f"⚠️ Couldn't parse that file: {exc}\nPlease fix it and send it again.")
        return

    if not await db.is_premium(message.from_user.id) and len(questions) > FREE_MAX_QUESTIONS:
        await message.answer(
            f"Free tier quizzes can have at most {FREE_MAX_QUESTIONS} questions "
            f"(this file has {len(questions)}). Trim it down or /upgrade to go Pro."
        )
        return

    default_name = document.file_name.rsplit(".", 1)[0][:50]
    await state.update_data(questions=questions, default_name=default_name)
    await state.set_state(QuizUpload.waiting_name)
    await message.answer(
        f"Parsed {len(questions)} questions ✅\n"
        f"Send a short name to save this quiz as, or send /skip to use \"{default_name}\"."
    )


@router.message(QuizUpload.waiting_file)
async def receive_quiz_file_invalid(message: Message) -> None:
    await message.answer("Please upload the .xlsx file as a document, or /cancel to stop.")


@router.message(QuizUpload.waiting_name, Command("skip"))
async def skip_quiz_name(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await _save_quiz(message, state, data["default_name"], data["questions"])


@router.message(QuizUpload.waiting_name, F.text)
async def receive_quiz_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()[:50]
    if not name:
        await message.answer("Please send a non-empty name.")
        return
    data = await state.get_data()
    await _save_quiz(message, state, name, data["questions"])


async def _save_quiz(message: Message, state: FSMContext, name: str, questions: list[dict]) -> None:
    owner_id = message.from_user.id
    if await db.quiz_name_exists(owner_id, name):
        name = f"{name} ({len(questions)}q)"

    quiz_id = await db.create_quiz(owner_id, name, questions)
    await state.clear()
    await message.answer(
        f"✅ Saved quiz \"{name}\" with {len(questions)} questions.\n"
        f"Run it with /startquiz {name}"
    )


@router.message(Command("cancel"), QuizUpload.waiting_file)
@router.message(Command("cancel"), QuizUpload.waiting_name)
async def cancel_upload(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Cancelled.")


# ---------------------------------------------------------------------------
# /myquizzes
# ---------------------------------------------------------------------------


@router.message(Command("myquizzes"))
async def cmd_myquizzes(message: Message) -> None:
    quizzes = await db.list_quizzes_by_owner(message.from_user.id)
    if not quizzes:
        await message.answer("You don't have any saved quizzes yet. Use /newquiz to create one.")
        return

    lines = [f"• {q['name']} — {q['question_count']} questions" for q in quizzes]
    await message.answer("Your quizzes:\n" + "\n".join(lines))


# ---------------------------------------------------------------------------
# /startquiz
# ---------------------------------------------------------------------------


@router.message(Command("startquiz"))
async def cmd_startquiz(message: Message, command: CommandObject, bot: Bot) -> None:
    if command.args:
        quiz = await db.get_quiz_by_name(message.from_user.id, command.args.strip())
        if not await _require_owner(message, quiz):
            return
        await _run_quiz(bot, message.chat.id, message.from_user.id, quiz)
        return

    quizzes = await db.list_quizzes_by_owner(message.from_user.id)
    if not quizzes:
        await message.answer("You don't have any saved quizzes yet. Use /newquiz to create one.")
        return
    await message.answer("Pick a quiz to start:", reply_markup=_quiz_list_keyboard(quizzes, "startquiz"))


@router.callback_query(F.data.startswith("startquiz:"))
async def cb_startquiz(callback: CallbackQuery, bot: Bot) -> None:
    quiz_id = int(callback.data.split(":", 1)[1])
    quiz = await db.get_quiz_by_id(quiz_id)
    if quiz is None or quiz["owner_id"] != callback.from_user.id:
        await callback.answer("Only the quiz owner can start it.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await _run_quiz(bot, callback.message.chat.id, callback.from_user.id, quiz)


async def _run_quiz(bot: Bot, chat_id: int, started_by: int, quiz: dict) -> None:
    questions = await db.get_questions(quiz["quiz_id"])
    if not questions:
        await bot.send_message(chat_id, "This quiz has no questions.")
        return

    session_id = await db.create_session(quiz["quiz_id"], chat_id, started_by)
    await bot.send_message(chat_id, f"🧠 Starting quiz: {quiz['name']} ({len(questions)} questions)")
    asyncio.create_task(_send_quiz_questions(bot, chat_id, session_id, questions))


async def _send_quiz_questions(bot: Bot, chat_id: int, session_id: int, questions: list[dict]) -> None:
    for question in questions:
        options, correct_index = _build_poll_options(question)
        try:
            poll_message = await bot.send_poll(
                chat_id=chat_id,
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
            continue

        await db.save_poll_map(
            poll_id=poll_message.poll.id,
            session_id=session_id,
            question_id=question["question_id"],
            correct_option=correct_index,
            chat_id=chat_id,
        )
        await asyncio.sleep(POLL_OPEN_PERIOD + 2)

    await db.finish_session(session_id)
    await bot.send_message(chat_id, "🏁 Quiz finished! Check /leaderboard for the top scorers.")


# ---------------------------------------------------------------------------
# /deletequiz
# ---------------------------------------------------------------------------


@router.message(Command("deletequiz"))
async def cmd_deletequiz(message: Message, command: CommandObject) -> None:
    if command.args:
        quiz = await db.get_quiz_by_name(message.from_user.id, command.args.strip())
        if not await _require_owner(message, quiz):
            return
        await db.delete_quiz(quiz["quiz_id"])
        await message.answer(f"🗑️ Deleted quiz \"{quiz['name']}\".")
        return

    quizzes = await db.list_quizzes_by_owner(message.from_user.id)
    if not quizzes:
        await message.answer("You don't have any saved quizzes yet.")
        return
    await message.answer(
        "Pick a quiz to delete:", reply_markup=_quiz_list_keyboard(quizzes, "deletequiz")
    )


@router.callback_query(F.data.startswith("deletequiz:"))
async def cb_deletequiz(callback: CallbackQuery) -> None:
    quiz_id = int(callback.data.split(":", 1)[1])
    quiz = await db.get_quiz_by_id(quiz_id)
    if quiz is None or quiz["owner_id"] != callback.from_user.id:
        await callback.answer("Only the quiz owner can delete it.", show_alert=True)
        return
    await db.delete_quiz(quiz_id)
    await callback.answer("Deleted.")
    await callback.message.edit_text(f"🗑️ Deleted quiz \"{quiz['name']}\".")


# ---------------------------------------------------------------------------
# /leaderboard
# ---------------------------------------------------------------------------


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: Message) -> None:
    rows = await db.get_leaderboard(message.chat.id)
    if not rows:
        await message.answer("No answers recorded in this chat yet. Run a quiz with /startquiz!")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, row in enumerate(rows):
        prefix = medals[i] if i < len(medals) else f"{i + 1}."
        name = row["username"] or f"user {row['user_id']}"
        lines.append(f"{prefix} {name} — {row['correct_count']}/{row['total_answered']} correct")

    await message.answer("🏆 Leaderboard\n" + "\n".join(lines))


# ---------------------------------------------------------------------------
# Telegram Stars payment (/upgrade)
# ---------------------------------------------------------------------------


@router.message(Command("upgrade"))
async def cmd_upgrade(message: Message, bot: Bot) -> None:
    if await db.is_premium(message.from_user.id):
        await message.answer("You're already on the Pro tier. Thanks for your support! 🌟")
        return

    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Quiz Bot Pro",
        description=f"Unlock unlimited quizzes and unlimited questions per quiz ({PRO_UPGRADE_STARS} Stars).",
        payload=f"pro_upgrade:{message.from_user.id}",
        currency="XTR",
        prices=[LabeledPrice(label="Quiz Bot Pro", amount=PRO_UPGRADE_STARS)],
        provider_token="",
    )


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message) -> None:
    payment = message.successful_payment
    await db.set_premium(message.from_user.id)
    await db.record_payment(
        user_id=message.from_user.id,
        stars_amount=payment.total_amount,
        telegram_charge_id=payment.telegram_payment_charge_id,
    )
    await message.answer("🌟 Payment received! You're now on the Pro tier — unlimited quizzes and questions.")


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

    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
