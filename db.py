"""Async SQLite persistence layer for the quiz bot (aiosqlite)."""

import aiosqlite

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    is_premium INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS quizzes (
    quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS questions (
    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT,
    option_d TEXT,
    correct_option INTEGER NOT NULL,
    explanation TEXT,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS quiz_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    started_by INTEGER NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS poll_map (
    poll_id TEXT PRIMARY KEY,
    session_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    correct_option INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES quiz_sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS answers (
    answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id TEXT NOT NULL,
    session_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    username TEXT,
    is_correct INTEGER NOT NULL,
    answered_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(poll_id, user_id)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stars_amount INTEGER NOT NULL,
    telegram_charge_id TEXT,
    paid_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_quizzes_owner ON quizzes(owner_id);
CREATE INDEX IF NOT EXISTS idx_questions_quiz ON questions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_answers_chat_user ON answers(chat_id, user_id);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def upsert_user(user_id: int, username: str | None, first_name: str | None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username = excluded.username,
                                                first_name = excluded.first_name
            """,
            (user_id, username, first_name),
        )
        await db.commit()


async def is_premium(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return bool(row and row[0])


async def set_premium(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_premium = 1 WHERE user_id = ?", (user_id,))
        await db.commit()


async def record_payment(user_id: int, stars_amount: int, telegram_charge_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO payments (user_id, stars_amount, telegram_charge_id) VALUES (?, ?, ?)",
            (user_id, stars_amount, telegram_charge_id),
        )
        await db.commit()


async def count_quizzes_by_owner(owner_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM quizzes WHERE owner_id = ?", (owner_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0


async def quiz_name_exists(owner_id: int, name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM quizzes WHERE owner_id = ? AND name = ?", (owner_id, name)
        )
        return (await cursor.fetchone()) is not None


async def create_quiz(owner_id: int, name: str, questions: list[dict]) -> int:
    """Create a quiz with its questions. Returns the new quiz_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO quizzes (owner_id, name) VALUES (?, ?)", (owner_id, name)
        )
        quiz_id = cursor.lastrowid
        await db.executemany(
            """
            INSERT INTO questions
                (quiz_id, position, question_text, option_a, option_b, option_c, option_d,
                 correct_option, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    quiz_id,
                    i,
                    q["question"],
                    q["option_a"],
                    q["option_b"],
                    q.get("option_c"),
                    q.get("option_d"),
                    q["correct_option"],
                    q.get("explanation"),
                )
                for i, q in enumerate(questions)
            ],
        )
        await db.commit()
        return quiz_id


async def list_quizzes_by_owner(owner_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT q.quiz_id, q.name, q.created_at, COUNT(qs.question_id) AS question_count
            FROM quizzes q
            LEFT JOIN questions qs ON qs.quiz_id = q.quiz_id
            WHERE q.owner_id = ?
            GROUP BY q.quiz_id
            ORDER BY q.created_at DESC
            """,
            (owner_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_quiz_by_name(owner_id: int, name: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM quizzes WHERE owner_id = ? AND name = ?", (owner_id, name)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_quiz_by_id(quiz_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM quizzes WHERE quiz_id = ?", (quiz_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_questions(quiz_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM questions WHERE quiz_id = ? ORDER BY position", (quiz_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_quiz(quiz_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute("DELETE FROM quizzes WHERE quiz_id = ?", (quiz_id,))
        await db.commit()


async def create_session(quiz_id: int, chat_id: int, started_by: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO quiz_sessions (quiz_id, chat_id, started_by) VALUES (?, ?, ?)",
            (quiz_id, chat_id, started_by),
        )
        await db.commit()
        return cursor.lastrowid


async def finish_session(session_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE quiz_sessions SET status = 'finished' WHERE session_id = ?", (session_id,)
        )
        await db.commit()


async def save_poll_map(
    poll_id: str, session_id: int, question_id: int, correct_option: int, chat_id: int
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO poll_map (poll_id, session_id, question_id, correct_option, chat_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (poll_id, session_id, question_id, correct_option, chat_id),
        )
        await db.commit()


async def get_poll_map(poll_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM poll_map WHERE poll_id = ?", (poll_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def record_answer(
    poll_id: str,
    session_id: int,
    chat_id: int,
    user_id: int,
    username: str | None,
    is_correct: bool,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO answers (poll_id, session_id, chat_id, user_id, username, is_correct)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(poll_id, user_id) DO UPDATE SET is_correct = excluded.is_correct
            """,
            (poll_id, session_id, chat_id, user_id, username, int(is_correct)),
        )
        await db.commit()


async def get_leaderboard(chat_id: int, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT user_id,
                   COALESCE(MAX(username), '') AS username,
                   SUM(is_correct) AS correct_count,
                   COUNT(*) AS total_answered
            FROM answers
            WHERE chat_id = ?
            GROUP BY user_id
            ORDER BY correct_count DESC, total_answered ASC
            LIMIT ?
            """,
            (chat_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
