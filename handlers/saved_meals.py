"""Handler for /saved - view and log saved meals."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from database import get_saved_meals, get_saved_meal, delete_saved_meal, log_meal
from utils import format_meal_summary

PAGE_SIZE = 5


async def saved_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of saved meals."""
    meals = await get_saved_meals(update.effective_user.id)

    if not meals:
        await update.message.reply_text(
            "📋 *No saved meals yet!*\n\n"
            "Send me a food photo or description, then use "
            "\"💾 Save & Log\" to save a meal for quick access.",
            parse_mode="Markdown",
        )
        return

    page = 0
    context.user_data["saved_page"] = page
    await _show_saved_page(update.message, meals, page)


async def _show_saved_page(target, meals: list, page: int, edit: bool = False) -> None:
    """Display a page of saved meals."""
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_meals = meals[start:end]
    total_pages = (len(meals) + PAGE_SIZE - 1) // PAGE_SIZE

    keyboard = []
    for meal in page_meals:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"🍽 {meal['name']} ({meal['calories']} kcal)",
                    callback_data=f"saved_select_{meal['id']}",
                )
            ]
        )

    # Pagination buttons
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"saved_page_{page - 1}"))
    if end < len(meals):
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"saved_page_{page + 1}"))
    if nav:
        keyboard.append(nav)
    
    # Add back button to the list if editing (callback from selection)
    if edit and not nav:
        keyboard.append([InlineKeyboardButton("⬅️ Back to list", callback_data="saved_back")])

    text = f"📋 *Saved Meals* (Page {page + 1}/{total_pages})\n\nSelect a meal to log:"

    if edit:
        await target.edit_message_text(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await target.reply_text(
            text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def saved_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pagination."""
    query = update.callback_query
    await query.answer()
    page = int(query.data.replace("saved_page_", ""))
    meals = await get_saved_meals(update.effective_user.id)
    await _show_saved_page(query, meals, page, edit=True)


async def saved_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle meal selection."""
    query = update.callback_query
    await query.answer()
    meal_id = int(query.data.replace("saved_select_", ""))
    meal = await get_saved_meal(meal_id, update.effective_user.id)

    if not meal:
        await query.edit_message_text("⚠️ Meal not found.")
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Log this meal", callback_data=f"saved_log_{meal_id}"),
                InlineKeyboardButton("🗑 Delete", callback_data=f"saved_delete_{meal_id}"),
            ],
            [InlineKeyboardButton("⬅️ Back to list", callback_data="saved_back")],
        ]
    )

    await query.edit_message_text(
        format_meal_summary(meal),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def saved_log_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log a saved meal."""
    query = update.callback_query
    await query.answer()
    meal_id = int(query.data.replace("saved_log_", ""))
    meal = await get_saved_meal(meal_id, update.effective_user.id)

    if not meal:
        await query.edit_message_text("⚠️ Meal not found.")
        return

    await log_meal(
        user_id=update.effective_user.id,
        name=meal["name"],
        description=meal.get("description", ""),
        calories=meal["calories"],
        protein_g=meal.get("protein_g", 0),
        carbs_g=meal.get("carbs_g", 0),
        fat_g=meal.get("fat_g", 0),
    )

    await query.edit_message_text(
        f"✅ *Logged:* {meal['name']} — {meal['calories']} kcal\n\n"
        f"Use /today to see your daily progress!",
        parse_mode="Markdown",
    )


async def saved_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a saved meal."""
    query = update.callback_query
    await query.answer()
    meal_id = int(query.data.replace("saved_delete_", ""))
    deleted = await delete_saved_meal(meal_id, update.effective_user.id)

    if deleted:
        await query.edit_message_text("🗑 Meal deleted.")
    else:
        await query.edit_message_text("⚠️ Could not delete meal.")


async def saved_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Go back to the saved meals list."""
    query = update.callback_query
    await query.answer()
    meals = await get_saved_meals(update.effective_user.id)
    page = context.user_data.get("saved_page", 0)
    await _show_saved_page(query, meals, page, edit=True)


def get_handlers():
    """Return all handlers for saved meals."""
    return [
        CommandHandler("saved", saved_command),
        CallbackQueryHandler(saved_page_callback, pattern=r"^saved_page_"),
        CallbackQueryHandler(saved_select_callback, pattern=r"^saved_select_"),
        CallbackQueryHandler(saved_log_callback, pattern=r"^saved_log_"),
        CallbackQueryHandler(saved_delete_callback, pattern=r"^saved_delete_"),
        CallbackQueryHandler(saved_back_callback, pattern=r"^saved_back$"),
    ]
