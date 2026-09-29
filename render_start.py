"""Render entrypoint: runs the Telegram bot and the web API as one service.

They both need the same local quizbot.db (SQLite, WAL mode) to actually
share data, and a single Render service is the simplest way to guarantee
that -- one filesystem, one process group. The API binds to $PORT (what
Render's health check expects); the bot is a long-polling background
process alongside it.
"""

import asyncio
import os
import subprocess
import sys


def main() -> None:
    port = os.environ.get("PORT", "8000")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "webapi.main:app", "--host", "0.0.0.0", "--port", port]
    )
    try:
        import bot

        asyncio.run(bot.main())
    finally:
        api_proc.terminate()
        api_proc.wait(timeout=10)


if __name__ == "__main__":
    main()
