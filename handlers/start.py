"""Handler for /start command."""

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CommandHandler, ContextTypes

from auth import require_authorized

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🍱 Log Meal")],
        [KeyboardButton("📊 Today"), KeyboardButton("📈 Week")],
        [KeyboardButton("📋 Saved"), KeyboardButton("👤 Profile")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)


@require_authorized
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with bot overview."""
    welcome = (
        "👋 *Welcome to CalorieBot!*\n\n"
        "I help you track your daily calorie intake using AI.\n"
        "Just send me a *photo* or *text description* of your food "
        "and I'll estimate the calories and macros!\n\n"
        "🚀 *Quick Start:*\n"
        "1️⃣ Set up your profile with 👤 Profile\n"
        "2️⃣ Send a food photo or description to log a meal\n"
        "3️⃣ Tap 📊 Today to check your progress!"
    )
    await update.message.reply_text(
        welcome, parse_mode="Markdown", reply_markup=MENU_KEYBOARD
    )


def get_handler():
    """Return the handler for registration."""
    return CommandHandler("start", start_command)
