"""Handler for /goal - view or set daily calorie goal."""

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from database import get_user, upsert_user


async def goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View or update daily calorie goal."""
    user_id = update.effective_user.id
    user = await get_user(user_id)
    args = context.args

    if args:
        # Set new goal
        try:
            new_goal = int(args[0])
            if not 800 <= new_goal <= 10000:
                raise ValueError
        except (ValueError, IndexError):
            await update.message.reply_text(
                "⚠️ Please enter a valid calorie goal (800-10000).\n"
                "Usage: /goal 2000"
            )
            return

        await upsert_user(user_id, daily_calorie_goal=new_goal)
        await update.message.reply_text(
            f"✅ Daily calorie goal updated to *{new_goal} kcal*!",
            parse_mode="Markdown",
        )
    else:
        # Show current goal
        if user and user.get("daily_calorie_goal"):
            goal = user["daily_calorie_goal"]
            await update.message.reply_text(
                f"🎯 *Your Daily Calorie Goal:* {goal} kcal\n\n"
                f"To change it: /goal <amount>\n"
                f"Example: `/goal 2000`",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "🎯 You haven't set a calorie goal yet.\n\n"
                "Set one with: /goal <amount>\n"
                "Example: `/goal 2000`\n\n"
                "Or use /profile to calculate one based on your stats!",
                parse_mode="Markdown",
            )


def get_handler():
    """Return the goal command handler."""
    return CommandHandler("goal", goal_command)
