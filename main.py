# Udemy Coupon Scraper & Cloner Bot
# This bot clones messages but now includes FILTERS for language and category.
# It only forwards courses that are in English AND match a target category.

import os
import re
import logging
from telethon import TelegramClient, events

# --- Basic Logging Configuration ---
logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.INFO)

# --- Configuration from Environment Variables ---
API_ID = os.environ.get('API_ID')
API_HASH = os.environ.get('API_HASH')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
SOURCE_CHANNEL = os.environ.get('SOURCE_CHANNEL')
DESTINATION_CHANNEL = os.environ.get('DESTINATION_CHANNEL')

# --- FILTERING CONFIGURATION ---
# Define the categories and language you want to forward.
# Using a set for categories makes lookups very fast.
TARGET_CATEGORIES = {"#it_and_software", "#development", "#programming"}
TARGET_LANGUAGE = "#english"


# --- Input Validation ---
def validate_config():
    """Checks if all necessary configuration variables are set."""
    required_vars = {
        'API_ID': API_ID, 'API_HASH': API_HASH, 'BOT_TOKEN': BOT_TOKEN,
        'SOURCE_CHANNEL': SOURCE_CHANNEL, 'DESTINATION_CHANNEL': DESTINATION_CHANNEL
    }
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    global SOURCE_CHANNEL, DESTINATION_CHANNEL
    try:
        # Allow usernames (non-digit) for source, but convert IDs to int
        if not SOURCE_CHANNEL.lstrip('-').isdigit(): pass
        else: SOURCE_CHANNEL = int(SOURCE_CHANNEL)
        DESTINATION_CHANNEL = int(DESTINATION_CHANNEL)
    except (ValueError, AttributeError):
        # AttributeError handles case where a variable might be None
        raise ValueError("Channel IDs must be valid integers or a public username for the source.")

# --- Regex to find Udemy URLs ---
UDEMY_URL_PATTERN = re.compile(r'https?://www\.udemy\.com/course/[^/\s]+/\?couponCode=[\w-]+')

# --- Initialize the Bot Client ---
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def coupon_handler(event):
    """
    Handles new messages, filters them by category and language,
    cleans them, and forwards them.
    """
    message = event.message
    
    # Ignore messages without text, as they can't be filtered
    if not message.text:
        return

    # 1. Primary Check: Find the Udemy URL from the "Enroll Course" button.
    udemy_url = None
    if message.buttons:
        for row in message.buttons:
            for button in row:
                # Use getattr for safe access to attributes
                button_url = getattr(getattr(button, 'button', None), 'url', None)
                if button_url and 'enroll' in button.text.lower():
                    if UDEMY_URL_PATTERN.search(button_url):
                        udemy_url = button_url
                        break
            if udemy_url: break

    if not udemy_url:
        logging.info("Message does not contain a valid Udemy 'Enroll' button. Skipping.")
        return

    # 2. FILTERING LOGIC
    message_text_lower = message.text.lower()
    has_target_language = False
    has_target_category = False

    # Check each line for our filter criteria
    for line in message_text_lower.split('\n'):
        stripped_line = line.strip()
        if stripped_line.startswith('language:') and TARGET_LANGUAGE in stripped_line:
            has_target_language = True
        if stripped_line.startswith('category:'):
            if any(cat in stripped_line for cat in TARGET_CATEGORIES):
                has_target_category = True

    # If it doesn't meet BOTH criteria, skip it.
    if not (has_target_language and has_target_category):
        logging.info(f"Skipping post. Language match: {has_target_language}, Category match: {has_target_category}.")
        return

    # 3. Clean the message text (Remove "Join" lines)
    cleaned_lines = [
        line for line in message.text.split('\n')
        if not line.strip().lower().startswith("join ")
    ]
    modified_text = '\n'.join(cleaned_lines)

    # 4. Filter the inline buttons (Remove "Join" or "Share")
    new_keyboard = []
    if message.buttons:
        for row in message.buttons:
            new_row = []
            for button in row:
                button_text = button.text.lower()
                if 'join' not in button_text and 'share' not in button_text:
                    new_row.append(button)
            if new_row:
                new_keyboard.append(new_row)

    # 5. Send the final, filtered, and cleaned message
    try:
        await bot.send_message(
            DESTINATION_CHANNEL,
            message=modified_text,
            file=message.media,
            buttons=new_keyboard if new_keyboard else None,
            link_preview=False
        )
        logging.info(f"Successfully filtered and forwarded a coupon post.")
    except Exception as e:
        logging.error(f"Failed to send the cloned message: {e}")

async def main():
    """Main function to start the bot."""
    try:
        validate_config()
        logging.info("Bot configuration is valid.")
        logging.info(f"Filtering for categories: {TARGET_CATEGORIES}")
        logging.info(f"Filtering for language: {TARGET_LANGUAGE}")
        logging.info("Bot is running and connected to Telegram...")
        await bot.run_until_disconnected()
    except ValueError as e:
        logging.critical(f"CONFIGURATION ERROR: {e}. The bot will not start.")
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    bot.loop.run_until_complete(main())

