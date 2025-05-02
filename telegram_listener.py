from telethon import TelegramClient, events
from parser import parse_signal
from trade_executor import execute_trade
from logger import log_trade, send_telegram_log
import os
from dotenv import load_dotenv

load_dotenv()

# Get credentials from environment variables
API_ID = int(os.getenv('TELEGRAM_API_ID'))
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_NAME = os.getenv('TELEGRAM_SESSION_NAME')
SIGNAL_GROUP = os.getenv('TELEGRAM_SIGNAL_GROUP')

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(chats=SIGNAL_GROUP))
async def handler(event):
    message = event.raw_text
    trade_data = parse_signal(message)
    if trade_data:
        status = execute_trade(trade_data)
        log_trade(trade_data, status)
        send_telegram_log(f"Trade Executed: {trade_data['pair']} | Status: {status}")

def start_listener():
    print("Telegram listener started...")
    client.start()
    client.run_until_disconnected()
