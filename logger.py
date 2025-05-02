import csv
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
import json
import time
from enum import Enum

load_dotenv()

class TradeStatus(Enum):
    SIGNAL = "📡 Signal"
    ORDER_PLACED = "✅ Order"
    STOPS_SET = "🎯 Stops"
    ERROR = "❌ Error"

def send_telegram_log(message, keyboard=None):
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            raise ValueError("Missing Telegram configuration")
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        if keyboard:
            data["reply_markup"] = json.dumps(keyboard)
        
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200, "Message sent successfully"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

def format_signal_message(trade_data):
    """Format initial signal notification"""
    entry_range = f"{trade_data['entry_range'][0]} - {trade_data['entry_range'][1]}" if isinstance(trade_data['entry_range'], list) else trade_data['entry_range']
    
    return f"""
📡 <b>New Signal</b>

{trade_data['direction'].upper()} {trade_data['pair']}
Entry: {entry_range}
SL: {trade_data['stop_loss']}
TP: {', '.join(str(t) for t in trade_data['targets'])}
    """.strip()

def format_order_message(trade_data, order_id, position_info):
    """Format order placement notification"""
    return f"""
✅ <b>Order Placed</b>

{trade_data['direction'].upper()} {trade_data['pair']}
Entry: {position_info['avgPrice']}
Size: {position_info['size']}
ID: {order_id}
    """.strip()

def format_stops_message(trade_data, stop_loss, take_profit):
    """Format stops confirmation"""
    return f"""
🎯 <b>Stops Confirmed</b>

{trade_data['pair']}
SL: {stop_loss}
TP: {take_profit}
    """.strip()

def notify_error(error_message):
    """Send error notification"""
    message = f"""
❌ <b>Error</b>

{error_message}
    """.strip()
    
    return send_telegram_log(message)

def get_positions_keyboard():
    """Create inline keyboard for checking positions"""
    return {
        "inline_keyboard": [
            [{"text": "📊 Check Open Positions", "callback_data": "check_positions"}]
        ]
    }

def format_positions_message(positions):
    """Format open positions message"""
    if not positions:
        return "No open positions"
    
    message = "📊 <b>Open Positions</b>\n\n"
    for pos in positions:
        pnl = float(pos.get('unrealisedPnl', 0))
        pnl_str = f"+{pnl:.2f}" if pnl > 0 else f"{pnl:.2f}"
        pnl_emoji = "📈" if pnl > 0 else "📉" if pnl < 0 else "➖"
        
        message += f"{pnl_emoji} {pos['symbol']}\n"
        message += f"Side: {pos['side']}\n"
        message += f"Size: {pos['size']}\n"
        message += f"Entry: {pos['avgPrice']}\n"
        message += f"PnL: {pnl_str} USDT\n\n"
    
    return message.strip()

def log_trade(trade_data, status):
    """Simple trade logging to CSV"""
    try:
        with open("trade_logs.csv", "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                datetime.now().isoformat(),
                trade_data["pair"],
                trade_data["direction"],
                json.dumps(trade_data["entry_range"]),
                json.dumps(trade_data["targets"]),
                trade_data["stop_loss"],
                status
            ])
        return True, "Trade logged"
    except Exception as e:
        return False, f"Log error: {str(e)}"
