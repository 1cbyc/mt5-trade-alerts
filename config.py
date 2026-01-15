import os
from dotenv import load_dotenv
from typing import List, Dict, Tuple
import json

load_dotenv('config.env')


class Config:
    # MT5 Configuration
    MT5_LOGIN = int(os.getenv('MT5_LOGIN', '0'))
    MT5_PASSWORD = os.getenv('MT5_PASSWORD', '')
    MT5_SERVER = os.getenv('MT5_SERVER', '')
    MT5_PATH = os.getenv('MT5_PATH', None)
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Alert Settings
    PRICE_CHECK_INTERVAL = int(os.getenv('PRICE_CHECK_INTERVAL', '5'))
    ENABLE_TRADE_ALERTS = os.getenv('ENABLE_TRADE_ALERTS', 'true').lower() == 'true'
    ENABLE_ORDER_ALERTS = os.getenv('ENABLE_ORDER_ALERTS', 'true').lower() == 'true'
    ENABLE_PRICE_ALERTS = os.getenv('ENABLE_PRICE_ALERTS', 'true').lower() == 'true'
    
    # Synthetic Indices to Monitor (comma-separated)
    # Common synthetic indices: Volatility 25 Index, Volatility 50 Index, Volatility 75 Index, Volatility 100 Index
    # Step Index, Boom 1000 Index, Crash 1000 Index, Jump 50 Index, Jump 75 Index, Jump 100 Index
    MONITORED_SYMBOLS = [s.strip() for s in os.getenv('MONITORED_SYMBOLS', 'Volatility 25 Index,Volatility 50 Index,Volatility 75 Index,Volatility 100 Index,Step Index,Boom 1000 Index,Crash 1000 Index,Jump 50 Index,Jump 75 Index,Jump 100 Index').split(',') if s.strip()]
    
    # Pending Order Monitoring
    ENABLE_PENDING_ORDER_ALERTS = os.getenv('ENABLE_PENDING_ORDER_ALERTS', 'true').lower() == 'true'
    PENDING_ORDER_PROXIMITY_PCT = float(os.getenv('PENDING_ORDER_PROXIMITY_PCT', '1.0'))  # Alert when price is within X% of pending order
    
    # Profit-taking Settings
    ENABLE_PROFIT_SUGGESTIONS = os.getenv('ENABLE_PROFIT_SUGGESTIONS', 'true').lower() == 'true'
    MIN_PROFIT_FOR_SUGGESTION = float(os.getenv('MIN_PROFIT_FOR_SUGGESTION', '10.0'))  # Minimum profit to suggest closing
    PROFIT_PERCENTAGE_THRESHOLD = float(os.getenv('PROFIT_PERCENTAGE_THRESHOLD', '5.0'))  # Suggest if profit is X% of account
    
    # Risk Management Alerts
    ENABLE_RISK_ALERTS = os.getenv('ENABLE_RISK_ALERTS', 'true').lower() == 'true'
    MARGIN_LEVEL_WARNING = float(os.getenv('MARGIN_LEVEL_WARNING', '150.0'))  # Alert when margin level drops below X%
    MARGIN_LEVEL_CRITICAL = float(os.getenv('MARGIN_LEVEL_CRITICAL', '100.0'))  # Critical alert when margin level drops below X%
    MAX_POSITION_SIZE_PCT = float(os.getenv('MAX_POSITION_SIZE_PCT', '20.0'))  # Alert when position size exceeds X% of account
    DAILY_LOSS_LIMIT_PCT = float(os.getenv('DAILY_LOSS_LIMIT_PCT', '5.0'))  # Alert when daily loss exceeds X% of balance
    DAILY_LOSS_LIMIT_AMOUNT = float(os.getenv('DAILY_LOSS_LIMIT_AMOUNT', '0.0'))  # Alert when daily loss exceeds X amount (0 = disabled)
    DRAWDOWN_LIMIT_PCT = float(os.getenv('DRAWDOWN_LIMIT_PCT', '10.0'))  # Alert when drawdown exceeds X% from starting balance
    
    # Daily Summary Settings
    ENABLE_DAILY_SUMMARY = os.getenv('ENABLE_DAILY_SUMMARY', 'true').lower() == 'true'
    DAILY_SUMMARY_HOUR = int(os.getenv('DAILY_SUMMARY_HOUR', '23'))  # Hour to send daily summary (24-hour format, default 23:00)
    DAILY_SUMMARY_MINUTE = int(os.getenv('DAILY_SUMMARY_MINUTE', '0'))  # Minute to send daily summary (default 0)
    
    @staticmethod
    def load_price_levels() -> Dict[str, List[Dict]]:
        """Load price level configurations from JSON file"""
        if os.path.exists('price_levels.json'):
            try:
                with open('price_levels.json', 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading price_levels.json: {e}")
                return {}
        return {}
    
    @staticmethod
    def save_price_levels(levels: Dict[str, List[Dict]]):
        """Save price level configurations to JSON file"""
        try:
            with open('price_levels.json', 'w') as f:
                json.dump(levels, f, indent=2)
        except Exception as e:
            print(f"Error saving price_levels.json: {e}")
    
    @staticmethod
    def validate() -> Tuple[bool, str]:
        """Validate configuration"""
        if Config.MT5_LOGIN == 0:
            return False, "MT5_LOGIN is not set"
        if not Config.MT5_PASSWORD:
            return False, "MT5_PASSWORD is not set"
        if not Config.MT5_SERVER:
            return False, "MT5_SERVER is not set"
        if not Config.TELEGRAM_BOT_TOKEN:
            return False, "TELEGRAM_BOT_TOKEN is not set"
        if not Config.TELEGRAM_CHAT_ID:
            return False, "TELEGRAM_CHAT_ID is not set"
        return True, "OK"

