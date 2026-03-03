"""Authorization helpers for the Telegram bot.

This module provides a simple whitelist check and a decorator to protect
handler callables. The whitelist is driven by `AUTHORIZED_TELEGRAM_IDS`
in `config.py` (a list of integer Telegram user IDs). If that list is
empty the bot remains open to all users (useful for development).
"""

from typing import Callable

from config import AUTHORIZED_TELEGRAM_IDS
from telegram import Update
from telegram.ext import ContextTypes


async def is_authorized(telegram_id: int) -> bool:
    """Return True if `telegram_id` is allowed to use the bot.

    An empty `AUTHORIZED_TELEGRAM_IDS` list means "allow all".
    """
    if not AUTHORIZED_TELEGRAM_IDS:
        return True
    return telegram_id in AUTHORIZED_TELEGRAM_IDS


def require_authorized(func: Callable):
    """Decorator for handler functions to block unauthorized users.

    Usage:

    @require_authorized
    async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        ...

    The decorator replies with an "Access denied" message if the user
    is not authorized and returns early.
    """

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        user_id = user.id if user else None
        if not user_id or not await is_authorized(user_id):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "Access denied. Contact the bot owner to gain access."
                )
            return
        return await func(update, context, *args, **kwargs)

    return wrapper
