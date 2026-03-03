"""Utility functions for the calorie tracking bot."""


def calculate_calorie_goal(
    gender: str,
    age: int,
    height_cm: float,
    weight_kg: float,
    goal_weight_kg: float,
    activity_level: str = "moderate",
) -> int:
    """
    Calculate daily calorie goal using Mifflin-St Jeor equation.

    Activity levels: sedentary, light, moderate, active, very_active
    """
    # Mifflin-St Jeor BMR
    if gender.lower() in ("male", "m"):
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    # Activity multiplier
    multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    tdee = bmr * multipliers.get(activity_level, 1.55)

    # Adjust for weight goal
    diff = goal_weight_kg - weight_kg
    if diff < -1:  # Want to lose weight
        calorie_goal = int(tdee - 500)  # ~0.5kg/week deficit
    elif diff > 1:  # Want to gain weight
        calorie_goal = int(tdee + 300)  # Lean bulk surplus
    else:
        calorie_goal = int(tdee)  # Maintain

    # Ensure minimum safe calories
    return max(calorie_goal, 1200)


def format_progress_bar(current: int, goal: int, length: int = 15) -> str:
    """Create a text-based progress bar."""
    if goal <= 0:
        return "▓" * length

    ratio = min(current / goal, 1.5)  # Cap at 150%
    filled = int(ratio * length)
    filled = min(filled, length)

    bar = "█" * filled + "░" * (length - filled)
    percentage = int(ratio * 100)

    if ratio > 1.0:
        return f"[{bar}] {percentage}% ⚠️ Over goal!"
    return f"[{bar}] {percentage}%"


def format_meal_summary(meal: dict) -> str:
    """Format a meal for display."""
    name = meal.get("name", "Unknown")
    calories = meal.get("calories", 0)
    protein = meal.get("protein_g", 0)
    carbs = meal.get("carbs_g", 0)
    fat = meal.get("fat_g", 0)

    return (
        f"🍽 *{name}*\n"
        f"   🔥 {calories} kcal\n"
        f"   🥩 Protein: {protein}g | 🍞 Carbs: {carbs}g | 🧈 Fat: {fat}g"
    )


def format_estimate_message(estimate: dict) -> str:
    """Format an AI estimate for display with action prompt."""
    name = estimate.get("name", "Unknown")
    desc = estimate.get("description", "")
    calories = estimate.get("calories", 0)
    protein = estimate.get("protein_g", 0)
    carbs = estimate.get("carbs_g", 0)
    fat = estimate.get("fat_g", 0)

    msg = (
        f"🔍 *Calorie Estimate*\n\n"
        f"*{name}*\n"
    )
    if desc:
        msg += f"_{desc}_\n"
    msg += (
        f"\n"
        f"🔥 *Calories:* {calories} kcal\n"
        f"🥩 *Protein:* {protein}g\n"
        f"🍞 *Carbs:* {carbs}g\n"
        f"🧈 *Fat:* {fat}g\n"
        f"\n"
        f"What would you like to do?"
    )
    return msg


ACTIVITY_LEVEL_LABELS = {
    "sedentary": "🪑 Sedentary (little/no exercise)",
    "light": "🚶 Lightly Active (1-3 days/week)",
    "moderate": "🏃 Moderately Active (3-5 days/week)",
    "active": "💪 Active (6-7 days/week)",
    "very_active": "🏋️ Very Active (2x/day or physical job)",
}

GENDER_LABELS = {
    "male": "♂️ Male",
    "female": "♀️ Female",
}

# Regex to match any of the main menu buttons
MENU_BUTTONS_REGEX = r"^(🍱 Log Meal|📊 Today|📈 Week|📋 Saved|👤 Profile)$"


async def send_help_message(update, context=None):
    """Common utility to send command list and menu."""
    help_text = (
        "❓ *Not sure what that means!*\n\n"
        "Here are the available commands:\n\n"
        "🍱 /log — Log a meal \\(text or photo\\)\n"
        "📊 /today — Check today's progress\n"
        "📈 /week — See weekly history\n"
        "👤 /profile — View or update your settings\n"
        "📋 /saved — Browse your saved meals\n"
        "🎯 /goal — View or set your calorie goal\n"
        "📜 /history — View a past date\n"
        "🔔 /reminder — Set meal reminders\n\n"
        "_Tap /log first if you want to describe a meal\\!_"
    )
    
    # Lazy import to avoid circular dependency
    from handlers.start import MENU_KEYBOARD
    
    if update.message:
        await update.message.reply_text(
            help_text, parse_mode="Markdown", reply_markup=MENU_KEYBOARD
        )
    elif update.callback_query:
        # Use query.message to reply if it's a callback
        await update.callback_query.message.reply_text(
            help_text, parse_mode="Markdown", reply_markup=MENU_KEYBOARD
        )
