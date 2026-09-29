# Telegram Quiz Bot + Web Portal

An aiogram 3.x Telegram bot that turns an Excel file into native Telegram
quiz-polls, with persistent storage, a per-chat leaderboard, pausable quiz
sessions, uz/ru/en localization, Telegram Stars *and* manual (cash/Click/
Payme) payments, and a standalone web portal for Pro subscribers to retake
quizzes and drill their mistakes.

## Features

- **Upload → quiz**: `/newquiz` + an `.xlsx` file (see `quiz_template.xlsx`,
  also sent automatically on `/start`) creates a quiz from `Question |
  Option A | Option B | Option C | Option D | Correct Answer (A/B/C/D) |
  Explanation` columns.
- **Persistence**: quizzes, questions, scores and web-portal data live in
  SQLite (`aiosqlite`, WAL mode), so they survive restarts and are shared
  safely between the bot process and the web API process.
- **Leaderboard**: every `poll_answer` update is recorded; `/leaderboard`
  shows the top scorers for the current chat.
- **Quiz management**: `/myquizzes` lists your saved quizzes, `/startquiz
  [name]` runs one (native Telegram quiz polls, `open_period=30s`,
  non-anonymous), `/deletequiz [name]` removes one. Without a name, both
  commands show an inline-button picker.
- **Pausable sessions**: a running quiz auto-pauses if 4 questions in a row
  get no answers, and `/stop` (or the inline "⏸ Stop" button) pauses it
  manually — either way a "▶️ Resume" button continues right where it left
  off. Only the admin who started the quiz can pause/resume it.
- **uz / ru / en localization**: `/language` switches anytime; every message
  is translated (`translations.py`).
- **Admin panel**: only the Telegram user who uploaded a quiz can start or
  delete it.
- **Two payment paths to the Pro tier** (unlimited quizzes/questions; free
  tier is capped at 2 quizzes / 10 questions each):
  - **Telegram Stars**: `/upgrade` sends a Stars invoice.
  - **Manual (cash, Click, Payme, bank transfer, ...)**: the buyer sends
    `/myid` to get their numeric ID, hands it to you outside the bot, and
    you run `/grantpro <id or @username>` (or just reply to their message
    with `/grantpro`) to activate them. `/revokepro` undoes it.
- **Web portal**: once `WEB_URL` is configured, granting Pro (either way)
  DMs the user a username/password for the standalone website (`webapp/`),
  where they can retake any quiz and review/retry a personal "Mistakes"
  list. `/webportal` (re)issues credentials on demand.

## Setup — bot

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in BOT_TOKEN from @BotFather, and the rest as needed
python3 bot.py
```

## Setup — web portal (optional)

Two extra processes, sharing the same SQLite file as the bot:

```bash
# API (FastAPI)
pip install -r webapi/requirements.txt
cd webapi && uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend (React + Vite + Tailwind)
cd webapp
cp .env.example .env   # VITE_API_URL -> where the API above is reachable
npm install
npm run dev      # local dev
npm run build    # production build -> dist/, deploy as a static site
```

Then set `WEB_URL` in the root `.env` to wherever the frontend is deployed
(e.g. a Vercel/Netlify URL for `webapp/dist`, with the API on a small VPS or
Railway/Render). The bot and the API must reach the **same** `quizbot.db`
file (and the same `.env`, for `WEB_URL`/`ADMIN_IDS`/etc.) — run them on the
same host, or point both at a shared volume.

## Project layout

| Path                   | Purpose                                              |
|-------------------------|-------------------------------------------------------|
| `bot.py`                | aiogram handlers, quiz-running logic, entrypoint      |
| `db.py`                 | Async SQLite persistence layer (aiosqlite)            |
| `auth.py`                | Password hashing + session tokens (shared by bot & API) |
| `excel_parser.py`       | Parses/validates the uploaded `.xlsx` into questions  |
| `translations.py`       | uz/ru/en text for every bot message                   |
| `config.py`             | Env-driven settings (token, DB path, tiers, admin IDs)|
| `generate_template.py`  | Regenerates `quiz_template.xlsx`                      |
| `quiz_template.xlsx`    | Sample template admins fill in and upload             |
| `webapi/main.py`        | FastAPI backend for the web portal                    |
| `webapp/`                | React + Vite + Tailwind frontend (login, quizzes, mistakes) |

## Bot commands

- `/start` — welcome, language picker on first use, sends the xlsx template
- `/language` — change language (uz/ru/en)
- `/newquiz` — upload an `.xlsx` to create a quiz
- `/myquizzes` — list your saved quizzes
- `/startquiz [name]` — run a saved quiz in the current chat
- `/stop` — pause the quiz currently running in this chat
- `/deletequiz [name]` — delete one of your quizzes
- `/leaderboard` — top scorers in the current chat
- `/upgrade` — buy the Pro tier with Telegram Stars
- `/myid` — get your numeric Telegram ID (for manual-payment Pro requests)
- `/webportal` — (Pro only) get/regenerate your web-portal login
- `/grantpro`, `/revokepro` — **admin-only** (see `ADMIN_IDS`), manually
  grant/revoke Pro for out-of-band payments

## Notes

- Telegram poll limits are enforced when sending (300-char question,
  100-char options, 200-char explanation); the Excel parser itself only
  validates structure (headers present, correct answer is A–D, referenced
  option isn't empty).
- Quizzes are scoped to their uploader (`owner_id`), so the same saved quiz
  can be started in any chat the owner and bot share; the leaderboard is
  scoped per chat. The web portal lists *all* quizzes in the system (it's
  meant as the bot owner's own content library for their Pro subscribers).
- The web API's `/api/*` routes require a `Bearer` session token from
  `/api/auth/login`; login itself requires the account to currently be Pro.
