"""Handlers for /today, /week, /history - calorie tracking summaries."""

from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

from database import get_user, get_meals_for_date, get_meals_for_week, delete_meal
from utils import format_progress_bar, format_meal_summary


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show today's calorie summary with a delete option."""
    user_id = update.effective_user.id
    msg, keyboard = await _build_today_message(user_id)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)


async def _build_today_message(user_id: int):
    """Build today's summary text with a single 'Delete a meal' button."""
    user = await get_user(user_id)
    today = datetime.utcnow()
    meals = await get_meals_for_date(user_id, today)

    total_cal = sum(m["calories"] for m in meals)
    total_protein = sum(m.get("protein_g", 0) for m in meals)
    total_carbs = sum(m.get("carbs_g", 0) for m in meals)
    total_fat = sum(m.get("fat_g", 0) for m in meals)

    goal = user.get("daily_calorie_goal", 2000) if user else 2000
    remaining = max(goal - total_cal, 0)

    msg = f"📊 *Today's Summary* ({today.strftime('%b %d')})\n\n"

    if meals:
        for i, meal in enumerate(meals, 1):
            log_ts = meal.get("logged_at")
            if log_ts:
                time_str = log_ts.strftime("%H:%M") if hasattr(log_ts, "strftime") else str(log_ts)[11:16]
            else:
                time_str = ""
            msg += f"{i}. {meal['name']} — {meal['calories']} kcal"
            if time_str:
                msg += f" _{time_str}_"
            msg += "\n"
        msg += "\n"
    else:
        msg += "_No meals logged yet today._\n\n"

    msg += (
        f"🔥 *Total: {total_cal} / {goal} kcal*\n"
        f"{format_progress_bar(total_cal, goal)}\n\n"
        f"🥩 Protein: {total_protein:.1f}g\n"
        f"🍞 Carbs: {total_carbs:.1f}g\n"
        f"🧈 Fat: {total_fat:.1f}g\n"
    )

    if remaining > 0:
        msg += f"\n💡 {remaining} kcal remaining"
    elif total_cal > goal:
        msg += f"\n⚠️ {total_cal - goal} kcal over goal"

    # Only show the delete entry button if there are meals
    buttons = []
    if meals:
        buttons.append([InlineKeyboardButton("🗑 Delete a meal", callback_data="today_delete_menu")])

    keyboard = InlineKeyboardMarkup(buttons) if buttons else None
    return msg, keyboard


async def show_delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Expand the delete menu to show individual meal delete buttons."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    today = datetime.utcnow()
    meals = await get_meals_for_date(user_id, today)

    if not meals:
        await query.answer("No meals to delete.", show_alert=True)
        return

    buttons = []
    for i, meal in enumerate(meals, 1):
        buttons.append([
            InlineKeyboardButton(
                f"🗑 #{i}: {meal['name'][:25]} ({meal['calories']} kcal)",
                callback_data=f"delmeal_{meal['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("← Back", callback_data="today_back")])

    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))


async def back_to_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return to the clean today summary from the delete menu."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    msg, keyboard = await _build_today_message(user_id)
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)


async def delete_meal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle meal deletion from today's summary."""
    query = update.callback_query
    await query.answer()
    
    meal_id = int(query.data.replace("delmeal_", ""))
    user_id = update.effective_user.id
    
    deleted = await delete_meal(meal_id, user_id)
    
    if deleted:
        # Rebuild fresh today summary (back to clean view)
        msg, keyboard = await _build_today_message(user_id)
        msg = "✅ *Meal deleted!*\n\n" + msg
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await query.answer("⚠️ Could not delete that meal.", show_alert=True)


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show this week's calorie summary."""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    today = datetime.utcnow()
    weekly = await get_meals_for_week(user_id, today)

    goal = user.get("daily_calorie_goal", 2000) if user else 2000
    weekly_goal = goal * 7

    msg = "📊 *This Week's Summary*\n\n"
    total_week = 0

    for date_str, meals in weekly.items():
        day_total = sum(m["calories"] for m in meals)
        total_week += day_total

        # Parse date for display
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = dt.strftime("%a %b %d")

        if day_total > 0:
            bar = format_progress_bar(day_total, goal, length=10)
            msg += f"*{day_name}:* {day_total} kcal {bar}\n"
        else:
            msg += f"*{day_name}:* — _no meals_\n"

    msg += (
        f"\n📈 *Weekly Total:* {total_week} kcal\n"
        f"🎯 *Weekly Goal:* {weekly_goal} kcal\n"
        f"📉 *Daily Average:* {total_week // 7} kcal\n"
    )

    diff = weekly_goal - total_week
    if diff > 0:
        msg += f"\n💡 {diff} kcal remaining this week"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show date picker for calorie history, or show specific date if arg provided."""
    # If called with a date argument (e.g. /history 2025-01-15), show it directly
    args = context.args if context.args else []
    if args:
        try:
            target_date = datetime.strptime(args[0], "%Y-%m-%d")
        except ValueError:
            await update.message.reply_text(
                "⚠️ Invalid date format. Use: /history YYYY-MM-DD\n"
                "Example: /history 2025-01-15"
            )
            return
        await _show_history_for_date(update.message, update.effective_user.id, target_date)
        return

    # No args — show date picker with last 7 days
    today = datetime.utcnow()
    buttons = []
    row = []
    for i in range(1, 8):
        d = today - timedelta(days=i)
        label = d.strftime("%a %d/%m") if i > 1 else "Yesterday"
        row.append(InlineKeyboardButton(label, callback_data=f"hist_{d.strftime('%Y-%m-%d')}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await update.message.reply_text(
        "📜 *History*\n\nSelect a date to view:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def history_date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle date selection from history picker."""
    query = update.callback_query
    await query.answer()
    date_str = query.data.replace("hist_", "")
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    await _show_history_for_date(query, update.effective_user.id, target_date, edit=True)


async def _show_history_for_date(target, user_id: int, target_date: datetime, edit: bool = False) -> None:
    """Build and send the history message for a given date."""
    user = await get_user(user_id)
    meals = await get_meals_for_date(user_id, target_date)
    goal = user.get("daily_calorie_goal", 2000) if user else 2000

    date_display = target_date.strftime("%A, %b %d %Y")
    msg = f"📜 *History — {date_display}*\n\n"

    if meals:
        total_cal = sum(m["calories"] for m in meals)
        total_protein = sum(m.get("protein_g", 0) for m in meals)
        total_carbs = sum(m.get("carbs_g", 0) for m in meals)
        total_fat = sum(m.get("fat_g", 0) for m in meals)

        for i, meal in enumerate(meals, 1):
            log_ts = meal.get("logged_at")
            if log_ts:
                time_str = log_ts.strftime("%H:%M") if hasattr(log_ts, "strftime") else str(log_ts)[11:16]
            else:
                time_str = ""
            msg += f"{i}. {meal['name']} — {meal['calories']} kcal"
            if time_str:
                msg += f" _{time_str}_"
            msg += "\n"

        msg += (
            f"\n🔥 *Total: {total_cal} / {goal} kcal*\n"
            f"{format_progress_bar(total_cal, goal)}\n\n"
            f"🥩 Protein: {total_protein:.1f}g\n"
            f"🍞 Carbs: {total_carbs:.1f}g\n"
            f"🧈 Fat: {total_fat:.1f}g"
        )
    else:
        msg += "_No meals were logged on this date._"

    if edit:
        await target.edit_message_text(msg, parse_mode="Markdown")
    else:
        await target.reply_text(msg, parse_mode="Markdown")


def get_handlers():
    """Return all tracking command handlers."""
    return [
        CommandHandler("today", today_command),
        CommandHandler("week", week_command),
        CommandHandler("history", history_command),
        CallbackQueryHandler(history_date_callback, pattern=r"^hist_"),
        CallbackQueryHandler(show_delete_menu, pattern=r"^today_delete_menu$"),
        CallbackQueryHandler(back_to_today, pattern=r"^today_back$"),
        CallbackQueryHandler(delete_meal_callback, pattern=r"^delmeal_"),
    ]
