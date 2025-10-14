"""
Telegram bot for managing user subscriptions to exam notifications.
"""

import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, CallbackQueryHandler, ContextTypes
)
from db import init_db, add_user, update_user_cities


# ========== CONFIGURATION ==========

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "token")
if not TELEGRAM_TOKEN:
    raise ValueError("Missing TELEGRAM_TOKEN environment variable")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
START, CHOOSING_CITIES = range(2)

# City options
CITY_OPTIONS = ["תל אביב", "באר שבע", "ירושלים", "חיפה"]


# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command: add user and ask for city selection."""
    user = update.effective_user
    user_id = user.id

    add_user(user_id)
    context.user_data['selected_cities'] = set()

    await update.message.reply_text("ברוך הבא לבוט שלי 👋")
    await update.message.reply_text(
        "בחר ערים שעליהן תרצה לקבל התראות:",
        reply_markup=_build_city_keyboard()
    )

    return CHOOSING_CITIES


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle city selection and confirmation."""
    query = update.callback_query
    await query.answer()

    data = query.data
    selected_cities = context.user_data.setdefault('selected_cities', set())

    if data.startswith("city_"):
        _toggle_city(data[5:], selected_cities)
        await query.edit_message_reply_markup(reply_markup=_build_city_keyboard(selected_cities))

    elif data == "continue":
        if not selected_cities:
            await query.edit_message_text("לא נבחרו ערים. אנא בחר לפחות עיר אחת.")
            return CHOOSING_CITIES

        update_user_cities(update.effective_user.id, list(selected_cities))
        await query.edit_message_text(
            f"הערים שנבחרו: {', '.join(selected_cities)}.\nההגדרות נשמרו בהצלחה ✅"
        )
        return ConversationHandler.END

    return CHOOSING_CITIES


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel command: end the conversation."""
    await update.message.reply_text("הפעולה בוטלה.")
    return ConversationHandler.END


# ========== HELPERS ==========

def _build_city_keyboard(selected_cities: set[str] | None = None) -> InlineKeyboardMarkup:
    """Build the dynamic inline keyboard of city options."""
    selected_cities = selected_cities or set()

    keyboard = [
        [InlineKeyboardButton(f"{'✅ ' if c in selected_cities else ''}{c}", callback_data=f"city_{c}")]
        for c in CITY_OPTIONS
    ]
    keyboard.append([InlineKeyboardButton("המשך", callback_data="continue")])

    return InlineKeyboardMarkup(keyboard)


def _toggle_city(city: str, selected_cities: set[str]) -> None:
    """Toggle city selection on/off."""
    if city in selected_cities:
        selected_cities.remove(city)
    else:
        selected_cities.add(city)


# ========== MAIN ==========

def main() -> None:
    """Run the Telegram bot."""
    init_db()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={CHOOSING_CITIES: [CallbackQueryHandler(handle_callback)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    logger.info("Bot started successfully.")
    application.run_polling()


if __name__ == "__main__":
    main()
