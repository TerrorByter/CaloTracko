"""Configuration loader for the calorie tracking bot."""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(var_name: str) -> str:
    """Get a required environment variable or raise an error."""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value


# Telegram
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")

# Webhook URL (your Vercel deployment URL, e.g. https://your-app.vercel.app)
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")

# AI Model (OpenAI-compatible aggregator)
API_KEY: str = _require("API_KEY")
API_BASE_URL: str = _require("API_BASE_URL")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")

# Database (Supabase Postgres connection string)
DATABASE_URL: str = _require("DATABASE_URL")

# Optional: comma-separated Telegram user IDs allowed to use the bot.
_authorized_raw = os.getenv("AUTHORIZED_TELEGRAM_IDS", "")
if _authorized_raw:
    try:
        AUTHORIZED_TELEGRAM_IDS = [int(x.strip()) for x in _authorized_raw.split(",") if x.strip()]
    except ValueError:
        raise ValueError("AUTHORIZED_TELEGRAM_IDS must be a comma-separated list of integers")
else:
    AUTHORIZED_TELEGRAM_IDS = []
