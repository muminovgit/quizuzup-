"""Standalone web API for the Quiz Bot's web portal.

Pro users get a username/password (issued by the bot) to take the same
quizzes on a website, with a "mistakes" list they can review and retry.
Runs as its own process, sharing the bot's SQLite database (WAL mode).
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
from auth import generate_session_token, verify_password  # noqa: E402

SESSION_TTL_HOURS = 24 * 30

app = FastAPI(title="Quiz Bot Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await db.init_db()


@app.get("/healthz")
async def healthz():
    """Cheap, unauthenticated endpoint for keep-alive pings (see
    .github/workflows/keepalive.yml) -- Render's free tier spins the
    service down after 15 minutes with no inbound HTTP traffic, which
    would otherwise also kill the bot's long-polling loop alongside it."""
    return {"status": "ok"}


@app.get("/_diag")
async def diag(x_diag_key: str | None = Header(default=None)):
    """TEMPORARY: checking whether Render's disk actually persists data
    across deploys. Remove once confirmed either way."""
    import os

    import aiosqlite
    import config

    if x_diag_key != config.WEB_CREDENTIAL_SECRET:
        raise HTTPException(status_code=404)

    async with aiosqlite.connect(db.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        users = [dict(r) for r in await (await conn.execute("SELECT user_id, username, is_premium FROM users")).fetchall()]

    return {
        "db_path": db.DB_PATH,
        "db_exists": os.path.exists(db.DB_PATH),
        "db_size_bytes": os.path.getsize(db.DB_PATH) if os.path.exists(db.DB_PATH) else 0,
        "quizzes": await db.list_all_quizzes(),
        "users": users,
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class SubmitAnswer(BaseModel):
    question_id: int
    selected_option: int


class SubmitRequest(BaseModel):
    answers: list[SubmitAnswer]


class RetryRequest(BaseModel):
    selected_option: int


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    session = await db.get_web_session(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return session


@app.post("/api/auth/login")
async def login(payload: LoginRequest):
    creds = await db.get_web_credentials_by_username(payload.username.strip())
    if creds is None or not verify_password(payload.password, creds["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not await db.is_premium(creds["user_id"]):
        raise HTTPException(status_code=403, detail="Pro subscription required")

    token = generate_session_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    await db.create_web_session(token, creds["user_id"], expires_at)
    return {"token": token, "username": creds["username"]}


@app.post("/api/auth/logout")
async def logout(session: dict = Depends(get_current_user)):
    await db.delete_web_session(session["token"])
    return {"ok": True}


@app.get("/api/me")
async def me(session: dict = Depends(get_current_user)):
    creds = await db.get_web_credentials_by_user_id(session["user_id"])
    return {"username": creds["username"] if creds else None, "user_id": session["user_id"]}


# ---------------------------------------------------------------------------
# Quizzes
# ---------------------------------------------------------------------------


@app.get("/api/quizzes")
async def list_quizzes(session: dict = Depends(get_current_user)):
    return await db.list_all_quizzes()


@app.get("/api/quizzes/{quiz_id}")
async def get_quiz(quiz_id: int, session: dict = Depends(get_current_user)):
    quiz = await db.get_quiz_by_id(quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    questions = await db.get_questions(quiz_id)
    return {
        "quiz_id": quiz["quiz_id"],
        "name": quiz["name"],
        "questions": [_public_question(q) for q in questions],
    }


def _public_question(q: dict) -> dict:
    options = [
        {"index": i, "text": text}
        for i, text in enumerate([q["option_a"], q["option_b"], q["option_c"], q["option_d"]])
        if text
    ]
    return {"question_id": q["question_id"], "question_text": q["question_text"], "options": options}


@app.post("/api/quizzes/{quiz_id}/submit")
async def submit_quiz(quiz_id: int, payload: SubmitRequest, session: dict = Depends(get_current_user)):
    quiz = await db.get_quiz_by_id(quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    results = []
    correct_count = 0
    for answer in payload.answers:
        question = await db.get_question_by_id(answer.question_id)
        if question is None or question["quiz_id"] != quiz_id:
            continue
        is_correct = answer.selected_option == question["correct_option"]
        if is_correct:
            correct_count += 1
        await db.record_web_attempt(
            session["user_id"], quiz_id, answer.question_id, answer.selected_option, is_correct
        )
        results.append(
            {
                "question_id": answer.question_id,
                "correct": is_correct,
                "correct_option": question["correct_option"],
                "explanation": question["explanation"],
            }
        )

    return {"score": correct_count, "total": len(payload.answers), "results": results}


@app.post("/api/quizzes/{quiz_id}/questions/{question_id}/answer")
async def answer_question(
    quiz_id: int, question_id: int, payload: RetryRequest, session: dict = Depends(get_current_user)
):
    """Grades and records a single answer immediately (one-question-at-a-time UI)."""
    question = await db.get_question_by_id(question_id)
    if question is None or question["quiz_id"] != quiz_id:
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = payload.selected_option == question["correct_option"]
    await db.record_web_attempt(session["user_id"], quiz_id, question_id, payload.selected_option, is_correct)
    return {
        "correct": is_correct,
        "correct_option": question["correct_option"],
        "explanation": question["explanation"],
    }


# ---------------------------------------------------------------------------
# Mistakes (review + retry)
# ---------------------------------------------------------------------------


@app.get("/api/mistakes")
async def mistakes(session: dict = Depends(get_current_user)):
    rows = await db.get_mistakes(session["user_id"])
    out = []
    for row in rows:
        options = [
            {"index": i, "text": text}
            for i, text in enumerate(
                [row["option_a"], row["option_b"], row["option_c"], row["option_d"]]
            )
            if text
        ]
        out.append(
            {
                "question_id": row["question_id"],
                "quiz_id": row["quiz_id"],
                "quiz_name": row["quiz_name"],
                "question_text": row["question_text"],
                "options": options,
                "selected_option": row["selected_option"],
                "correct_option": row["correct_option"],
                "explanation": row["explanation"],
            }
        )
    return out


@app.post("/api/mistakes/{question_id}/retry")
async def retry_mistake(question_id: int, payload: RetryRequest, session: dict = Depends(get_current_user)):
    question = await db.get_question_by_id(question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = payload.selected_option == question["correct_option"]
    await db.record_web_attempt(
        session["user_id"], question["quiz_id"], question_id, payload.selected_option, is_correct
    )
    return {
        "correct": is_correct,
        "correct_option": question["correct_option"],
        "explanation": question["explanation"],
    }


# ---------------------------------------------------------------------------
# Serve the built frontend (webapp/dist), same origin as the API -- this
# must be registered LAST so it never shadows an /api/* route above it.
# ---------------------------------------------------------------------------

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "webapp" / "dist"

if _FRONTEND_DIST.is_dir():

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
