"""Handler for /profile - multi-step profile setup conversation."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import logging
from database import get_user, upsert_user
from utils import (
    calculate_calorie_goal,
    ACTIVITY_LEVEL_LABELS,
    GENDER_LABELS,
    MENU_BUTTONS_REGEX,
)

logger = logging.getLogger(__name__)

# Conversation states
GENDER, AGE, HEIGHT, WEIGHT, GOAL_WEIGHT, ACTIVITY, CONFIRM_GOAL, SELECT_SECTION = range(8)


async def profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start profile setup or show existing profile."""
    # Check if this was a direct "Update" button press from an old session
    query = update.callback_query
    
    # If this is /start, show a welcome message first if they are new
    is_start = update.message and update.message.text and update.message.text.startswith("/start")
    
    if query:
        await query.answer()
        logger.info(f"Direct profile entry from query: {query.data}")
        if query.data == "profile_update":
            logger.info("Starting section-based update menu")
            return await _show_sections_menu(update, context)
        elif query.data == "profile_keep":
            logger.info("Keeping current profile")
            await query.edit_message_text("✅ Profile unchanged!")
            return ConversationHandler.END
        elif query.data == "profile_full_restart":
            logger.info("Starting full profile restart")
            context.user_data["is_editing"] = False
            await query.edit_message_text(
                "Let's do a full profile setup!\n\nWhat is your gender?",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("♂️ Male", callback_data="gender_male"),
                            InlineKeyboardButton("♀️ Female", callback_data="gender_female"),
                        ]
                    ]
                ),
            )
            return GENDER

    user_id = update.effective_user.id
    user = await get_user(user_id)

    if user and user.get("age"):
        if is_start:
            from handlers.start import MENU_KEYBOARD
            welcome = (
                "👋 *Welcome back to CalorieBot!*\n\n"
                "I'm ready to help you track your calories.\n\n"
                "🚀 *Quick Tips:*\n"
                "• Send a photo or description to log a meal\n"
                "• Tap 📊 Today to check your progress\n"
                "• Use 👤 Profile to view or update your stats"
            )
            await update.effective_message.reply_text(
                welcome, parse_mode="Markdown", reply_markup=MENU_KEYBOARD
            )
            return ConversationHandler.END
            
        # Show existing profile with option to re-do
        goal = user.get("daily_calorie_goal", "Not set")
        msg = (
            f"📊 *Your Profile*\n\n"
            f"👤 Gender: {GENDER_LABELS.get(user.get('gender', ''), user.get('gender', 'N/A'))}\n"
            f"🎂 Age: {user.get('age', 'N/A')}\n"
            f"📏 Height: {user.get('height_cm', 'N/A')} cm\n"
            f"⚖️ Weight: {user.get('weight_kg', 'N/A')} kg\n"
            f"🎯 Goal Weight: {user.get('goal_weight_kg', 'N/A')} kg\n"
            f"🏃 Activity: {ACTIVITY_LEVEL_LABELS.get(user.get('activity_level', ''), user.get('activity_level', 'N/A'))}\n"
            f"🔥 Daily Goal: {goal} kcal\n\n"
            f"Would you like to update your profile?"
        )
        keyboard = [
            [
                InlineKeyboardButton("✏️ Update", callback_data="profile_update"),
                InlineKeyboardButton("❌ Keep", callback_data="profile_keep"),
            ]
        ]
        await update.effective_message.reply_text(
            msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CONFIRM_GOAL
    else:
        logger.info(f"Starting new profile setup for user {user_id}")
        
        prefix = ""
        if is_start:
            prefix = (
                "👋 *Welcome to CalorieBot!*\n\n"
                "I help you track your daily calorie intake using AI. "
                "To get started, I need to ask a few questions to set up your profile.\n\n"
            )
            
        await update.effective_message.reply_text(
            f"{prefix}What is your gender?",
            parse_mode="Markdown" if prefix else None,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("♂️ Male", callback_data="gender_male"),
                        InlineKeyboardButton("♀️ Female", callback_data="gender_female"),
                    ]
                ]
            ),
        )
        return GENDER


async def _show_sections_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Helper to display the section selection menu for editing."""
    query = update.callback_query
    # Load user stats into context to ensure we have initials to modify
    user = await get_user(update.effective_user.id)
    if user:
        context.user_data.update(user)
    context.user_data["is_editing"] = True
    
    keyboard = [
        [InlineKeyboardButton("♂️ Gender", callback_data="edit_gender"), InlineKeyboardButton("🎂 Age", callback_data="edit_age")],
        [InlineKeyboardButton("📏 Height", callback_data="edit_height"), InlineKeyboardButton("⚖️ Weight", callback_data="edit_weight")],
        [InlineKeyboardButton("🎯 Goal Weight", callback_data="edit_goal_weight"), InlineKeyboardButton("🏃 Activity", callback_data="edit_activity")],
        [InlineKeyboardButton("🔄 Full Update", callback_data="profile_full_restart")],
        [InlineKeyboardButton("❌ Cancel", callback_data="profile_keep")]
    ]
    
    msg = "What would you like to update?"
    if query:
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        
    return SELECT_SECTION


async def gender_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle gender selection."""
    query = update.callback_query
    await query.answer()
    gender = query.data.replace("gender_", "")
    context.user_data["gender"] = gender

    await query.edit_message_text(
        f"Gender: {GENDER_LABELS[gender]} ✅\n\n"
        f"🎂 How old are you? (Enter a number)"
    )
    
    if context.user_data.get("is_editing"):
        await _save_single_update(update, context)
        return ConversationHandler.END
        
    return AGE


async def section_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle section selection for editing."""
    query = update.callback_query
    await query.answer()
    
    section = query.data.replace("edit_", "")
    
    if section == "gender":
        await query.edit_message_text(
            "What is your gender?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("♂️ Male", callback_data="gender_male"),
                        InlineKeyboardButton("♀️ Female", callback_data="gender_female"),
                    ]
                ]
            ),
        )
        return GENDER
    elif section == "age":
        await query.edit_message_text("🎂 How old are you? (Enter a number)")
        return AGE
    elif section == "height":
        await query.edit_message_text("📏 What is your height in cm? (e.g., 175)")
        return HEIGHT
    elif section == "weight":
        await query.edit_message_text("⚖️ What is your current weight in kg? (e.g., 70)")
        return WEIGHT
    elif section == "goal_weight":
        await query.edit_message_text("🎯 What is your goal weight in kg? (e.g., 65)")
        return GOAL_WEIGHT
    elif section == "activity":
        keyboard = [[InlineKeyboardButton(label, callback_data=f"activity_{key}")] for key, label in ACTIVITY_LEVEL_LABELS.items()]
        await query.edit_message_text("🏃 What is your activity level?", reply_markup=InlineKeyboardMarkup(keyboard))
        return ACTIVITY
        
    return SELECT_SECTION


async def age_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle age input."""
    try:
        age = int(update.message.text.strip())
        if not 10 <= age <= 120:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid age (10-120):")
        return AGE

    context.user_data["age"] = age
    
    if context.user_data.get("is_editing"):
        await _save_single_update(update, context)
        return ConversationHandler.END
        
    await update.message.reply_text(
        f"Age: {age} ✅\n\n📏 What is your height in cm? (e.g., 175)"
    )
    return HEIGHT


async def height_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle height input."""
    try:
        height = float(update.message.text.strip())
        if not 50 <= height <= 300:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid height in cm (50-300):")
        return HEIGHT

    context.user_data["height_cm"] = height
    
    if context.user_data.get("is_editing"):
        await _save_single_update(update, context)
        return ConversationHandler.END
        
    await update.message.reply_text(
        f"Height: {height} cm ✅\n\n⚖️ What is your current weight in kg? (e.g., 70)"
    )
    return WEIGHT


async def weight_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle weight input."""
    try:
        weight = float(update.message.text.strip())
        if not 20 <= weight <= 500:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid weight in kg (20-500):")
        return WEIGHT

    context.user_data["weight_kg"] = weight
    
    if context.user_data.get("is_editing"):
        await _save_single_update(update, context)
        return ConversationHandler.END
        
    await update.message.reply_text(
        f"Weight: {weight} kg ✅\n\n"
        f"🎯 What is your goal weight in kg? (e.g., 65)"
    )
    return GOAL_WEIGHT


async def goal_weight_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle goal weight input."""
    try:
        goal = float(update.message.text.strip())
        if not 20 <= goal <= 500:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid goal weight in kg (20-500):")
        return GOAL_WEIGHT

    context.user_data["goal_weight_kg"] = goal
    
    if context.user_data.get("is_editing"):
        await _save_single_update(update, context)
        return ConversationHandler.END

    # Show activity level options
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"activity_{key}")]
        for key, label in ACTIVITY_LEVEL_LABELS.items()
    ]
    await update.message.reply_text(
        f"Goal Weight: {goal} kg ✅\n\n🏃 What is your activity level?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ACTIVITY


async def activity_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle activity level selection and calculate goal."""
    query = update.callback_query
    await query.answer()
    activity = query.data.replace("activity_", "")
    context.user_data["activity_level"] = activity

    # Calculate calorie goal
    data = context.user_data
    calorie_goal = calculate_calorie_goal(
        gender=data["gender"],
        age=data["age"],
        height_cm=data["height_cm"],
        weight_kg=data["weight_kg"],
        goal_weight_kg=data["goal_weight_kg"],
        activity_level=activity,
    )
    context.user_data["daily_calorie_goal"] = calorie_goal
    
    if context.user_data.get("is_editing"):
        await _save_single_update(update, context)
        return ConversationHandler.END

    diff = data["goal_weight_kg"] - data["weight_kg"]
    if diff < -1:
        strategy = "lose weight (500 kcal deficit)"
    elif diff > 1:
        strategy = "gain weight (300 kcal surplus)"
    else:
        strategy = "maintain weight"

    keyboard = [
        [
            InlineKeyboardButton("✅ Accept", callback_data="goal_accept"),
            InlineKeyboardButton("✏️ Custom", callback_data="goal_custom"),
        ]
    ]
    await query.edit_message_text(
        f"📊 *Profile Summary*\n\n"
        f"👤 {GENDER_LABELS[data['gender']]}\n"
        f"🎂 Age: {data['age']}\n"
        f"📏 Height: {data['height_cm']} cm\n"
        f"⚖️ Weight: {data['weight_kg']} kg\n"
        f"🎯 Goal: {data['goal_weight_kg']} kg ({strategy})\n"
        f"🏃 Activity: {ACTIVITY_LEVEL_LABELS[activity]}\n\n"
        f"🔥 *Recommended Daily Calories: {calorie_goal} kcal*\n\n"
        f"Accept this goal or set a custom value?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CONFIRM_GOAL


async def goal_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle goal acceptance or custom input."""
    query = update.callback_query
    await query.answer()
    import logging
    logging.getLogger(__name__).info(f"Profile callback received: {query.data}")

    if query.data == "profile_keep":
        await query.edit_message_text("✅ Profile unchanged!")
        return ConversationHandler.END

    if query.data == "profile_update":
        return await _show_sections_menu(update, context)

    if query.data == "goal_accept":
        # Save everything
        data = context.user_data
        await upsert_user(
            update.effective_user.id,
            name=update.effective_user.full_name,
            gender=data["gender"],
            age=data["age"],
            height_cm=data["height_cm"],
            weight_kg=data["weight_kg"],
            goal_weight_kg=data["goal_weight_kg"],
            activity_level=data["activity_level"],
            daily_calorie_goal=data["daily_calorie_goal"],
        )
        await query.edit_message_text(
            f"✅ *Profile saved!*\n\n"
            f"Your daily calorie goal is *{data['daily_calorie_goal']} kcal*.\n\n"
            f"Start logging meals by sending me a food photo or description!",
            parse_mode="Markdown",
        )
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == "goal_custom":
        await query.edit_message_text(
            "💡 Enter your custom daily calorie goal (e.g., 2000):"
        )
        return CONFIRM_GOAL

    return CONFIRM_GOAL


async def custom_goal_entered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom calorie goal input."""
    try:
        goal = int(update.message.text.strip())
        if not 800 <= goal <= 10000:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid calorie goal (800-10000):")
        return CONFIRM_GOAL

    context.user_data["daily_calorie_goal"] = goal

    # Save everything
    data = context.user_data
    await upsert_user(
        update.effective_user.id,
        name=update.effective_user.full_name,
        gender=data["gender"],
        age=data["age"],
        height_cm=data["height_cm"],
        weight_kg=data["weight_kg"],
        goal_weight_kg=data["goal_weight_kg"],
        activity_level=data["activity_level"],
        daily_calorie_goal=goal,
    )
    await update.message.reply_text(
        f"✅ *Profile saved!*\n\n"
        f"Your daily calorie goal is *{goal} kcal*.\n\n"
        f"Start logging meals by sending me a food photo or description!",
        parse_mode="Markdown",
    )
    context.user_data.clear()
    return ConversationHandler.END


async def _save_single_update(update, context):
    """Save a single updated field and re-calculate goal if needed."""
    data = context.user_data
    user_id = update.effective_user.id
    
    # Recalculate goal
    new_goal = calculate_calorie_goal(
        gender=data["gender"],
        age=data["age"],
        height_cm=data["height_cm"],
        weight_kg=data["weight_kg"],
        goal_weight_kg=data["goal_weight_kg"],
        activity_level=data["activity_level"],
    )
    
    await upsert_user(
        user_id,
        name=update.effective_user.full_name,
        gender=data["gender"],
        age=data["age"],
        height_cm=data["height_cm"],
        weight_kg=data["weight_kg"],
        goal_weight_kg=data["goal_weight_kg"],
        activity_level=data["activity_level"],
        daily_calorie_goal=new_goal,
    )
    
    msg = f"✅ *Profile field updated!*\n\nNew daily goal: *{new_goal} kcal*\n\nUse /profile to see your full summary."
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    context.user_data.clear()


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the profile setup and show help."""
    from utils import send_help_message
    await send_help_message(update, context)
    context.user_data.clear()
    return ConversationHandler.END


def get_handler():
    """Return the ConversationHandler for profile setup."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("profile", profile_start),
            CommandHandler("start", profile_start),
            MessageHandler(filters.Regex("^👤 Profile$"), profile_start),
            CallbackQueryHandler(profile_start, pattern=r"^(profile_update|profile_keep)$"),
        ],
        states={
            GENDER: [CallbackQueryHandler(gender_selected, pattern=r"^gender_")],
            AGE: [MessageHandler(filters.Regex(r"^\d+$") & ~filters.COMMAND, age_entered)],
            HEIGHT: [MessageHandler(filters.Regex(r"^\d+(\.\d+)?$") & ~filters.COMMAND, height_entered)],
            WEIGHT: [MessageHandler(filters.Regex(r"^\d+(\.\d+)?$") & ~filters.COMMAND, weight_entered)],
            GOAL_WEIGHT: [
                MessageHandler(filters.Regex(r"^\d+(\.\d+)?$") & ~filters.COMMAND, goal_weight_entered)
            ],
            ACTIVITY: [
                CallbackQueryHandler(activity_selected, pattern=r"^activity_")
            ],
            CONFIRM_GOAL: [
                CallbackQueryHandler(goal_confirmed, pattern=r"^(goal_|profile_)"),
                MessageHandler(filters.Regex(r"^\d+$") & ~filters.COMMAND, custom_goal_entered),
            ],
            SELECT_SECTION: [
                 CallbackQueryHandler(section_selected, pattern=r"^edit_"),
                 CallbackQueryHandler(profile_start, pattern=r"^profile_"),
                 CallbackQueryHandler(gender_selected, pattern=r"^gender_"),
                 CallbackQueryHandler(goal_confirmed, pattern=r"^goal_"),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            # Any unmatched text that is NOT a menu button ends the flow and triggers help
            MessageHandler(filters.TEXT & (~filters.Regex(MENU_BUTTONS_REGEX)), cancel)
        ],
        per_message=False,
        allow_reentry=True,
    )
