import os
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import time
from logger import (
    log_trade, 
    send_telegram_log, 
    format_signal_message,
    format_order_message,
    format_stops_message,
    notify_error,
    format_positions_message,
    get_positions_keyboard
)

load_dotenv()

# Force testnet-demo environment
os.environ["BYBIT_ENVIRONMENT"] = "testnet-demo"

# Environment settings
ENVIRONMENTS = {
    "mainnet": {"demo": False, "testnet": False},
    "testnet": {"demo": False, "testnet": True},
    "mainnet-demo": {"demo": True, "testnet": False},
    "testnet-demo": {"demo": True, "testnet": True}
}

def create_session():
    env_name = os.getenv("BYBIT_ENVIRONMENT", "testnet-demo")
    env_settings = ENVIRONMENTS.get(env_name, ENVIRONMENTS["testnet-demo"])
    
    return HTTP(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        testnet=env_settings["testnet"],
        demo=env_settings["demo"]
    )

def test_connection():
    try:
        session = create_session()
        env_name = os.getenv("BYBIT_ENVIRONMENT", "testnet-demo")
        print(f"Testing connection to Bybit {env_name}...")
        
        # Try to get wallet balance as a connection test
        result = session.get_wallet_balance(accountType="UNIFIED")
        if result["retCode"] == 0:
            return True, "Connection successful"
        return False, f"Connection failed: {result['retMsg']}"
    except Exception as e:
        return False, f"Connection error: {str(e)}"

session = create_session()

def get_wallet_balance():
    try:
        response = session.get_wallet_balance(accountType="UNIFIED")
        if response["retCode"] == 0:
            return float(response["result"]["list"][0]["totalAvailableBalance"])
        return 0
    except Exception as e:
        print(f"Error getting wallet balance: {e}")
        return 0

def calculate_position_size(entry_price, stop_loss, risk_percentage=1):
    """
    Calculate position size based on:
    - Account risk percentage (default 1%)
    - Entry price and stop loss
    """
    wallet_balance = get_wallet_balance()
    risk_amount = wallet_balance * (risk_percentage / 100)
    
    # Calculate position size based on risk
    stop_loss_pct = abs((float(stop_loss) - float(entry_price)) / float(entry_price))
    position_size = risk_amount / stop_loss_pct
    
    return position_size

def wait_for_position(symbol, max_attempts=10):
    """Wait for position to be confirmed and return position details"""
    for attempt in range(max_attempts):
        try:
            response = session.get_positions(
                category="linear",
                symbol=symbol
            )
            if response["retCode"] == 0:
                positions = response["result"]["list"]
                for pos in positions:
                    if pos["symbol"] == symbol and float(pos["size"]) != 0:
                        return pos
            time.sleep(1)  # Wait 1 second between checks
        except Exception as e:
            print(f"Error checking position: {e}")
            time.sleep(1)
    return None

def validate_and_adjust_stops(position_info, stop_loss, take_profit):
    """Validate and adjust stop loss and take profit based on position side"""
    entry_price = float(position_info["avgPrice"])
    is_short = position_info["side"] == "Sell"
    
    if is_short:
        # For short positions, stop loss must be above entry
        if float(stop_loss) <= entry_price:
            stop_loss = entry_price * 1.02  # Set 2% above entry
        # Take profit must be below entry
        if float(take_profit) >= entry_price:
            take_profit = entry_price * 0.98  # Set 2% below entry
    else:
        # For long positions, stop loss must be below entry
        if float(stop_loss) >= entry_price:
            stop_loss = entry_price * 0.98  # Set 2% below entry
        # Take profit must be above entry
        if float(take_profit) <= entry_price:
            take_profit = entry_price * 1.02  # Set 2% above entry
    
    return stop_loss, take_profit

def format_price(price):
    """Format price to match Bybit's requirements"""
    return "{:.1f}".format(float(price))

def set_position_stops(symbol, position_info, stop_loss, take_profit):
    """Set stop loss and take profit for an open position"""
    try:
        # Validate and adjust stops based on position side
        stop_loss, take_profit = validate_and_adjust_stops(position_info, stop_loss, take_profit)
        
        # Format prices
        stop_loss = format_price(stop_loss)
        take_profit = format_price(take_profit)
        
        print(f"\nSetting stops - Stop Loss: {stop_loss}, Take Profit: {take_profit}")
        print(f"Position Entry Price: {position_info['avgPrice']}")
        
        sl_params = {
            "category": "linear",
            "symbol": symbol,
            "stopLoss": stop_loss,
            "takeProfit": take_profit,
            "positionIdx": 0
        }
        result = session.set_trading_stop(**sl_params)
        print(f"\nStop-loss result: {result}")
        
        if result["retCode"] == 0:
            return True, "Stop loss and take profit set successfully"
        return False, f"Failed to set stops: {result['retMsg']}"
    except Exception as e:
        return False, f"Error setting stops: {str(e)}"

def get_open_positions(symbol=None):
    """Get all open positions or for a specific symbol"""
    try:
        response = session.get_positions(
            category="linear",
            symbol=symbol
        )
        if response["retCode"] == 0:
            positions = response["result"]["list"]
            return [pos for pos in positions if float(pos["size"]) != 0]
        return []
    except Exception as e:
        print(f"Error getting positions: {e}")
        return []

def execute_trade(trade):
    try:
        # Send initial signal notification with positions button
        send_telegram_log(
            format_signal_message(trade),
            keyboard=get_positions_keyboard()
        )
        
        # Test connection
        success, message = test_connection()
        if not success:
            notify_error(f"Connection test failed: {message}")
            return f"Connection test failed: {message}"

        side = "Sell" if trade["direction"] == "short" else "Buy"
        symbol = f"{trade['pair']}"
        entry_price = sum(trade["entry_range"]) / 2
        
        # Set position size
        if symbol == "BTCUSDT":
            position_size = 0.001  # Minimum size for BTC
        else:
            min_position_value = 5.1
            position_size = min_position_value / entry_price
            position_size = round(position_size, 3)
        
        # Place the market order
        order_params = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": str(position_size),
            "timeInForce": "GoodTillCancel"
        }
        
        result = session.place_order(**order_params)
        
        if result["retCode"] != 0:
            status = f"Order failed: {result['retMsg']}"
            notify_error(status)
            log_trade(trade, status)
            return status
        
        order_id = result["result"]["orderId"]
        
        # Wait for position to be confirmed
        position = wait_for_position(symbol)
        
        if position:
            # Send order confirmation
            send_telegram_log(
                format_order_message(trade, order_id, position),
                keyboard=get_positions_keyboard()
            )
            
            # Set stop loss and take profit
            success, message = set_position_stops(
                symbol=symbol,
                position_info=position,
                stop_loss=trade["stop_loss"],
                take_profit=trade["targets"][0]  # Using first target as take profit
            )
            
            if success:
                # Send stops confirmation
                send_telegram_log(
                    format_stops_message(
                        trade,
                        stop_loss=trade["stop_loss"],
                        take_profit=trade["targets"][0]
                    ),
                    keyboard=get_positions_keyboard()
                )
                status = f"Order placed and stops set successfully"
            else:
                notify_error(f"Failed to set stops: {message}")
                status = f"Order placed but failed to set stops: {message}"
            
            log_trade(trade, status)
            return status
        else:
            status = f"Order placed but position not confirmed"
            notify_error(status)
            log_trade(trade, status)
            return status
            
    except Exception as e:
        status = f"Trade failed: {str(e)}"
        notify_error(status)
        log_trade(trade, status)
        return status
