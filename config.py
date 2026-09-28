import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "quizbot.db")

# Free tier limits
FREE_MAX_QUIZZES = 2
FREE_MAX_QUESTIONS = 10

# Telegram Stars price for the Pro upgrade (unlimited quizzes/questions)
PRO_UPGRADE_STARS = 100

# How long each poll stays open, in seconds
POLL_OPEN_PERIOD = 30
