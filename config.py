import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "quizbot.db")

# Telegram user IDs allowed to run /grantpro and /revokepro (manual Pro
# activation for admins who take payment outside Telegram Stars -- cash,
# Click, Payme, bank transfer, etc). Comma-separated in the env var.
_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip().isdigit()}

# Optional @username shown in /upgrade as a manual-payment contact.
ADMIN_CONTACT_USERNAME = os.getenv("ADMIN_CONTACT_USERNAME", "")

# Free tier limits
FREE_MAX_QUIZZES = 2
FREE_MAX_QUESTIONS = 10

# Telegram Stars price for the Pro upgrade (unlimited quizzes/questions)
PRO_UPGRADE_STARS = 100

# How long each poll stays open, in seconds
POLL_OPEN_PERIOD = 30
