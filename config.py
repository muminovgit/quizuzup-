import os
from pathlib import Path

from dotenv import load_dotenv

# Resolve relative to this file, not the process's current working
# directory -- the bot and the web API are launched from different
# directories (webapi/ has its own cwd) and must share one .env/DB.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

_db_path = os.getenv("DB_PATH", "quizbot.db")
DB_PATH = _db_path if os.path.isabs(_db_path) else str(BASE_DIR / _db_path)

# When set, db_driver.py routes all storage to a remote Turso (libSQL)
# database instead of the local DB_PATH file. This is what makes data
# survive a Render redeploy -- the free tier's local disk does not.
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

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

# Public URL of the standalone web portal (shown in login messages)
WEB_URL = os.getenv("WEB_URL", "")

# Secret used to deterministically derive each user's web-portal password
# (see auth.derive_password), so re-issuing credentials never changes them.
# Falls back to BOT_TOKEN so it works with zero extra config.
WEB_CREDENTIAL_SECRET = os.getenv("WEB_CREDENTIAL_SECRET", "") or BOT_TOKEN
