from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
        self.enabled = True
        self.application = None
        self.mt5_monitor = None  # Will be set by main service
    
    async def send_message(self, message: str) -> bool:
        """Send a message to Telegram"""
        if not self.enabled:
            return False
        
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message, parse_mode='HTML')
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    def format_trade_alert(self, trade: dict) -> str:
        """Format trade information for Telegram"""
        trade_type = trade.get('type', 'UNKNOWN')
        symbol = trade.get('symbol', 'N/A')
        volume = trade.get('volume', 0)
        price_open = trade.get('price_open', 0)
        price_current = trade.get('price_current', 0)
        profit = trade.get('profit', 0)
        ticket = trade.get('ticket', 'N/A')
        time = trade.get('time', 'N/A')
        
        if trade_type == 'CLOSED':
            emoji = "🔴"
            status = "CLOSED"
        elif trade_type == 'BUY':
            emoji = "🟢"
            status = "OPENED (BUY)"
        else:
            emoji = "🔵"
            status = "OPENED (SELL)"
        
        message = f"{emoji} <b>Trade {status}</b>\n\n"
        message += f"Ticket: {ticket}\n"
        message += f"Symbol: {symbol}\n"
        message += f"Type: {trade_type}\n"
        message += f"Volume: {volume}\n"
        message += f"Open Price: {price_open}\n"
        
        if price_current:
            message += f"Current Price: {price_current}\n"
        
        if profit is not None:
            profit_emoji = "💰" if profit >= 0 else "📉"
            message += f"Profit: {profit_emoji} {profit:.2f}\n"
        
        message += f"Time: {time}"
        
        return message
    
    def format_order_alert(self, order: dict) -> str:
        """Format order information for Telegram"""
        order_type = order.get('type', 'UNKNOWN')
        symbol = order.get('symbol', 'N/A')
        volume = order.get('volume', 0)
        price_open = order.get('price_open', 0)
        price_current = order.get('price_current', 0)
        ticket = order.get('ticket', 'N/A')
        time_setup = order.get('time_setup', 'N/A')
        time_expiration = order.get('time_expiration', 'N/A')
        
        if 'EXECUTED' in order_type or 'CANCELLED' in order_type:
            emoji = "✅"
        else:
            emoji = "📋"
        
        message = f"{emoji} <b>Order Alert</b>\n\n"
        message += f"Ticket: {ticket}\n"
        message += f"Symbol: {symbol}\n"
        message += f"Type: {order_type}\n"
        message += f"Volume: {volume}\n"
        message += f"Price: {price_open}\n"
        
        if price_current:
            message += f"Current Price: {price_current}\n"
        
        message += f"Setup Time: {time_setup}\n"
        if time_expiration != 'No expiration':
            message += f"Expiration: {time_expiration}\n"
        
        return message
    
    def format_price_alert(self, alert: dict) -> str:
        """Format price level alert for Telegram"""
        symbol = alert.get('symbol', 'N/A')
        level_price = alert.get('level_price', 0)
        current_price = alert.get('current_price', 0)
        level_type = alert.get('level_type', 'both')
        level_id = alert.get('level_id', 'unknown')
        time = alert.get('time', 'N/A')
        
        emoji = "🎯"
        
        message = f"{emoji} <b>Price Level Reached</b>\n\n"
        message += f"Symbol: {symbol}\n"
        message += f"Level ID: {level_id}\n"
        message += f"Target Price: {level_price}\n"
        message += f"Current Price: {current_price}\n"
        message += f"Direction: {level_type}\n"
        message += f"Time: {time}"
        
        return message
    
    async def send_trade_alert(self, trade: dict) -> bool:
        """Send trade alert to Telegram"""
        message = self.format_trade_alert(trade)
        return await self.send_message(message)
    
    async def send_order_alert(self, order: dict) -> bool:
        """Send order alert to Telegram"""
        message = self.format_order_alert(order)
        return await self.send_message(message)
    
    async def send_price_alert(self, alert: dict) -> bool:
        """Send price level alert to Telegram"""
        message = self.format_price_alert(alert)
        return await self.send_message(message)
    
    def format_profit_suggestion(self, suggestion: dict) -> str:
        """Format profit-taking suggestion for Telegram"""
        symbol = suggestion.get('symbol', 'N/A')
        ticket = suggestion.get('ticket', 'N/A')
        trade_type = suggestion.get('type', 'N/A')
        volume = suggestion.get('volume', 0)
        volume_to_close = suggestion.get('volume_to_close', 0)
        profit = suggestion.get('profit', 0)
        profit_pct = suggestion.get('profit_percentage', 0)
        price_open = suggestion.get('price_open', 0)
        price_current = suggestion.get('price_current', 0)
        
        emoji = "💡"
        
        message = f"{emoji} <b>Profit-Taking Suggestion</b>\n\n"
        message += f"Symbol: {symbol}\n"
        message += f"Ticket: {ticket}\n"
        message += f"Type: {trade_type}\n"
        message += f"Current Profit: 💰 {profit:.2f} ({profit_pct:.2f}%)\n"
        message += f"Open Price: {price_open}\n"
        message += f"Current Price: {price_current}\n"
        message += f"\n💡 <b>Suggestion:</b> Consider closing {volume_to_close} lots (50% of position) to secure profits\n"
        message += f"Remaining: {volume - volume_to_close} lots"
        
        return message
    
    async def send_profit_suggestion(self, suggestion: dict) -> bool:
        """Send profit-taking suggestion to Telegram"""
        message = self.format_profit_suggestion(suggestion)
        return await self.send_message(message)
    
    def format_pending_order_alert(self, alert: dict) -> str:
        """Format pending order proximity alert for Telegram"""
        symbol = alert.get('symbol', 'N/A')
        ticket = alert.get('ticket', 'N/A')
        order_type = alert.get('order_type', 'N/A')
        order_price = alert.get('order_price', 0)
        current_price = alert.get('current_price', 0)
        distance_pct = alert.get('distance_pct', 0)
        volume = alert.get('volume', 0)
        time = alert.get('time', 'N/A')
        
        emoji = "⚠️"
        
        message = f"{emoji} <b>Pending Order Alert</b>\n\n"
        message += f"Symbol: {symbol}\n"
        message += f"Order Ticket: {ticket}\n"
        message += f"Order Type: {order_type}\n"
        message += f"Order Price: {order_price}\n"
        message += f"Current Price: {current_price}\n"
        message += f"Distance: {distance_pct}%\n"
        message += f"Volume: {volume}\n"
        message += f"\n⚠️ Price is approaching your pending order!"
        message += f"\nTime: {time}"
        
        return message
    
    async def send_pending_order_alert(self, alert: dict) -> bool:
        """Send pending order proximity alert to Telegram"""
        message = self.format_pending_order_alert(alert)
        return await self.send_message(message)
    
    async def send_test_message(self) -> bool:
        """Send a test message to verify connection"""
        message = "🤖 <b>MT5 Trade Alerts Bot</b>\n\nBot is connected and ready!"
        return await self.send_message(message)
    
    def set_mt5_monitor(self, mt5_monitor):
        """Set the MT5Monitor instance for command handlers"""
        self.mt5_monitor = mt5_monitor
    
    def format_status(self, account_info: dict) -> str:
        """Format account status for /status command"""
        if not account_info:
            return "❌ <b>Status</b>\n\nUnable to retrieve account information."
        
        margin_level = account_info.get('margin_level', 0)
        margin_level_emoji = "🟢" if margin_level > 200 else "🟡" if margin_level > 100 else "🔴"
        
        message = f"📊 <b>Account Status</b>\n\n"
        message += f"Account: {account_info.get('login', 'N/A')}\n"
        message += f"Server: {account_info.get('server', 'N/A')}\n"
        message += f"Currency: {account_info.get('currency', 'N/A')}\n"
        message += f"Leverage: 1:{account_info.get('leverage', 'N/A')}\n\n"
        message += f"💰 Balance: {account_info.get('balance', 0):.2f}\n"
        message += f"💵 Equity: {account_info.get('equity', 0):.2f}\n"
        message += f"📈 Profit: {account_info.get('profit', 0):.2f}\n"
        message += f"💳 Margin: {account_info.get('margin', 0):.2f}\n"
        message += f"🆓 Free Margin: {account_info.get('free_margin', 0):.2f}\n"
        message += f"{margin_level_emoji} Margin Level: {margin_level:.2f}%\n\n"
        message += f"📊 Open Positions: {account_info.get('open_positions', 0)}"
        
        return message
    
    def format_positions(self, positions: list) -> str:
        """Format positions list for /positions command"""
        if not positions:
            return "📊 <b>Open Positions</b>\n\nNo open positions."
        
        message = f"📊 <b>Open Positions</b> ({len(positions)})\n\n"
        
        total_profit = 0.0
        for pos in positions:
            profit = pos.get('profit', 0)
            total_profit += profit
            profit_emoji = "💰" if profit >= 0 else "📉"
            
            message += f"<b>{pos.get('symbol', 'N/A')}</b> - {pos.get('type', 'N/A')}\n"
            message += f"Ticket: {pos.get('ticket', 'N/A')}\n"
            message += f"Volume: {pos.get('volume', 0)}\n"
            message += f"Open: {pos.get('price_open', 0)}\n"
            message += f"Current: {pos.get('price_current', 0)}\n"
            message += f"Profit: {profit_emoji} {profit:.2f}\n"
            if pos.get('sl'):
                message += f"SL: {pos.get('sl')}\n"
            if pos.get('tp'):
                message += f"TP: {pos.get('tp')}\n"
            message += f"Time: {pos.get('time', 'N/A')}\n\n"
        
        total_emoji = "💰" if total_profit >= 0 else "📉"
        message += f"<b>Total Profit: {total_emoji} {total_profit:.2f}</b>"
        
        return message
    
    def format_orders(self, orders: list) -> str:
        """Format orders list for /orders command"""
        if not orders:
            return "📋 <b>Pending Orders</b>\n\nNo pending orders."
        
        message = f"📋 <b>Pending Orders</b> ({len(orders)})\n\n"
        
        for order in orders:
            message += f"<b>{order.get('symbol', 'N/A')}</b> - {order.get('type', 'N/A')}\n"
            message += f"Ticket: {order.get('ticket', 'N/A')}\n"
            message += f"Volume: {order.get('volume', 0)}\n"
            message += f"Price: {order.get('price_open', 0)}\n"
            message += f"Current: {order.get('price_current', 0)}\n"
            if order.get('sl'):
                message += f"SL: {order.get('sl')}\n"
            if order.get('tp'):
                message += f"TP: {order.get('tp')}\n"
            message += f"Setup: {order.get('time_setup', 'N/A')}\n"
            if order.get('time_expiration'):
                message += f"Expires: {order.get('time_expiration')}\n"
            message += "\n"
        
        return message
    
    def format_summary(self, summary: dict) -> str:
        """Format P/L summary for /summary command"""
        if not summary:
            return "📈 <b>P/L Summary</b>\n\nUnable to retrieve summary."
        
        period = summary.get('period', 'daily').upper()
        total_profit = summary.get('total_profit', 0)
        open_profit = summary.get('open_profit', 0)
        total_trades = summary.get('total_trades', 0)
        winning_trades = summary.get('winning_trades', 0)
        losing_trades = summary.get('losing_trades', 0)
        win_rate = summary.get('win_rate', 0)
        largest_win = summary.get('largest_win', 0)
        largest_loss = summary.get('largest_loss', 0)
        best_trade = summary.get('best_trade')
        worst_trade = summary.get('worst_trade')
        
        profit_emoji = "💰" if total_profit >= 0 else "📉"
        open_emoji = "💰" if open_profit >= 0 else "📉"
        
        message = f"📈 <b>{period} P/L Summary</b>\n\n"
        message += f"Period: {summary.get('start_time', 'N/A')} - Now\n\n"
        message += f"<b>Closed Trades:</b>\n"
        message += f"Total Profit: {profit_emoji} {total_profit:.2f}\n"
        message += f"Total Trades: {total_trades}\n"
        message += f"Winning: {winning_trades} | Losing: {losing_trades}\n"
        message += f"Win Rate: {win_rate:.1f}%\n"
        message += f"Largest Win: 💰 {largest_win:.2f}\n"
        message += f"Largest Loss: 📉 {largest_loss:.2f}\n\n"
        
        if best_trade:
            message += f"<b>🏆 Best Trade:</b>\n"
            message += f"{best_trade.get('symbol', 'N/A')} {best_trade.get('type', 'N/A')}\n"
            message += f"Profit: 💰 {best_trade.get('profit', 0):.2f}\n"
            message += f"Entry: {best_trade.get('entry_price', 0)} → Exit: {best_trade.get('exit_price', 0)}\n"
            if best_trade.get('duration'):
                message += f"Duration: {best_trade.get('duration')}\n"
            message += "\n"
        
        if worst_trade:
            message += f"<b>📉 Worst Trade:</b>\n"
            message += f"{worst_trade.get('symbol', 'N/A')} {worst_trade.get('type', 'N/A')}\n"
            message += f"Loss: 📉 {worst_trade.get('profit', 0):.2f}\n"
            message += f"Entry: {worst_trade.get('entry_price', 0)} → Exit: {worst_trade.get('exit_price', 0)}\n"
            if worst_trade.get('duration'):
                message += f"Duration: {worst_trade.get('duration')}\n"
            message += "\n"
        
        message += f"<b>Open Positions:</b>\n"
        message += f"Unrealized P/L: {open_emoji} {open_profit:.2f}\n\n"
        message += f"<b>Total P/L: {profit_emoji} {total_profit + open_profit:.2f}</b>"
        
        return message
    
    def format_daily_summary(self, stats: dict) -> str:
        """Format comprehensive daily performance summary"""
        if not stats:
            return "📊 <b>Daily Performance Summary</b>\n\nUnable to retrieve statistics."
        
        total_profit = stats.get('total_profit', 0)
        open_profit = stats.get('open_profit', 0)
        total_trades = stats.get('total_trades', 0)
        winning_trades = stats.get('winning_trades', 0)
        losing_trades = stats.get('losing_trades', 0)
        break_even_trades = stats.get('break_even_trades', 0)
        win_rate = stats.get('win_rate', 0)
        average_win = stats.get('average_win', 0)
        average_loss = stats.get('average_loss', 0)
        profit_factor = stats.get('profit_factor', 0)
        best_trade = stats.get('best_trade')
        worst_trade = stats.get('worst_trade')
        total_commission = stats.get('total_commission', 0)
        total_swap = stats.get('total_swap', 0)
        total_volume = stats.get('total_volume', 0)
        
        profit_emoji = "💰" if total_profit >= 0 else "📉"
        open_emoji = "💰" if open_profit >= 0 else "📉"
        
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        
        message = f"📊 <b>Daily Performance Summary</b>\n"
        message += f"📅 {date_str}\n"
        message += "━" * 30 + "\n\n"
        
        # Overall Performance
        message += f"<b>💰 Overall Performance</b>\n"
        message += f"Closed P/L: {profit_emoji} {total_profit:.2f}\n"
        message += f"Open P/L: {open_emoji} {open_profit:.2f}\n"
        message += f"Total P/L: {profit_emoji} {total_profit + open_profit:.2f}\n\n"
        
        # Trade Statistics
        message += f"<b>📈 Trade Statistics</b>\n"
        message += f"Total Trades: {total_trades}\n"
        message += f"Winning: 🟢 {winning_trades} | Losing: 🔴 {losing_trades}"
        if break_even_trades > 0:
            message += f" | Break-even: ⚪ {break_even_trades}"
        message += "\n"
        message += f"Win Rate: {win_rate:.1f}%\n"
        message += f"Average Win: 💰 {average_win:.2f}\n"
        message += f"Average Loss: 📉 {average_loss:.2f}\n"
        message += f"Profit Factor: {profit_factor:.2f}\n\n"
        
        # Best/Worst Trades
        if best_trade:
            message += f"<b>🏆 Best Trade</b>\n"
            message += f"Ticket: {best_trade.get('ticket', 'N/A')}\n"
            message += f"Symbol: {best_trade.get('symbol', 'N/A')} ({best_trade.get('type', 'N/A')})\n"
            message += f"Profit: 💰 {best_trade.get('profit', 0):.2f}\n"
            message += f"Volume: {best_trade.get('volume', 0)}\n"
            message += f"Entry: {best_trade.get('entry_price', 0)} → Exit: {best_trade.get('exit_price', 0)}\n"
            if best_trade.get('entry_time'):
                message += f"Time: {best_trade.get('entry_time')} → {best_trade.get('exit_time', 'N/A')}\n"
            if best_trade.get('duration'):
                message += f"Duration: {best_trade.get('duration')}\n"
            message += "\n"
        
        if worst_trade:
            message += f"<b>📉 Worst Trade</b>\n"
            message += f"Ticket: {worst_trade.get('ticket', 'N/A')}\n"
            message += f"Symbol: {worst_trade.get('symbol', 'N/A')} ({worst_trade.get('type', 'N/A')})\n"
            message += f"Loss: 📉 {worst_trade.get('profit', 0):.2f}\n"
            message += f"Volume: {worst_trade.get('volume', 0)}\n"
            message += f"Entry: {worst_trade.get('entry_price', 0)} → Exit: {worst_trade.get('exit_price', 0)}\n"
            if worst_trade.get('entry_time'):
                message += f"Time: {worst_trade.get('entry_time')} → {worst_trade.get('exit_time', 'N/A')}\n"
            if worst_trade.get('duration'):
                message += f"Duration: {worst_trade.get('duration')}\n"
            message += "\n"
        
        # Additional Info
        if total_volume > 0 or total_commission > 0 or total_swap != 0:
            message += f"<b>📊 Additional Info</b>\n"
            if total_volume > 0:
                message += f"Total Volume: {total_volume:.2f} lots\n"
            if total_commission > 0:
                message += f"Total Commission: {total_commission:.2f}\n"
            if total_swap != 0:
                message += f"Total Swap: {total_swap:.2f}\n"
            message += "\n"
        
        message += "━" * 30 + "\n"
        message += f"📅 Period: {stats.get('start_time', 'N/A')} - {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return message
    
    async def send_daily_summary(self, stats: dict) -> bool:
        """Send daily performance summary to Telegram"""
        message = self.format_daily_summary(stats)
        return await self.send_message(message)
    
    def format_help(self) -> str:
        """Format help message for /help command"""
        message = "🤖 <b>MT5 Trade Alerts Bot - Commands</b>\n\n"
        message += "<b>Available Commands:</b>\n\n"
        message += "/status - Show account balance, equity, margin, and open positions count\n"
        message += "/positions - List all open positions with current P/L\n"
        message += "/orders - List all pending orders\n"
        message += "/summary - Show daily P/L summary\n"
        message += "/summary weekly - Show weekly P/L summary\n"
        message += "/summary monthly - Show monthly P/L summary\n"
        message += "/help - Show this help message\n\n"
        message += "The bot automatically sends alerts for:\n"
        message += "• New trades (open/close)\n"
        message += "• New orders (pending/executed)\n"
        message += "• Price level alerts\n"
        message += "• Pending order proximity warnings\n"
        message += "• Profit-taking suggestions"
        
        return message
    
    def _check_authorized(self, update: Update) -> bool:
        """Check if the user is authorized (same chat_id)"""
        if not update.message or not update.message.chat:
            return False
        return str(update.message.chat.id) == str(self.chat_id)
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.mt5_monitor:
            await update.message.reply_text("❌ MT5 monitor not available.")
            return
        
        account_info = self.mt5_monitor.get_account_info()
        message = self.format_status(account_info)
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.mt5_monitor:
            await update.message.reply_text("❌ MT5 monitor not available.")
            return
        
        positions = self.mt5_monitor.get_all_positions()
        message = self.format_positions(positions)
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /orders command"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.mt5_monitor:
            await update.message.reply_text("❌ MT5 monitor not available.")
            return
        
        orders = self.mt5_monitor.get_all_orders()
        message = self.format_orders(orders)
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /summary command"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.mt5_monitor:
            await update.message.reply_text("❌ MT5 monitor not available.")
            return
        
        period = 'daily'
        if context.args and len(context.args) > 0:
            period_arg = context.args[0].lower()
            if period_arg in ['daily', 'weekly', 'monthly']:
                period = period_arg
        
        summary = self.mt5_monitor.get_pl_summary(period=period)
        message = self.format_summary(summary)
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        message = self.format_help()
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def setup_commands(self):
        """Setup command handlers"""
        if not self.application:
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("status", self.handle_status))
            self.application.add_handler(CommandHandler("positions", self.handle_positions))
            self.application.add_handler(CommandHandler("orders", self.handle_orders))
            self.application.add_handler(CommandHandler("summary", self.handle_summary))
            self.application.add_handler(CommandHandler("help", self.handle_help))
            self.application.add_handler(CommandHandler("start", self.handle_help))
            
            # Start polling
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)
            logger.info("Telegram bot command handlers initialized")
    
    def format_margin_alert(self, alert: dict) -> str:
        """Format margin level alert"""
        alert_type = alert.get('type', 'warning')
        margin_level = alert.get('margin_level', 0)
        threshold = alert.get('threshold', 0)
        
        if alert_type == 'critical':
            emoji = "🚨"
            title = "CRITICAL: Margin Call Warning"
            urgency = "URGENT"
        else:
            emoji = "⚠️"
            title = "Margin Level Warning"
            urgency = "Warning"
        
        message = f"{emoji} <b>{title}</b>\n\n"
        message += f"Margin Level: {margin_level:.2f}%\n"
        message += f"Threshold: {threshold:.2f}%\n\n"
        message += f"Balance: {alert.get('balance', 0):.2f}\n"
        message += f"Equity: {alert.get('equity', 0):.2f}\n"
        message += f"Margin: {alert.get('margin', 0):.2f}\n"
        message += f"Free Margin: {alert.get('free_margin', 0):.2f}\n\n"
        message += f"<b>{urgency}:</b> Your margin level is critically low. Consider closing positions or adding funds."
        
        return message
    
    def format_position_size_alert(self, alert: dict) -> str:
        """Format position size warning alert"""
        emoji = "⚠️"
        
        message = f"{emoji} <b>Position Size Warning</b>\n\n"
        message += f"Symbol: {alert.get('symbol', 'N/A')}\n"
        message += f"Ticket: {alert.get('ticket', 'N/A')}\n"
        message += f"Volume: {alert.get('volume', 0)}\n\n"
        message += f"Position Size: {alert.get('position_size_pct', 0):.2f}% of account\n"
        message += f"Maximum Allowed: {alert.get('max_size_pct', 0):.2f}%\n"
        message += f"Margin Used: {alert.get('margin_used', 0):.2f}\n"
        message += f"Account Balance: {alert.get('balance', 0):.2f}\n\n"
        message += f"⚠️ This position is larger than your risk management limit!"
        
        return message
    
    def format_daily_loss_alert(self, alert: dict) -> str:
        """Format daily loss limit alert"""
        emoji = "🚨"
        alert_type = alert.get('type', 'daily_loss_pct')
        
        message = f"{emoji} <b>Daily Loss Limit Alert</b>\n\n"
        
        if alert_type == 'daily_loss_pct':
            message += f"Daily Loss: {alert.get('daily_loss', 0):.2f}\n"
            message += f"Loss Percentage: {alert.get('loss_pct', 0):.2f}%\n"
            message += f"Limit: {alert.get('limit_pct', 0):.2f}%\n"
        else:
            message += f"Daily Loss: {alert.get('daily_loss', 0):.2f}\n"
            message += f"Loss Limit: {alert.get('loss_limit', 0):.2f}\n"
        
        message += f"\nBalance: {alert.get('balance', 0):.2f}\n"
        message += f"Closed P/L: {alert.get('closed_profit', 0):.2f}\n"
        message += f"Open P/L: {alert.get('open_profit', 0):.2f}\n\n"
        message += f"🚨 Your daily loss limit has been exceeded. Consider stopping trading for today."
        
        return message
    
    def format_drawdown_alert(self, alert: dict) -> str:
        """Format drawdown alert"""
        emoji = "📉"
        
        message = f"{emoji} <b>Drawdown Alert</b>\n\n"
        message += f"Drawdown: {alert.get('drawdown_pct', 0):.2f}%\n"
        message += f"Limit: {alert.get('limit_pct', 0):.2f}%\n"
        message += f"Drawdown Amount: {alert.get('drawdown_amount', 0):.2f}\n\n"
        message += f"Initial Balance: {alert.get('initial_balance', 0):.2f}\n"
        message += f"Current Balance: {alert.get('current_balance', 0):.2f}\n"
        message += f"Equity: {alert.get('equity', 0):.2f}\n"
        message += f"Total P/L: {alert.get('profit', 0):.2f}\n\n"
        message += f"📉 Your account drawdown has exceeded the limit. Review your risk management."
        
        return message
    
    async def send_margin_alert(self, alert: dict) -> bool:
        """Send margin level alert"""
        message = self.format_margin_alert(alert)
        return await self.send_message(message)
    
    async def send_position_size_alert(self, alert: dict) -> bool:
        """Send position size warning alert"""
        message = self.format_position_size_alert(alert)
        return await self.send_message(message)
    
    async def send_daily_loss_alert(self, alert: dict) -> bool:
        """Send daily loss limit alert"""
        message = self.format_daily_loss_alert(alert)
        return await self.send_message(message)
    
    async def send_drawdown_alert(self, alert: dict) -> bool:
        """Send drawdown alert"""
        message = self.format_drawdown_alert(alert)
        return await self.send_message(message)
    
    async def stop_commands(self):
        """Stop command handlers"""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram bot command handlers stopped")

