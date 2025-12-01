import asyncio
import logging
import signal
import sys
from datetime import datetime
from mt5_monitor import MT5Monitor
from telegram_bot import TelegramNotifier
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mt5_alerts.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class MT5AlertService:
    def __init__(self):
        self.mt5_monitor = None
        self.telegram = None
        self.running = False
        self.price_levels = {}
        self.triggered_levels = set()
    
    async def initialize(self):
        """Initialize MT5 and Telegram connections"""
        # Validate configuration
        valid, error = Config.validate()
        if not valid:
            logger.error(f"Configuration error: {error}")
            return False
        
        # Initialize MT5
        logger.info("Connecting to MT5...")
        self.mt5_monitor = MT5Monitor(
            login=Config.MT5_LOGIN,
            password=Config.MT5_PASSWORD,
            server=Config.MT5_SERVER,
            path=Config.MT5_PATH
        )
        
        if not self.mt5_monitor.connect():
            logger.error("Failed to connect to MT5")
            return False
        
        # Initialize Telegram
        logger.info("Initializing Telegram bot...")
        self.telegram = TelegramNotifier(
            bot_token=Config.TELEGRAM_BOT_TOKEN,
            chat_id=Config.TELEGRAM_CHAT_ID
        )
        
        # Send test message
        if await self.telegram.send_test_message():
            logger.info("Telegram bot connected successfully")
        else:
            logger.warning("Telegram bot connection test failed, but continuing...")
        
        # Load price levels
        self.price_levels = Config.load_price_levels()
        if self.price_levels:
            logger.info(f"Loaded price levels for {len(self.price_levels)} symbols")
        
        return True
    
    async def check_trades(self):
        """Check for new trades and send alerts"""
        if not Config.ENABLE_TRADE_ALERTS:
            return
        
        new_trades = self.mt5_monitor.get_new_positions()
        for trade in new_trades:
            logger.info(f"New trade detected: {trade.get('symbol')} - {trade.get('type')}")
            await self.telegram.send_trade_alert(trade)
    
    async def check_orders(self):
        """Check for new orders and send alerts"""
        if not Config.ENABLE_ORDER_ALERTS:
            return
        
        new_orders = self.mt5_monitor.get_new_orders()
        for order in new_orders:
            logger.info(f"New order detected: {order.get('symbol')} - {order.get('type')}")
            await self.telegram.send_order_alert(order)
    
    async def check_price_levels(self):
        """Check if price levels have been reached"""
        if not Config.ENABLE_PRICE_ALERTS:
            return
        
        for symbol, levels in self.price_levels.items():
            triggered = self.mt5_monitor.check_price_levels(symbol, levels)
            for alert in triggered:
                level_key = f"{symbol}_{alert['level_id']}"
                if level_key not in self.triggered_levels:
                    logger.info(f"Price level reached: {symbol} - {alert['level_id']} at {alert['current_price']}")
                    await self.telegram.send_price_alert(alert)
                    self.triggered_levels.add(level_key)
    
    async def run(self):
        """Main event loop"""
        if not await self.initialize():
            logger.error("Initialization failed. Exiting.")
            return
        
        self.running = True
        logger.info("MT5 Alert Service started. Monitoring trades, orders, and price levels...")
        
        try:
            while self.running:
                # Check trades
                await self.check_trades()
                
                # Check orders
                await self.check_orders()
                
                # Check price levels
                await self.check_price_levels()
                
                # Wait before next check
                await asyncio.sleep(Config.PRICE_CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down...")
        self.running = False
        
        if self.mt5_monitor:
            self.mt5_monitor.disconnect()
        
        logger.info("Shutdown complete")


def signal_handler(service):
    """Handle shutdown signals"""
    def handler(signum, frame):
        logger.info(f"Received signal {signum}")
        service.running = False
    return handler


async def main():
    service = MT5AlertService()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler(service))
    signal.signal(signal.SIGTERM, signal_handler(service))
    
    await service.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

