"""
Telegram Client Bot - User Registration and Subscription Management

This bot handles user interactions for subscribing to NITE exam notifications.
Users can select which cities they want to receive alerts for through an
interactive inline keyboard interface.

Flow:
    1. User sends /start command
    2. Bot registers user in database
    3. Bot presents city selection interface with checkboxes
    4. User toggles cities on/off
    5. User confirms selection
    6. Bot saves preferences to database

Commands:
    /start - Begin registration and city selection
    /cancel - Cancel current operation

Dependencies:
    - python-telegram-bot: Telegram Bot API wrapper
    - db: Database operations for user management
    - config: Centralized city configuration
"""

import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, CallbackQueryHandler, ContextTypes
)
from db import init_db, add_user, update_user_cities
from config import get_city_options


# ========== CONFIGURATION ==========

# Load Telegram bot token from environment variable
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("Missing TELEGRAM_TOKEN environment variable")

# Configure logging for bot operations
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation handler states for managing user flow
START, CHOOSING_CITIES = range(2)

# List of city names for UI display, loaded from central configuration
# Example: ['תל אביב', 'באר שבע', 'ירושלים', 'חיפה']
CITY_OPTIONS = get_city_options()


# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /start command - initiate user registration and city selection.
    
    Args:
        update: Telegram update object containing message and user info
        context: Bot context for storing user session data
    
    Returns:
        CHOOSING_CITIES state constant to continue conversation flow
    
    Side Effects:
        - Registers user in database (if not already registered)
        - Initializes empty city selection set in user session
        - Sends welcome message and city selection keyboard to user
    """
    user = update.effective_user
    user_id = user.id

    # Register user in database (INSERT OR IGNORE if exists)
    add_user(user_id)
    
    # Initialize user session data for tracking city selections
    context.user_data['selected_cities'] = set()

    # Send welcome messages and city selection interface
    await update.message.reply_text("ברוך הבא לבוט שלי 👋")
    await update.message.reply_text(
        "בחר ערים שעליהן תרצה לקבל התראות:",
        reply_markup=_build_city_keyboard()
    )

    return CHOOSING_CITIES


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle inline keyboard button presses (city toggles and confirmation).
    
    Args:
        update: Telegram update containing callback query
        context: Bot context with user session data
    
    Returns:
        CHOOSING_CITIES to continue selection, or END to complete conversation
    
    Callback Data Formats:
        - "city_<city_name>": Toggle city subscription (e.g., "city_תל אביב")
        - "continue": Confirm and save selections
    
    Behavior:
        - City toggle: Updates keyboard to show/hide checkmark, stays in same state
        - Continue with no cities: Shows error, stays in selection state
        - Continue with cities: Saves to DB, shows confirmation, ends conversation
    """
    query = update.callback_query
    await query.answer()  # Acknowledge button press to remove loading state

    data = query.data
    selected_cities = context.user_data.setdefault('selected_cities', set())

    if data.startswith("city_"):
        # Extract city name from callback data and toggle its selection
        _toggle_city(data[5:], selected_cities)
        # Update keyboard to reflect new selection state (add/remove checkmark)
        await query.edit_message_reply_markup(reply_markup=_build_city_keyboard(selected_cities))

    elif data == "continue":
        # Validate that at least one city is selected
        if not selected_cities:
            await query.edit_message_text("לא נבחרו ערים. אנא בחר לפחות עיר אחת.")
            return CHOOSING_CITIES

        # Save user preferences to database
        update_user_cities(update.effective_user.id, list(selected_cities))
        
        # Show confirmation message and end conversation
        await query.edit_message_text(
            f"הערים שנבחרו: {', '.join(selected_cities)}.\nההגדרות נשמרו בהצלחה ✅"
        )
        return ConversationHandler.END

    return CHOOSING_CITIES


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle /cancel command - abort current operation.
    
    Args:
        update: Telegram update object
        context: Bot context
    
    Returns:
        ConversationHandler.END to terminate conversation
    
    Note:
        User can restart registration by sending /start again.
    """
    await update.message.reply_text("הפעולה בוטלה.")
    return ConversationHandler.END


# ========== HELPERS ==========

def _build_city_keyboard(selected_cities: set[str] | None = None) -> InlineKeyboardMarkup:
    """
    Build interactive inline keyboard with city selection buttons.
    
    Args:
        selected_cities: Set of currently selected city names (Hebrew)
                        If None, creates keyboard with no selections
    
    Returns:
        InlineKeyboardMarkup with:
            - One button per city (with ✅ prefix if selected)
            - "המשך" (Continue) button at bottom
    
    Button Layout:
        Each city button has:
            - Text: "✅ city_name" if selected, else "city_name"
            - Callback data: "city_<city_name>" for toggling
        
        Continue button has:
            - Text: "המשך"
            - Callback data: "continue"
    """
    selected_cities = selected_cities or set()

    # Create one button per city, adding checkmark if selected
    keyboard = [
        [InlineKeyboardButton(f"{'✅ ' if c in selected_cities else ''}{c}", callback_data=f"city_{c}")]
        for c in CITY_OPTIONS
    ]
    
    # Add confirmation button at bottom
    keyboard.append([InlineKeyboardButton("המשך", callback_data="continue")])

    return InlineKeyboardMarkup(keyboard)


def _toggle_city(city: str, selected_cities: set[str]) -> None:
    """
    Toggle city in selection set (add if absent, remove if present).
    
    Args:
        city: Hebrew city name to toggle
        selected_cities: Mutable set to modify in-place
    
    Side Effects:
        Modifies selected_cities set directly (in-place operation)
    """
    if city in selected_cities:
        selected_cities.remove(city)
    else:
        selected_cities.add(city)


# ========== MAIN ==========

def main() -> None:
    """
    Initialize and run the Telegram client bot.
    
    Setup Process:
        1. Initialize database schema (create tables if needed)
        2. Build Telegram application with bot token
        3. Configure conversation handler with:
           - Entry point: /start command
           - States: CHOOSING_CITIES (handles inline button callbacks)
           - Fallbacks: /cancel command
        4. Start polling for updates (blocks until interrupted)
    
    Bot Behavior:
        - Listens for /start and /cancel commands
        - Handles inline keyboard button presses during city selection
        - Runs indefinitely until process is terminated
    
    Note:
        This function blocks. Use in separate process via main.py
        for parallel operation with checker bot.
    """
    # Ensure database tables exist before starting bot
    init_db()

    # Build Telegram bot application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Configure multi-step conversation flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],  # Conversation starts with /start
        states={
            CHOOSING_CITIES: [CallbackQueryHandler(handle_callback)]  # Handle button presses
        },
        fallbacks=[CommandHandler("cancel", cancel)],  # Allow user to abort
    )

    application.add_handler(conv_handler)

    logger.info("Bot started successfully.")
    application.run_polling()  # Start long-polling (blocks)


if __name__ == "__main__":
    main()
