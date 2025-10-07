# Simple Telegram Cloner Bot
# This version forwards ALL messages and performs basic cleaning.
# All complex filters have been removed for reliability.

import os
import re
import logging
import threading
import http.server
import socketserver
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

# --- Web Server for Render ---
def run_web_server():
    PORT = int(os.environ.get('PORT', 10000))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        logging.info(f"Dummy web server started on port {PORT} to keep Render service alive.")
        httpd.serve_forever()

# --- Input Validation ---
def validate_config():
    """Checks if all necessary configuration variables are set."""
    global SOURCE_CHANNEL, DESTINATION_CHANNEL
    required_vars = {
        'API_ID': API_ID, 'API_HASH': API_HASH, 'BOT_TOKEN': BOT_TOKEN,
        'SOURCE_CHANNEL': SOURCE_CHANNEL, 'DESTINATION_CHANNEL': DESTINATION_CHANNEL
    }
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    try:
        if not SOURCE_CHANNEL.lstrip('-').isdigit(): pass
        else: SOURCE_CHANNEL = int(SOURCE_CHANNEL)
        DESTINATION_CHANNEL = int(DESTINATION_CHANNEL)
    except ValueError:
        raise ValueError("DESTINATION_CHANNEL must be a valid integer ID. SOURCE_CHANNEL can be an integer ID or a public @username.")

# --- Initialize the Bot Client ---
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@bot.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def message_handler(event):
    """
    Handles ALL new messages, cleans them, and forwards them.
    No more complex filtering.
    """
    logging.info("New message received. Processing...")
    message = event.message

    # --- Text Cleaning: Remove any line that starts with "join" ---
    cleaned_lines = []
    if message.text:
        cleaned_lines = [
            line for line in message.text.split('\n')
            if not line.strip().lower().startswith("join ")
        ]
    modified_text = '\n'.join(cleaned_lines)

    # --- Button Cleaning: Remove buttons with "join" or "share" ---
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

    # --- Forward the Message ---
    try:
        await bot.send_message(
            DESTINATION_CHANNEL,
            message=modified_text,
            file=message.media,
            buttons=new_keyboard if new_keyboard else None,
            link_preview=False
        )
        logging.info("Successfully cleaned and forwarded the message.")
    except Exception as e:
        logging.error(f"Failed to send the cloned message: {e}")

async def main():
    """Main function to start the bot."""
    try:
        validate_config()
        logging.info("Bot configuration is valid.")
        logging.info("BOT MODE: Simple Forwarder. All messages will be processed.")
        logging.info("Bot is running and connected to Telegram...")
        await bot.run_until_disconnected()
    except ValueError as e:
        logging.critical(f"CONFIGURATION ERROR: {e}. The bot will not start.")
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    bot.loop.run_until_complete(main())

