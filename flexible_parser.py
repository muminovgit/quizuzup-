"""Parses quiz files of (almost) any common format into question dicts.

The strict .xlsx template keeps going through excel_parser.py unchanged.
This module adds support for the other formats people actually share test
banks in: .csv (same columns as the .xlsx template, in any order), and
free-text formats (.docx, .txt, .pdf) using the two conventions most test
banks are written in:

  1. "+/-" marked options (very common for Uzbek test banks):
         1. Savol matni?
         +To'g'ri javob
         -Noto'g'ri javob
         -Noto'g'ri javob

  2. Lettered options with the correct one starred, or a separate
     "Javob: B" / "Answer: B" / "To'g'ri javob: B" line:
         1. Savol matni?
         A) Variant 1
         B) Variant 2*
         C) Variant 3
         D) Variant 4

Every path produces the same shape as excel_parser.parse_quiz_excel:
question, option_a..option_d (option_c/d may be None), correct_option
(0-3), explanation (or None).
"""

import csv
import io
import re

from excel_parser import ExcelParseError, parse_quiz_excel

SUPPORTED_EXTENSIONS = {"xlsx", "csv", "docx", "txt", "pdf"}

HEADER_SYNONYMS = {
    "question": {"question", "savol", "вопрос"},
    "option_a": {"option a", "optiona", "a", "variant a", "variant1", "variant 1", "javob a", "вариант a", "вариант1"},
    "option_b": {"option b", "optionb", "b", "variant b", "variant2", "variant 2", "javob b", "вариант b", "вариант2"},
    "option_c": {"option c", "optionc", "c", "variant c", "variant3", "variant 3", "javob c", "вариант c", "вариант3"},
    "option_d": {"option d", "optiond", "d", "variant d", "variant4", "variant 4", "javob d", "вариант d", "вариант4"},
    "correct_answer": {
        "correct answer", "correct", "javob", "to'g'ri javob", "togri javob",
        "answer", "правильный ответ", "ответ",
    },
    "explanation": {"explanation", "izoh", "объяснение", "комментарий"},
}

LETTER_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}
CYRILLIC_LETTER_MAP = {"А": "A", "Б": "B", "В": "C", "Г": "D", "а": "A", "б": "B", "в": "C", "г": "D"}

_NUMBERED_LINE_RE = re.compile(r"^\s*(\d{1,3})[.)]\s+", re.MULTILINE)
_PLUS_MINUS_RE = re.compile(r"^\s*([+\-−–])\s*(.+)$")
_LETTER_RE = re.compile(r"^\s*[(\[]?([A-DA-ZА-Да-г])[.)\]:\-]\s*(.+)$")
_ANSWER_LINE_RE = re.compile(
    r"^\s*(javob|answer|to'?g'?ri\s*javob|togri\s*javob|правильный\s*ответ|ответ)\s*[:\-]?\s*([A-DА-Г])\b",
    re.IGNORECASE,
)
_EXPLANATION_LINE_RE = re.compile(
    r"^\s*(izoh|explanation|объяснение|комментарий)\s*[:\-]?\s*(.+)$", re.IGNORECASE
)
# GIFT-ish "?/=" convention: questions start with "?", every option starts
# with "=", and the correct one is the "=" with no space right after it
# ("=Oila") while wrong ones have a space ("= Venera"). Common export
# format from Uzbek test-bank tools.
_QUESTION_MARK_RE = re.compile(r"^(?:\s*\?)+\s*")
_EQUALS_RE = re.compile(r"^\s*=(\s*)(.+)$")


class ParseError(Exception):
    pass


def parse_quiz_file(filename: str, file_bytes: bytes) -> tuple[list[dict], list[str]]:
    """Dispatches to the right parser based on the file extension.

    Returns (questions, warnings). warnings is non-empty only for the free-text
    formats (.docx/.txt/.pdf), where a handful of unreadable questions out of
    a large file (stray OCR/extraction glitches) are skipped rather than
    failing the whole upload -- each skipped one is named in warnings so the
    uploader can go check it. .xlsx/.csv stay strict: any bad row raises
    immediately, since the user filled in a fixed template there.
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "xlsx":
        try:
            return parse_quiz_excel(file_bytes), []
        except ExcelParseError as exc:
            raise ParseError(str(exc)) from exc
    if ext == "csv":
        return _parse_csv(file_bytes), []
    if ext == "docx":
        return _parse_free_text(_extract_docx_text(file_bytes))
    if ext == "pdf":
        return _parse_free_text(_extract_pdf_text(file_bytes))
    if ext == "txt":
        return _parse_free_text(_decode_text(file_bytes))

    raise ParseError(
        "Qo'llab-quvvatlanmaydigan fayl turi: ." + (ext or "?")
        + ". Quyidagilardan birini yuboring: .xlsx, .docx, .txt, .csv, .pdf"
    )


# ---------------------------------------------------------------------------
# .csv -- same columns as the .xlsx template, header order/wording flexible
# ---------------------------------------------------------------------------


def _parse_csv(file_bytes: bytes) -> list[dict]:
    text = _decode_text(file_bytes)
    try:
        sample = text[:4096]
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = [row for row in csv.reader(io.StringIO(text), dialect) if any(cell.strip() for cell in row)]
    if not rows:
        raise ParseError("Fayl bo'sh.")
    return _rows_to_questions(rows)


def _rows_to_questions(rows: list[list]) -> list[dict]:
    header_map = _match_header(rows[0])
    data_rows = rows[1:] if header_map else rows
    if not header_map:
        header_map = {
            "question": 0, "option_a": 1, "option_b": 2, "option_c": 3,
            "option_d": 4, "correct_answer": 5, "explanation": 6,
        }

    questions = []
    for row_number, row in enumerate(data_rows, start=2):
        if not any(str(cell).strip() for cell in row if cell is not None):
            continue

        def cell(field: str) -> str:
            idx = header_map.get(field)
            if idx is None or idx >= len(row) or row[idx] is None:
                return ""
            return str(row[idx]).strip()

        question_text = cell("question")
        option_a = cell("option_a")
        option_b = cell("option_b")
        option_c = cell("option_c")
        option_d = cell("option_d")
        correct_raw = cell("correct_answer")
        explanation = cell("explanation")

        if not question_text:
            raise ParseError(f"{row_number}-qator: savol matni bo'sh.")
        if not option_a or not option_b:
            raise ParseError(f"{row_number}-qator: A va B variantlari kerak.")

        options = [option_a, option_b, option_c, option_d]
        correct_index = _resolve_correct_index(correct_raw, options, row_number)

        questions.append({
            "question": question_text,
            "option_a": option_a,
            "option_b": option_b,
            "option_c": option_c or None,
            "option_d": option_d or None,
            "correct_option": correct_index,
            "explanation": explanation or None,
        })

    if not questions:
        raise ParseError("Faylda savollar topilmadi.")
    return questions


def _match_header(row: list) -> dict[str, int] | None:
    normalized = [str(cell).strip().lower() if cell is not None else "" for cell in row]
    found: dict[str, int] = {}
    for idx, cell_text in enumerate(normalized):
        for field, synonyms in HEADER_SYNONYMS.items():
            if cell_text in synonyms and field not in found:
                found[field] = idx
                break
    if {"question", "option_a", "option_b"} <= found.keys():
        return found
    return None


def _resolve_correct_index(correct_raw: str, options: list[str], row_number: int) -> int:
    value = correct_raw.strip()
    letter = value.upper()
    if letter in LETTER_TO_INDEX:
        idx = LETTER_TO_INDEX[letter]
    elif value.isdigit() and 1 <= int(value) <= 4:
        idx = int(value) - 1
    else:
        matches = [i for i, opt in enumerate(options) if opt and opt.strip().lower() == value.lower()]
        if len(matches) == 1:
            idx = matches[0]
        else:
            raise ParseError(
                f"{row_number}-qator: to'g'ri javob aniqlanmadi ({correct_raw!r})."
            )
    if idx >= len(options) or not options[idx]:
        raise ParseError(f"{row_number}-qator: to'g'ri javob bo'sh variantga ishora qiladi.")
    return idx


# ---------------------------------------------------------------------------
# Free text (.txt, .docx, .pdf after extraction) -- "+/-" or lettered options
# ---------------------------------------------------------------------------


def _parse_free_text(text: str) -> tuple[list[dict], list[str]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ParseError("Faylda matn topilmadi.")

    blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) < 2:
        blocks = _split_by_numbering(text)

    questions = []
    warnings = []
    for block_number, block in enumerate(blocks, start=1):
        try:
            question = _parse_block(block, block_number)
        except ParseError as exc:
            warnings.append(str(exc))
            continue
        if question is not None:
            questions.append(question)

    if not questions:
        raise ParseError(
            "Faylda tushunarli savollar topilmadi. Har bir savol kamida 2 ta variant "
            "(A)/B), +/- yoki =/= bilan belgilangan) va to'g'ri javobni o'z ichiga olishi kerak."
        )
    return questions, warnings


def _split_by_numbering(text: str) -> list[str]:
    matches = list(_NUMBERED_LINE_RE.finditer(text))
    if len(matches) < 2:
        return [text]
    blocks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append(text[start:end])
    return blocks


def _parse_block(block: str, block_number: int) -> dict | None:
    lines = [line.strip() for line in block.split("\n") if line.strip()]
    if not lines:
        return None

    question_lines: list[str] = []
    options: list[tuple[str, str]] = []
    scheme: str | None = None
    answer_letter: str | None = None
    explanation: str | None = None

    for line in lines:
        answer_match = _ANSWER_LINE_RE.match(line)
        if answer_match:
            answer_letter = CYRILLIC_LETTER_MAP.get(answer_match.group(2), answer_match.group(2).upper())
            continue

        explanation_match = _EXPLANATION_LINE_RE.match(line)
        if explanation_match:
            explanation = explanation_match.group(2).strip()
            continue

        pm_match = _PLUS_MINUS_RE.match(line)
        if pm_match and scheme in (None, "pm"):
            scheme = "pm"
            options.append((pm_match.group(1), pm_match.group(2).strip()))
            continue

        eq_match = _EQUALS_RE.match(line)
        if eq_match and scheme in (None, "eq"):
            scheme = "eq"
            sign = "-" if eq_match.group(1) else "+"
            options.append((sign, eq_match.group(2).strip()))
            continue

        letter_match = _LETTER_RE.match(line)
        if letter_match and scheme in (None, "letter"):
            letter = CYRILLIC_LETTER_MAP.get(letter_match.group(1), letter_match.group(1).upper())
            if letter in LETTER_TO_INDEX:
                scheme = "letter"
                options.append((letter, letter_match.group(2).strip()))
                continue

        if not options:
            question_lines.append(line)
        else:
            # Continuation of the previous option's wrapped text.
            last_letter, last_text = options[-1]
            options[-1] = (last_letter, f"{last_text} {line}")

    if not question_lines or not options:
        return None

    question_text = " ".join(question_lines).strip()
    question_text = _NUMBERED_LINE_RE.sub("", question_text, count=1).strip()
    question_text = _QUESTION_MARK_RE.sub("", question_text, count=1).strip()
    if not question_text:
        return None

    if scheme in ("pm", "eq"):
        correct_candidates = [i for i, (sign, _) in enumerate(options) if sign == "+"]
        if len(correct_candidates) != 1:
            raise ParseError(
                f"{block_number}-savol: to'g'ri javob aniq emas "
                "(variantlardan faqat bittasi to'g'ri javob sifatida belgilangan bo'lishi kerak)."
            )
        correct_index = correct_candidates[0]
        option_texts = [text for _, text in options]
    else:
        option_texts = []
        correct_index = None
        for i, (letter, text) in enumerate(options):
            starred = text.endswith("*")
            if starred:
                text = text[:-1].strip()
            option_texts.append(text)
            if starred:
                correct_index = i
        if correct_index is None and answer_letter is not None:
            letters = [letter for letter, _ in options]
            if answer_letter in letters:
                correct_index = letters.index(answer_letter)
        if correct_index is None:
            raise ParseError(
                f"{block_number}-savol: to'g'ri javob aniqlanmadi "
                "(variantni '*' bilan belgilang yoki \"Javob: A\" qatorini qo'shing)."
            )

    if len(option_texts) < 2:
        raise ParseError(f"{block_number}-savol: kamida 2 ta variant kerak.")
    option_texts = option_texts[:4]
    if correct_index >= len(option_texts):
        raise ParseError(f"{block_number}-savol: to'g'ri javob variantlar sonidan oshib ketdi.")

    option_a, option_b, option_c, option_d = (option_texts + [None, None, None, None])[:4]
    return {
        "question": question_text,
        "option_a": option_a,
        "option_b": option_b,
        "option_c": option_c,
        "option_d": option_d,
        "correct_option": correct_index,
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------


def _decode_text(file_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="ignore")


def _extract_docx_text(file_bytes: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ParseError("Server .docx fayllarni o'qiy olmaydi (python-docx o'rnatilmagan).") from exc

    try:
        document = Document(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ParseError(f"Word faylini o'qib bo'lmadi: {exc}") from exc

    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append("\n".join(cell.text for cell in row.cells if cell.text))
    return "\n".join(parts)


def _extract_pdf_text(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ParseError("Server .pdf fayllarni o'qiy olmaydi (pypdf o'rnatilmagan).") from exc

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ParseError(f"PDF faylini o'qib bo'lmadi: {exc}") from exc

    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages)
    if not text.strip():
        raise ParseError(
            "PDF ichidan matn chiqmadi (ehtimol, skanerlangan rasm). "
            "Matnli PDF, .docx yoki .txt fayl yuboring."
        )
    return text
