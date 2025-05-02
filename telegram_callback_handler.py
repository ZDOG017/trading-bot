from telethon import TelegramClient, events
from trade_executor import get_open_positions
from logger import send_telegram_log, format_positions_message, get_positions_keyboard
from dotenv import load_dotenv
import os
import json

load_dotenv()

# Get credentials from environment variables
API_ID = int(os.getenv('TELEGRAM_API_ID'))
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize the client
client = TelegramClient('bot_session', API_ID, API_HASH)

@client.on(events.CallbackQuery())
async def callback_handler(event):
    try:
        if event.data == b'check_positions':
            # Get open positions
            positions = get_open_positions()
            
            # Format and send positions message
            message = format_positions_message(positions)
            
            # Answer the callback query (removes loading state)
            await event.answer()
            
            # Edit the message to show positions
            await event.edit(
                message,
                buttons=get_positions_keyboard()
            )
    except Exception as e:
        print(f"Error handling callback: {e}")
        await event.answer("Error getting positions", alert=True)

def start_callback_handler():
    """Start the callback handler"""
    print("Starting callback handler...")
    client.run_until_disconnected() 