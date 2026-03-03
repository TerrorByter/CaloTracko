"""Handler for /reminder - manage meal reminder notifications using text input for time."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from database import get_user, upsert_user

logger = logging.getLogger(__name__)

# Conversation states
SETTING_TIME = 1


async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show reminder settings menu."""
    user = await get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "⚠️ Please set up your profile first with /profile"
        )
        return ConversationHandler.END

    await _show_reminder_menu(update, context, user)
    return ConversationHandler.END  # Menu is stateless by default, only time-setting is a conversation


async def _show_reminder_menu(update, context, user, edit=False):
    """Build and send/edit the reminder settings menu."""
    enabled = user.get("reminder_enabled", 1)
    hour = user.get("reminder_hour", 12)

    status = "✅ ON" if enabled else "❌ OFF"
    time_display = f"{hour:02d}:00"

    msg = (
        f"🔔 *Reminder Settings*\n\n"
        f"Status: *{status}*\n"
        f"Time: *{time_display} SGT*\n\n"
        f"When enabled, I'll remind you to log meals if you haven't logged any by this time."
    )

    toggle_label = "❌ Turn OFF" if enabled else "✅ Turn ON"
    keyboard = [
        [InlineKeyboardButton(toggle_label, callback_data="rem_toggle")],
        [InlineKeyboardButton("🕒 Change Time", callback_data="rem_set_time")],
    ]

    markup = InlineKeyboardMarkup(keyboard)

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            msg, parse_mode="Markdown", reply_markup=markup
        )
    else:
        # Check if update.message exists (from command)
        if update.message:
            await update.message.reply_text(
                msg, parse_mode="Markdown", reply_markup=markup
            )
        else:
            # Fallback for callback queries that don't want to edit (rare)
            await update.effective_message.reply_text(
                msg, parse_mode="Markdown", reply_markup=markup
            )


async def reminder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reminder setting button presses."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    user = await get_user(user_id)
    if not user:
        return ConversationHandler.END

    action = query.data

    if action == "rem_toggle":
        enabled = user.get("reminder_enabled", 1)
        enabled = 0 if enabled else 1
        await upsert_user(user_id, reminder_enabled=enabled)
        user = await get_user(user_id)
        await _show_reminder_menu(update, context, user, edit=True)
        return ConversationHandler.END

    if action == "rem_set_time":
        await query.edit_message_text(
            "🕒 *Setting Reminder Time*\n\n"
            "Please enter the hour you'd like to be reminded (0-23).\n"
            "Example: `12` for noon, `18` for 6 PM.\n\n"
            "Type /cancel to go back.",
            parse_mode="Markdown"
        )
        return SETTING_TIME

    return ConversationHandler.END


async def handle_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the text input for the reminder hour."""
    text = update.message.text.strip()
    user_id = update.effective_user.id

    try:
        hour = int(text)
        if not 0 <= hour <= 23:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Invalid input. Please enter a whole number between 0 and 23:"
        )
        return SETTING_TIME

    await upsert_user(user_id, reminder_hour=hour)
    user = await get_user(user_id)
    
    await update.message.reply_text(f"✅ Reminder time updated to *{hour:02d}:00 SGT*.", parse_mode="Markdown")
    await _show_reminder_menu(update, context, user)
    return ConversationHandler.END


async def cancel_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the reminder setting process."""
    user = await get_user(update.effective_user.id)
    if user:
        await _show_reminder_menu(update, context, user)
    else:
        await update.message.reply_text("Setup cancelled.")
    return ConversationHandler.END


def get_handlers():
    """Return reminder conversation handler."""
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("reminder", reminder_command),
            CallbackQueryHandler(reminder_callback, pattern="^rem_"),
        ],
        states={
            SETTING_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time_input),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_reminder)],
        allow_reentry=True,
    )
    return [conv_handler]
