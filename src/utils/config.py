import os
from dotenv import load_dotenv
from typing import List, Dict, Tuple
import json


class Config:
    def __init__(self, config_path: str = 'config.env'):
        load_dotenv(config_path, override=True)

        # Account label (shown in alerts to identify which account)
        self.ACCOUNT_LABEL = os.getenv('ACCOUNT_LABEL', '')

        # MT5 Configuration
        self.MT5_LOGIN = int(os.getenv('MT5_LOGIN', '0'))
        self.MT5_PASSWORD = os.getenv('MT5_PASSWORD', '')
        self.MT5_SERVER = os.getenv('MT5_SERVER', '')
        self.MT5_PATH = os.getenv('MT5_PATH', None)

        # Telegram Configuration
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

        # Alert Settings
        self.PRICE_CHECK_INTERVAL = int(os.getenv('PRICE_CHECK_INTERVAL', '5'))
        self.ENABLE_TRADE_ALERTS = os.getenv('ENABLE_TRADE_ALERTS', 'true').lower() == 'true'
        self.ENABLE_ORDER_ALERTS = os.getenv('ENABLE_ORDER_ALERTS', 'true').lower() == 'true'
        self.ENABLE_PRICE_ALERTS = os.getenv('ENABLE_PRICE_ALERTS', 'true').lower() == 'true'

        # Synthetic Indices to Monitor (comma-separated)
        self.MONITORED_SYMBOLS = [s.strip() for s in os.getenv(
            'MONITORED_SYMBOLS',
            'Volatility 25 Index,Volatility 50 Index,Volatility 75 Index,Volatility 100 Index,'
            'Step Index,Boom 1000 Index,Crash 1000 Index,Jump 50 Index,Jump 75 Index,Jump 100 Index'
        ).split(',') if s.strip()]

        # Pending Order Monitoring
        self.ENABLE_PENDING_ORDER_ALERTS = os.getenv('ENABLE_PENDING_ORDER_ALERTS', 'true').lower() == 'true'
        self.PENDING_ORDER_PROXIMITY_PCT = float(os.getenv('PENDING_ORDER_PROXIMITY_PCT', '1.0'))

        # Profit-taking Settings
        self.ENABLE_PROFIT_SUGGESTIONS = os.getenv('ENABLE_PROFIT_SUGGESTIONS', 'true').lower() == 'true'
        self.MIN_PROFIT_FOR_SUGGESTION = float(os.getenv('MIN_PROFIT_FOR_SUGGESTION', '10.0'))
        self.PROFIT_PERCENTAGE_THRESHOLD = float(os.getenv('PROFIT_PERCENTAGE_THRESHOLD', '5.0'))

        # Auto Break-Even Settings
        self.ENABLE_AUTO_BREAKEVEN = os.getenv('ENABLE_AUTO_BREAKEVEN', 'false').lower() == 'true'
        self.AUTO_BREAKEVEN_PIPS = float(os.getenv('AUTO_BREAKEVEN_PIPS', '20.0'))

        # Risk Management Alerts
        self.ENABLE_RISK_ALERTS = os.getenv('ENABLE_RISK_ALERTS', 'true').lower() == 'true'
        self.MARGIN_LEVEL_WARNING = float(os.getenv('MARGIN_LEVEL_WARNING', '150.0'))
        self.MARGIN_LEVEL_CRITICAL = float(os.getenv('MARGIN_LEVEL_CRITICAL', '100.0'))
        self.MARGIN_ALERT_MIN_BALANCE = float(os.getenv('MARGIN_ALERT_MIN_BALANCE', '25.0'))
        self.MAX_POSITION_SIZE_PCT = float(os.getenv('MAX_POSITION_SIZE_PCT', '20.0'))
        self.DAILY_LOSS_LIMIT_PCT = float(os.getenv('DAILY_LOSS_LIMIT_PCT', '5.0'))
        self.DAILY_LOSS_LIMIT_AMOUNT = float(os.getenv('DAILY_LOSS_LIMIT_AMOUNT', '0.0'))
        self.DRAWDOWN_LIMIT_PCT = float(os.getenv('DRAWDOWN_LIMIT_PCT', '10.0'))

        # Daily Summary Settings
        self.ENABLE_DAILY_SUMMARY = os.getenv('ENABLE_DAILY_SUMMARY', 'true').lower() == 'true'
        self.DAILY_SUMMARY_HOUR = int(os.getenv('DAILY_SUMMARY_HOUR', '23'))
        self.DAILY_SUMMARY_MINUTE = int(os.getenv('DAILY_SUMMARY_MINUTE', '0'))

        # Advanced Price Level Features
        self.ENABLE_PRICE_LEVEL_GROUPS = os.getenv('ENABLE_PRICE_LEVEL_GROUPS', 'true').lower() == 'true'
        self.ENABLE_DYNAMIC_LEVELS = os.getenv('ENABLE_DYNAMIC_LEVELS', 'false').lower() == 'true'
        self.DYNAMIC_LEVELS_TIMEFRAME = int(os.getenv('DYNAMIC_LEVELS_TIMEFRAME', '16385'))
        self.DYNAMIC_LEVELS_PERIODS = int(os.getenv('DYNAMIC_LEVELS_PERIODS', '100'))
        self.DYNAMIC_LEVELS_MIN_TOUCHES = int(os.getenv('DYNAMIC_LEVELS_MIN_TOUCHES', '2'))
        self.DYNAMIC_LEVELS_TOLERANCE_PCT = float(os.getenv('DYNAMIC_LEVELS_TOLERANCE_PCT', '0.5'))
        self.DYNAMIC_LEVELS_AUTO_UPDATE_HOURS = int(os.getenv('DYNAMIC_LEVELS_AUTO_UPDATE_HOURS', '24'))

        # Enhanced Monitoring
        self.ENABLE_CONNECTION_HEALTH_MONITORING = os.getenv('ENABLE_CONNECTION_HEALTH_MONITORING', 'true').lower() == 'true'
        self.CONNECTION_CHECK_INTERVAL = int(os.getenv('CONNECTION_CHECK_INTERVAL', '30'))

        # Alert Rate Limiting
        self.ENABLE_ALERT_RATE_LIMITING = os.getenv('ENABLE_ALERT_RATE_LIMITING', 'true').lower() == 'true'
        self.MAX_ALERTS_PER_MINUTE = int(os.getenv('MAX_ALERTS_PER_MINUTE', '10'))
        self.MAX_ALERTS_PER_HOUR = int(os.getenv('MAX_ALERTS_PER_HOUR', '100'))

        # Alert Grouping/Batching
        self.ENABLE_ALERT_GROUPING = os.getenv('ENABLE_ALERT_GROUPING', 'true').lower() == 'true'
        self.ALERT_BATCH_WINDOW_SECONDS = int(os.getenv('ALERT_BATCH_WINDOW_SECONDS', '30'))
        self.ALERT_BATCH_MAX_SIZE = int(os.getenv('ALERT_BATCH_MAX_SIZE', '10'))

        # Quiet Hours
        self.QUIET_HOURS_ENABLED = os.getenv('QUIET_HOURS_ENABLED', 'false').lower() == 'true'
        self.QUIET_HOURS_START_HOUR = int(os.getenv('QUIET_HOURS_START_HOUR', '22'))
        self.QUIET_HOURS_START_MINUTE = int(os.getenv('QUIET_HOURS_START_MINUTE', '0'))
        self.QUIET_HOURS_END_HOUR = int(os.getenv('QUIET_HOURS_END_HOUR', '8'))
        self.QUIET_HOURS_END_MINUTE = int(os.getenv('QUIET_HOURS_END_MINUTE', '0'))

        # Trade History & Analytics
        self.ENABLE_TRADE_HISTORY = os.getenv('ENABLE_TRADE_HISTORY', 'true').lower() == 'true'
        self.TRADE_HISTORY_DB_PATH = os.getenv('TRADE_HISTORY_DB_PATH', 'data/trade_history.db')
        self.ENABLE_CHARTS = os.getenv('ENABLE_CHARTS', 'true').lower() == 'true'

        # ML-based Profit Suggestions
        self.ENABLE_ML_PROFIT_SUGGESTIONS = os.getenv('ENABLE_ML_PROFIT_SUGGESTIONS', 'true').lower() == 'true'
        self.ML_MIN_TRADES_FOR_LEARNING = int(os.getenv('ML_MIN_TRADES_FOR_LEARNING', '10'))

        # Volatility-based Position Sizing
        self.ENABLE_VOLATILITY_POSITION_SIZING = os.getenv('ENABLE_VOLATILITY_POSITION_SIZING', 'true').lower() == 'true'
        self.VOLATILITY_PERIODS = int(os.getenv('VOLATILITY_PERIODS', '20'))

        # Advanced Notifications
        self.ENABLE_PRICE_CHARTS_IN_ALERTS = os.getenv('ENABLE_PRICE_CHARTS_IN_ALERTS', 'true').lower() == 'true'
        self.PRICE_CHART_PERIODS = int(os.getenv('PRICE_CHART_PERIODS', '50'))

        # Discord Notifications
        self.ENABLE_DISCORD_NOTIFICATIONS = os.getenv('ENABLE_DISCORD_NOTIFICATIONS', 'false').lower() == 'true'
        self.DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

        # Email Notifications
        self.ENABLE_EMAIL_NOTIFICATIONS = os.getenv('ENABLE_EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
        self.EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        self.EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        self.EMAIL_SENDER = os.getenv('EMAIL_SENDER', '')
        self.EMAIL_SENDER_PASSWORD = os.getenv('EMAIL_SENDER_PASSWORD', '')
        self.EMAIL_RECIPIENTS = [e.strip() for e in os.getenv('EMAIL_RECIPIENTS', '').split(',') if e.strip()]
        self.EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'

        # Webhook Notifications
        self.ENABLE_WEBHOOK_NOTIFICATIONS = os.getenv('ENABLE_WEBHOOK_NOTIFICATIONS', 'false').lower() == 'true'
        self.WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
        self.WEBHOOK_HEADERS = os.getenv('WEBHOOK_HEADERS', '')

    def load_price_levels(self) -> Dict[str, List[Dict]]:
        """Load price level configurations from JSON file"""
        paths = ['data/price_levels.json', 'price_levels.json']
        for path in paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"Error loading {path}: {e}")
        return {}

    def save_price_levels(self, levels: Dict[str, List[Dict]]):
        """Save price level configurations to JSON file"""
        os.makedirs('data', exist_ok=True)
        try:
            with open('data/price_levels.json', 'w') as f:
                json.dump(levels, f, indent=2)
        except Exception as e:
            print(f"Error saving price_levels.json: {e}")

    def validate(self) -> Tuple[bool, str]:
        """Validate configuration"""
        if self.MT5_LOGIN == 0:
            return False, "MT5_LOGIN is not set"
        if not self.MT5_PASSWORD:
            return False, "MT5_PASSWORD is not set"
        if not self.MT5_SERVER:
            return False, "MT5_SERVER is not set"
        if not self.TELEGRAM_BOT_TOKEN:
            return False, "TELEGRAM_BOT_TOKEN is not set"
        if not self.TELEGRAM_CHAT_ID:
            return False, "TELEGRAM_CHAT_ID is not set"
        return True, "OK"
