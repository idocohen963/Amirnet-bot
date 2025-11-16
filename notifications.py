"""
Telegram Notifications Module

This module handles sending Telegram messages to users.
It provides a clean interface for notification delivery.

Responsibilities:
    - Sending Telegram messages via Bot API
    - Error handling for failed message deliveries
    - Logging notification attempts

Dependencies:
    - requests: HTTP client for Telegram Bot API
    - logging: Operation logging
    - os: Environment variable access
"""

import os
import logging
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Telegram bot token for sending notifications
# Must be set in .env file as TELEGRAM_TOKEN
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("Missing TELEGRAM_TOKEN environment variable")


def send_telegram_message(user_id: int, text: str) -> bool:
    """
    Send a Telegram message to a specific user.
    
    Args:
        user_id: Telegram user ID (chat_id)
        text: Message content in Hebrew
    
    Returns:
        True if message sent successfully, False otherwise
    
    Side Effects:
        - Makes HTTP POST request to Telegram Bot API
        - Logs success or failure
    
    Error Handling:
        Catches and logs RequestException but does not raise.
        Failed messages do not stop the bot from continuing.
    
    Note:
        Uses global TELEGRAM_TOKEN for authentication.
        10-second timeout to prevent hanging.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": user_id, "text": text}
    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
        logger.info(f"Message successfully sent to user {user_id}.")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send message to user {user_id}: {e}")
        return False

