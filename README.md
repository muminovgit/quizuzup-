# Telegram Quiz Bot

An aiogram 3.x Telegram bot that turns an Excel file into native Telegram
quiz-polls, with persistent storage, a per-chat leaderboard, saved-quiz
management, and a Telegram Stars paid tier.

## Features

- **Upload → quiz**: `/newquiz` + an `.xlsx` file (see `quiz_template.xlsx`)
  creates a quiz from `Question | Option A | Option B | Option C | Option D |
  Correct Answer (A/B/C/D) | Explanation` columns.
- **Persistence**: quizzes and questions are stored in SQLite (`aiosqlite`),
  so they survive restarts and work across multiple chats/groups.
- **Leaderboard**: every `poll_answer` update is recorded; `/leaderboard`
  shows the top scorers for the current chat.
- **Quiz management**: `/myquizzes` lists your saved quizzes, `/startquiz
  [name]` runs one (as native Telegram quiz polls, `open_period=30s`,
  non-anonymous), `/deletequiz [name]` removes one. Without a name, both
  commands show an inline-button picker.
- **Admin panel**: only the Telegram user who uploaded a quiz can start or
  delete it.
- **Telegram Stars payments**: free tier is capped at 2 quizzes / 10
  questions each; `/upgrade` sends a Stars invoice that unlocks unlimited
  quizzes and questions once paid.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in BOT_TOKEN from @BotFather
python3 bot.py
```

## Project layout

| File                  | Purpose                                              |
|------------------------|-------------------------------------------------------|
| `bot.py`               | aiogram handlers, quiz-running logic, entrypoint      |
| `db.py`                | Async SQLite persistence layer (aiosqlite)            |
| `excel_parser.py`      | Parses/validates the uploaded `.xlsx` into questions  |
| `config.py`            | Env-driven settings (token, DB path, tier limits)     |
| `generate_template.py` | Regenerates `quiz_template.xlsx`                      |
| `quiz_template.xlsx`   | Sample template admins fill in and upload             |

## Commands

- `/start` — welcome + command list
- `/newquiz` — upload an `.xlsx` to create a quiz
- `/myquizzes` — list your saved quizzes
- `/startquiz [name]` — run a saved quiz in the current chat
- `/deletequiz [name]` — delete one of your quizzes
- `/leaderboard` — top scorers in the current chat
- `/upgrade` — buy the Pro tier with Telegram Stars

## Notes

- Telegram poll limits are enforced when sending (300-char question,
  100-char options, 200-char explanation); the Excel parser itself only
  validates structure (headers present, correct answer is A–D, referenced
  option isn't empty).
- Quizzes are scoped to their uploader (`owner_id`), so the same saved quiz
  can be started in any chat the owner and bot share; the leaderboard is
  scoped per chat.
