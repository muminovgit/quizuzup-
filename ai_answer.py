"""Best-effort correct-answer suggestions for questions whose source file
had no reliable marker (see flexible_parser.py's "pending" results).

Suggestions are never saved directly -- the uploader reviews and can
correct them before the quiz is created (see bot.py's QuizUpload.confirming_ai
state). This keeps a wrong AI guess from silently becoming the answer key
for a paid quiz.
"""

import json
import logging

import aiohttp

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2026-10-21"
MODEL = "claude-haiku-5-5"
BATCH_SIZE = 40
LETTERS = "ABCD"


class AIUnavailable(Exception):
    pass


async def suggest_answers(pending: list[dict]) -> dict[int, int]:
    """pending[i] has "question" and "options" (list[str], 2-4 entries).

    Returns {i: correct_option_index} only for the questions the model
    answered with a valid letter -- callers should treat a missing index
    as "AI couldn't tell either" and fall back to manual review.
    """
    if not ANTHROPIC_API_KEY:
        raise AIUnavailable("ANTHROPIC_API_KEY sozlanmagan.")
    if not pending:
        return {}

    results: dict[int, int] = {}
    async with aiohttp.ClientSession() as session:
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start : start + BATCH_SIZE]
            results.update(await _ask_batch(session, batch, start))
    return results


async def _ask_batch(session: aiohttp.ClientSession, batch: list[dict], offset: int) -> dict[int, int]:
    blocks = []
    for i, q in enumerate(batch):
        opts = "\n".join(f"{LETTERS[j]}) {opt}" for j, opt in enumerate(q["options"]))
        blocks.append(f"{i}. {q['question']}\n{opts}")

    prompt = (
        "Quyida test savollari berilgan, har birida bir nechta variant bor. "
        "Har bir savol uchun eng to'g'ri javobni tanla.\n\n"
        + "\n\n".join(blocks)
        + "\n\nFaqat JSON obyekt qaytar, boshqa hech qanday matn yozma. "
        'Format: {"0": "B", "1": "A", ...} -- kalit yuqoridagi savol raqami, '
        "qiymat to'g'ri variant harfi (A/B/C yoki D)."
    )
    payload = {
        "model": MODEL,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    try:
        async with session.post(
            API_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=90)
        ) as resp:
            data = await resp.json()
    except Exception:
        logger.warning("AI answer suggestion request failed", exc_info=True)
        return {}

    content = data.get("content")
    if not content:
        logger.warning("AI answer suggestion error response: %s", data)
        return {}

    text = "".join(block.get("text", "") for block in content if block.get("type") == "text")
    try:
        start_idx = text.index("{")
        end_idx = text.rindex("}") + 1
        parsed = json.loads(text[start_idx:end_idx])
    except (ValueError, json.JSONDecodeError):
        logger.warning("Could not parse AI answer JSON: %r", text)
        return {}

    out: dict[int, int] = {}
    for key, letter in parsed.items():
        try:
            local_idx = int(key)
        except (TypeError, ValueError):
            continue
        if not (0 <= local_idx < len(batch)):
            continue
        letter = str(letter).strip().upper()
        if letter not in LETTERS:
            continue
        option_idx = LETTERS.index(letter)
        if option_idx >= len(batch[local_idx]["options"]):
            continue
        out[offset + local_idx] = option_idx
    return out
