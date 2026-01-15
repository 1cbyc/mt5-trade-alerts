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
        self.monitored_symbols = set()
        self.sent_profit_suggestions = set()  # Track sent suggestions to avoid spam
        self.sent_risk_alerts = set()  # Track sent risk alerts to avoid spam
        self.initial_balance = None  # Track initial balance for drawdown calculation
        self.last_daily_summary_date = None  # Track last date daily summary was sent
        self.last_dynamic_levels_update = None  # Track last dynamic levels update time
    
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
        
        # Set MT5 monitor reference for command handlers
        self.telegram.set_mt5_monitor(self.mt5_monitor)
        
        # Setup command handlers
        await self.telegram.setup_commands()
        
        # Send test message
        if await self.telegram.send_test_message():
            logger.info("Telegram bot connected successfully")
        else:
            logger.warning("Telegram bot connection test failed, but continuing...")
        
        # Load price levels
        self.price_levels = Config.load_price_levels()
        if self.price_levels:
            logger.info(f"Loaded price levels for {len(self.price_levels)} symbols")
            # Initialize triggered_levels with levels that are already crossed
            # This prevents alerts on startup for levels that were already crossed
            await self._initialize_triggered_levels()
        
        # Initialize monitored symbols from config
        self.monitored_symbols = set(Config.MONITORED_SYMBOLS)
        logger.info(f"Monitoring synthetic indices: {', '.join(self.monitored_symbols)}")
        
        # Store initial balance for drawdown calculation
        account_info = self.mt5_monitor.get_account_info()
        if account_info:
            self.initial_balance = account_info.get('balance', 0)
            logger.info(f"Initial balance tracked: {self.initial_balance}")
        
        return True
    
    async def _initialize_triggered_levels(self):
        """Initialize triggered_levels set with levels that are already crossed on startup"""
        if not Config.ENABLE_PRICE_ALERTS:
            return
        
        logger.info("Initializing price level state (marking already-crossed levels as triggered)...")
        
        for symbol, levels in self.price_levels.items():
            triggered = self.mt5_monitor.check_price_levels(symbol, levels)
            for alert in triggered:
                level_key = f"{symbol}_{alert['level_id']}"
                is_recurring = alert.get('recurring', False)
                
                # Only mark one-time alerts as triggered (recurring alerts should still fire)
                if not is_recurring:
                    self.triggered_levels.add(level_key)
                    logger.debug(f"Marked {level_key} as already triggered (price already crossed)")
        
        if self.triggered_levels:
            logger.info(f"Marked {len(self.triggered_levels)} price level(s) as already triggered on startup")
    
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
        
        # Check configured price levels
        for symbol, levels in self.price_levels.items():
            triggered = self.mt5_monitor.check_price_levels(symbol, levels)
            for alert in triggered:
                level_key = f"{symbol}_{alert['level_id']}"
                is_recurring = alert.get('recurring', False)
                
                # For one-time alerts, check if already triggered
                if not is_recurring and level_key in self.triggered_levels:
                    continue
                
                logger.info(f"Price level reached: {symbol} - {alert['level_id']} at {alert['current_price']}")
                await self.telegram.send_price_alert(alert)
                
                # Only add to triggered set if it's a one-time alert
                if not is_recurring:
                    self.triggered_levels.add(level_key)
            
            # Check for level groups
            if Config.ENABLE_PRICE_LEVEL_GROUPS:
                triggered_ids = [alert['level_id'] for alert in triggered]
                if triggered_ids:
                    group_alerts = self.mt5_monitor.check_level_groups(symbol, levels, triggered_ids)
                    for group_alert in group_alerts:
                        group_key = f"{symbol}_group_{group_alert['group_id']}"
                        if group_key not in self.triggered_levels:
                            logger.info(f"Price level group triggered: {symbol} - {group_alert['group_id']}")
                            await self.telegram.send_level_group_alert(group_alert)
                            self.triggered_levels.add(group_key)
    
    async def update_monitored_symbols(self):
        """Update list of symbols to monitor based on active positions/orders"""
        active_instruments = self.mt5_monitor.get_active_instruments()
        
        # Add synthetic indices from config
        for symbol in Config.MONITORED_SYMBOLS:
            active_instruments.add(symbol)
        
        # Update monitored symbols
        new_symbols = active_instruments - self.monitored_symbols
        if new_symbols:
            logger.info(f"New instruments detected: {', '.join(new_symbols)}")
            self.monitored_symbols.update(new_symbols)
        
        # Log pending orders summary
        pending_by_symbol = self.mt5_monitor.get_pending_orders_by_symbol()
        if pending_by_symbol:
            total_pending = sum(len(orders) for orders in pending_by_symbol.values())
            logger.info(f"Tracking {total_pending} pending orders across {len(pending_by_symbol)} instruments")
    
    async def check_pending_order_proximity(self):
        """Check if prices are approaching pending order levels"""
        if not Config.ENABLE_PENDING_ORDER_ALERTS:
            return
        
        pending_by_symbol = self.mt5_monitor.get_pending_orders_by_symbol()
        
        for symbol in pending_by_symbol.keys():
            alerts = self.mt5_monitor.check_pending_order_proximity(
                symbol, 
                threshold_pct=Config.PENDING_ORDER_PROXIMITY_PCT
            )
            
            for alert in alerts:
                alert_key = f"pending_{alert['ticket']}"
                if alert_key not in self.triggered_levels:
                    logger.info(f"Price approaching pending order: {symbol} - {alert['order_type']} at {alert['order_price']} (current: {alert['current_price']}, {alert['distance_pct']}% away)")
                    await self.telegram.send_pending_order_alert(alert)
                    self.triggered_levels.add(alert_key)
    
    async def check_profit_suggestions(self):
        """Check for profitable positions and suggest partial closes"""
        if not Config.ENABLE_PROFIT_SUGGESTIONS:
            return
        
        suggestions = self.mt5_monitor.analyze_profitable_positions(
            min_profit=Config.MIN_PROFIT_FOR_SUGGESTION,
            profit_percentage=Config.PROFIT_PERCENTAGE_THRESHOLD
        )
        
        for suggestion in suggestions:
            suggestion_key = f"profit_{suggestion['ticket']}"
            if suggestion_key not in self.sent_profit_suggestions:
                logger.info(f"Profit suggestion for {suggestion['symbol']} - Ticket {suggestion['ticket']}: {suggestion['profit']:.2f}")
                await self.telegram.send_profit_suggestion(suggestion)
                self.sent_profit_suggestions.add(suggestion_key)
    
    async def check_risk_alerts(self):
        """Check for risk management alerts"""
        if not Config.ENABLE_RISK_ALERTS:
            return
        
        # Check margin level
        margin_alert = self.mt5_monitor.check_margin_level(
            warning_threshold=Config.MARGIN_LEVEL_WARNING,
            critical_threshold=Config.MARGIN_LEVEL_CRITICAL
        )
        if margin_alert:
            alert_key = f"margin_{margin_alert['type']}_{margin_alert['margin_level']:.1f}"
            if alert_key not in self.sent_risk_alerts:
                logger.warning(f"Margin {margin_alert['type']} alert: {margin_alert['margin_level']:.2f}%")
                await self.telegram.send_margin_alert(margin_alert)
                self.sent_risk_alerts.add(alert_key)
        
        # Check position sizes
        position_alerts = self.mt5_monitor.check_position_sizes(
            max_size_pct=Config.MAX_POSITION_SIZE_PCT
        )
        for alert in position_alerts:
            alert_key = f"position_size_{alert['ticket']}"
            if alert_key not in self.sent_risk_alerts:
                logger.warning(f"Position size warning: {alert['symbol']} - {alert['position_size_pct']:.2f}%")
                await self.telegram.send_position_size_alert(alert)
                self.sent_risk_alerts.add(alert_key)
        
        # Check daily loss limit
        if Config.DAILY_LOSS_LIMIT_PCT > 0 or Config.DAILY_LOSS_LIMIT_AMOUNT > 0:
            loss_alert = self.mt5_monitor.check_daily_loss_limit(
                loss_limit_pct=Config.DAILY_LOSS_LIMIT_PCT,
                loss_limit_amount=Config.DAILY_LOSS_LIMIT_AMOUNT
            )
            if loss_alert:
                alert_key = f"daily_loss_{loss_alert['type']}"
                if alert_key not in self.sent_risk_alerts:
                    logger.warning(f"Daily loss limit alert: {loss_alert.get('loss_pct', loss_alert.get('daily_loss', 0))}")
                    await self.telegram.send_daily_loss_alert(loss_alert)
                    self.sent_risk_alerts.add(alert_key)
        
        # Check drawdown
        if Config.DRAWDOWN_LIMIT_PCT > 0 and self.initial_balance:
            drawdown_alert = self.mt5_monitor.check_drawdown(
                drawdown_limit_pct=Config.DRAWDOWN_LIMIT_PCT,
                initial_balance=self.initial_balance
            )
            if drawdown_alert:
                alert_key = f"drawdown_{drawdown_alert['drawdown_pct']:.1f}"
                if alert_key not in self.sent_risk_alerts:
                    logger.warning(f"Drawdown alert: {drawdown_alert['drawdown_pct']:.2f}%")
                    await self.telegram.send_drawdown_alert(drawdown_alert)
                    self.sent_risk_alerts.add(alert_key)
    
    async def check_daily_summary(self):
        """Check if it's time to send daily performance summary"""
        if not Config.ENABLE_DAILY_SUMMARY:
            return
        
        now = datetime.now()
        current_date = now.date()
        
        # Check if we should send daily summary
        should_send = False
        
        # If we haven't sent today's summary yet
        if self.last_daily_summary_date != current_date:
            # Check if current time is at or past the configured summary time
            summary_time = now.replace(hour=Config.DAILY_SUMMARY_HOUR, minute=Config.DAILY_SUMMARY_MINUTE, second=0, microsecond=0)
            
            # If we're past the summary time for today, send it
            if now >= summary_time:
                should_send = True
        
        if should_send:
            logger.info("Sending daily performance summary...")
            stats = self.mt5_monitor.get_trade_statistics(period='daily')
            if stats and stats.get('total_trades', 0) > 0:
                await self.telegram.send_daily_summary(stats)
                self.last_daily_summary_date = current_date
                logger.info("Daily performance summary sent successfully")
            else:
                logger.info("No trades today, skipping daily summary")
                self.last_daily_summary_date = current_date
    
    async def update_dynamic_levels(self):
        """Auto-detect and update dynamic support/resistance levels"""
        if not Config.ENABLE_DYNAMIC_LEVELS:
            return
        
        from datetime import timedelta
        
        now = datetime.now()
        
        # Check if it's time to update (based on configured interval)
        if self.last_dynamic_levels_update:
            hours_since_update = (now - self.last_dynamic_levels_update).total_seconds() / 3600
            if hours_since_update < Config.DYNAMIC_LEVELS_AUTO_UPDATE_HOURS:
                return
        else:
            # First run, update immediately
            pass
        
        logger.info("Updating dynamic support/resistance levels...")
        
        # Get symbols to analyze (from monitored symbols or active instruments)
        symbols_to_analyze = set(Config.MONITORED_SYMBOLS)
        active_instruments = self.mt5_monitor.get_active_instruments()
        symbols_to_analyze.update(active_instruments)
        
        updated_count = 0
        for symbol in symbols_to_analyze:
            try:
                levels = self.mt5_monitor.detect_support_resistance(
                    symbol=symbol,
                    timeframe=Config.DYNAMIC_LEVELS_TIMEFRAME,
                    periods=Config.DYNAMIC_LEVELS_PERIODS,
                    min_touches=Config.DYNAMIC_LEVELS_MIN_TOUCHES,
                    tolerance_pct=Config.DYNAMIC_LEVELS_TOLERANCE_PCT
                )
                
                # Add detected levels to price_levels.json
                if symbol not in self.price_levels:
                    self.price_levels[symbol] = []
                
                # Remove old dynamic levels (those with id starting with "dynamic_")
                self.price_levels[symbol] = [
                    level for level in self.price_levels[symbol] 
                    if not level.get('id', '').startswith('dynamic_')
                ]
                
                # Add new support levels
                for idx, support_price in enumerate(levels['support']):
                    self.price_levels[symbol].append({
                        'id': f'dynamic_support_{idx+1}',
                        'price': support_price,
                        'type': 'below',
                        'description': f'Auto-detected support level #{idx+1}',
                        'recurring': True,  # Dynamic levels are recurring
                        'dynamic': True  # Mark as dynamic
                    })
                
                # Add new resistance levels
                for idx, resistance_price in enumerate(levels['resistance']):
                    self.price_levels[symbol].append({
                        'id': f'dynamic_resistance_{idx+1}',
                        'price': resistance_price,
                        'type': 'above',
                        'description': f'Auto-detected resistance level #{idx+1}',
                        'recurring': True,  # Dynamic levels are recurring
                        'dynamic': True  # Mark as dynamic
                    })
                
                if levels['support'] or levels['resistance']:
                    updated_count += 1
                    logger.info(f"Detected {len(levels['support'])} support and {len(levels['resistance'])} resistance levels for {symbol}")
            
            except Exception as e:
                logger.error(f"Error detecting levels for {symbol}: {e}")
        
        if updated_count > 0:
            # Save updated levels
            Config.save_price_levels(self.price_levels)
            logger.info(f"Updated dynamic levels for {updated_count} symbols")
        
        self.last_dynamic_levels_update = now
    
    async def run(self):
        """Main event loop"""
        if not await self.initialize():
            logger.error("Initialization failed. Exiting.")
            return
        
        self.running = True
        logger.info("MT5 Alert Service started. Monitoring trades, orders, and price levels...")
        logger.info(f"Monitoring synthetic indices: {', '.join(Config.MONITORED_SYMBOLS)}")
        
        # Counter for periodic tasks
        check_counter = 0
        
        try:
            while self.running:
                # Check trades
                await self.check_trades()
                
                # Check orders
                await self.check_orders()
                
                # Update monitored symbols (every 5 cycles = ~25 seconds)
                if check_counter % 5 == 0:
                    await self.update_monitored_symbols()
                
                # Check price levels for all monitored symbols
                await self.check_price_levels()
                
                # Check pending order proximity (every 2 cycles = ~10 seconds)
                if check_counter % 2 == 0:
                    await self.check_pending_order_proximity()
                
                # Check profit suggestions (every 3 cycles = ~15 seconds)
                if check_counter % 3 == 0:
                    await self.check_profit_suggestions()
                
                # Check risk management alerts (every 10 cycles = ~50 seconds - less frequent due to heavy operations)
                if check_counter % 10 == 0:
                    await self.check_risk_alerts()
                
                # Check daily summary (every 12 cycles = ~60 seconds - check once per minute)
                if check_counter % 12 == 0:
                    await self.check_daily_summary()
                
                # Update dynamic levels (every 360 cycles = ~30 minutes)
                if Config.ENABLE_DYNAMIC_LEVELS and check_counter % 360 == 0:
                    await self.update_dynamic_levels()
                
                # Wait before next check
                await asyncio.sleep(Config.PRICE_CHECK_INTERVAL)
                check_counter += 1
        
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
        
        if self.telegram:
            await self.telegram.stop_commands()
        
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

