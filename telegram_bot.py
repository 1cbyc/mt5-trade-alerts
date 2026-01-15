from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
import logging
from typing import Optional, Callable
from datetime import datetime, timedelta
import io
import os

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
        self.enabled = True
        self.application = None
        self.mt5_monitor = None  # Will be set by main service
        self.trade_db = None  # Will be set by main service
        self.chart_generator = None  # Will be set by main service
    
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
        recurring = alert.get('recurring', False)
        description = alert.get('description', '')
        group = alert.get('group')
        
        emoji = "🎯"
        if recurring:
            emoji = "🔄"
        
        message = f"{emoji} <b>Price Level Reached</b>\n\n"
        message += f"Symbol: {symbol}\n"
        message += f"Level ID: {level_id}\n"
        if description:
            message += f"Description: {description}\n"
        message += f"Target Price: {level_price}\n"
        message += f"Current Price: {current_price}\n"
        message += f"Direction: {level_type}\n"
        if recurring:
            message += f"Type: 🔄 Recurring Alert\n"
        else:
            message += f"Type: ⚡ One-time Alert\n"
        if group:
            message += f"Group: {group}\n"
        message += f"Time: {time}"
        
        return message
    
    def format_level_group_alert(self, alert: dict) -> str:
        """Format price level group alert for Telegram"""
        symbol = alert.get('symbol', 'N/A')
        group_id = alert.get('group_id', 'unknown')
        description = alert.get('description', '')
        triggered_count = alert.get('triggered_count', 0)
        required_count = alert.get('required_count', 2)
        triggered_levels = alert.get('triggered_levels', [])
        time = alert.get('time', 'N/A')
        
        emoji = "🎯🎯"
        
        message = f"{emoji} <b>Price Level Group Triggered</b>\n\n"
        message += f"Symbol: {symbol}\n"
        message += f"Group ID: {group_id}\n"
        if description:
            message += f"Description: {description}\n"
        message += f"\n✅ Triggered Levels: {triggered_count}/{required_count}\n"
        message += f"Levels: {', '.join(triggered_levels)}\n"
        message += f"\nTime: {time}"
        
        return message
    
    async def send_level_group_alert(self, alert: dict) -> bool:
        """Send price level group alert to Telegram"""
        message = self.format_level_group_alert(alert)
        return await self.send_message(message)
    
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
        
        # Check if ML-enhanced
        ml_enhanced = suggestion.get('ml_enhanced', False)
        emoji = "🤖" if ml_enhanced else "💡"
        
        message = f"{emoji} <b>Profit-Taking Suggestion</b>"
        if ml_enhanced:
            message += " <i>(ML-Enhanced)</i>"
        message += "\n\n"
        
        message += f"Symbol: {symbol}\n"
        message += f"Ticket: {ticket}\n"
        message += f"Type: {trade_type}\n"
        message += f"Current Profit: 💰 {profit:.2f} ({profit_pct:.2f}%)\n"
        message += f"Open Price: {price_open}\n"
        message += f"Current Price: {price_current}\n"
        
        if ml_enhanced:
            ml_confidence = suggestion.get('ml_confidence', 'low')
            ml_reason = suggestion.get('ml_reason', '')
            learned_target = suggestion.get('ml_learned_target', 0)
            
            confidence_emoji = "🔥" if ml_confidence == 'very_high' else "⭐" if ml_confidence == 'high' else "💭"
            message += f"\n{confidence_emoji} <b>ML Analysis:</b>\n"
            message += f"Confidence: {ml_confidence.upper()}\n"
            if learned_target > 0:
                message += f"Your avg exit target: {learned_target:.2f}%\n"
            if ml_reason:
                message += f"Reason: {ml_reason}\n"
        
        message += f"\n💡 <b>Suggestion:</b> Consider closing {volume_to_close} lots to secure profits\n"
        message += f"Remaining: {volume - volume_to_close} lots"
        
        return message
    
    def format_volatility_alert(self, alert: dict) -> str:
        """Format volatility-based position sizing alert for Telegram"""
        symbol = alert.get('symbol', 'N/A')
        current_volume = alert.get('current_volume', 0)
        suggested_volume = alert.get('suggested_volume', 0)
        volatility_level = alert.get('volatility_level', 'N/A')
        recommendation = alert.get('recommendation', '')
        message_text = alert.get('message', '')
        
        emoji = "⚠️" if alert.get('type') == 'position_too_large' else "💡"
        
        alert_message = f"{emoji} <b>Volatility Position Sizing Alert</b>\n\n"
        alert_message += f"Symbol: {symbol}\n"
        alert_message += f"Current Volume: {current_volume}\n"
        alert_message += f"Suggested Volume: {suggested_volume}\n"
        alert_message += f"Volatility Level: {volatility_level.upper()}\n"
        alert_message += f"\n{message_text}\n"
        alert_message += f"\n<b>Recommendation:</b> {recommendation}"
        
        return alert_message
    
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
    
    def set_trade_db(self, trade_db):
        """Set the TradeHistoryDB instance for command handlers"""
        self.trade_db = trade_db
    
    def set_chart_generator(self, chart_generator):
        """Set the ChartGenerator instance for command handlers"""
        self.chart_generator = chart_generator
    
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
        message += "<b>📊 Information Commands:</b>\n"
        message += "/status - Show account balance, equity, margin, and open positions count\n"
        message += "/positions - List all open positions with current P/L\n"
        message += "/orders - List all pending orders\n"
        message += "/summary - Show daily P/L summary\n"
        message += "/summary weekly - Show weekly P/L summary\n"
        message += "/summary monthly - Show monthly P/L summary\n\n"
        message += "<b>⚡ Trading Commands:</b>\n"
        message += "/close &lt;ticket&gt; - Close specific position\n"
        message += "/closeall - Close all open positions\n"
        message += "/modify &lt;ticket&gt; [sl] [tp] - Modify stop loss/take profit\n"
        message += "  Example: /modify 123456 1.1000 1.1100\n"
        message += "  Use 0 to remove SL/TP\n"
        message += "/partial &lt;ticket&gt; &lt;volume&gt; - Partially close position\n"
        message += "  Example: /partial 123456 0.5\n\n"
        message += "<b>📊 Analytics Commands:</b>\n"
        message += "/chart [type] [days] - Generate performance charts\n"
        message += "  Types: summary, equity, daily, distribution\n"
        message += "  Example: /chart summary 30\n"
        message += "/history [days=X] [symbol=X] [limit=X] - View trade history\n"
        message += "  Example: /history days=7 symbol=EURUSD limit=10\n"
        message += "/note &lt;ticket&gt; &lt;note&gt; - Add note to a trade\n"
        message += "  Example: /note 123456 Good entry point\n"
        message += "/export [days=X] [symbol=X] - Export trades to CSV\n"
        message += "  Example: /export days=30 symbol=EURUSD\n\n"
        message += "<b>🤖 Smart Features:</b>\n"
        message += "/mlinsights [symbol] - Show ML trading insights\n"
        message += "  Example: /mlinsights EURUSD\n"
        message += "/volatility &lt;symbol&gt; - Show volatility and position sizing\n"
        message += "  Example: /volatility EURUSD\n\n"
        message += "/help - Show this help message\n\n"
        message += "<b>🔔 Automatic Alerts:</b>\n"
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
    
    async def handle_close(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /close <ticket> command"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.mt5_monitor:
            await update.message.reply_text("❌ MT5 monitor not available.")
            return
        
        if not context.args or len(context.args) == 0:
            await update.message.reply_text("❌ Usage: /close <ticket>\nExample: /close 123456")
            return
        
        try:
            ticket = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid ticket number. Ticket must be a number.")
            return
        
        result = self.mt5_monitor.close_position(ticket)
        
        if result.get('success'):
            message = f"✅ <b>Position Closed</b>\n\n"
            message += f"Ticket: {result.get('ticket')}\n"
            message += f"Symbol: {result.get('symbol')}\n"
            message += f"Volume: {result.get('volume')}\n"
            message += f"Price: {result.get('price')}\n"
            profit = result.get('profit', 0)
            profit_emoji = "💰" if profit >= 0 else "📉"
            message += f"Profit: {profit_emoji} {profit:.2f}\n"
            message += f"Deal Ticket: {result.get('deal_ticket')}"
        else:
            message = f"❌ <b>Failed to Close Position</b>\n\n"
            message += f"Error: {result.get('error', 'Unknown error')}"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_closeall(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /closeall command"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.mt5_monitor:
            await update.message.reply_text("❌ MT5 monitor not available.")
            return
        
        result = self.mt5_monitor.close_all_positions()
        
        if result.get('success'):
            message = f"✅ <b>Close All Positions</b>\n\n"
            message += f"Closed: {result.get('closed_count')} positions\n"
            message += f"Failed: {result.get('failed_count')} positions\n"
            message += f"Total: {result.get('total_positions')} positions\n"
            total_profit = result.get('total_profit', 0)
            profit_emoji = "💰" if total_profit >= 0 else "📉"
            message += f"\nTotal Profit: {profit_emoji} {total_profit:.2f}"
            
            if result.get('errors'):
                message += f"\n\n⚠️ <b>Errors:</b>\n"
                for error in result.get('errors', [])[:5]:  # Show first 5 errors
                    message += f"• {error}\n"
                if len(result.get('errors', [])) > 5:
                    message += f"... and {len(result.get('errors', [])) - 5} more"
        else:
            message = f"ℹ️ {result.get('message', 'No positions to close')}"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_modify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /modify <ticket> <sl> <tp> command"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.mt5_monitor:
            await update.message.reply_text("❌ MT5 monitor not available.")
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text("❌ Usage: /modify <ticket> [sl] [tp]\n\nExamples:\n/modify 123456 1.1000 1.1100 - Set SL and TP\n/modify 123456 0 - Remove SL (keep TP)\n/modify 123456 1.1000 0 - Set SL, remove TP\n/modify 123456 0 0 - Remove both SL and TP")
            return
        
        try:
            ticket = int(context.args[0])
            # Parse SL - use special value -1 to indicate "remove" (0 means remove, None means keep current)
            if len(context.args) > 1:
                if context.args[1].lower() in ['none', 'remove', 'delete']:
                    sl = -1  # Special value to indicate removal
                elif context.args[1].lower() == 'keep':
                    sl = None  # Keep current
                else:
                    sl = float(context.args[1])
                    if sl == 0:
                        sl = -1  # 0 means remove
            else:
                sl = None  # Not provided, keep current
            
            # Parse TP - use special value -1 to indicate "remove"
            if len(context.args) > 2:
                if context.args[2].lower() in ['none', 'remove', 'delete']:
                    tp = -1  # Special value to indicate removal
                elif context.args[2].lower() == 'keep':
                    tp = None  # Keep current
                else:
                    tp = float(context.args[2])
                    if tp == 0:
                        tp = -1  # 0 means remove
            else:
                tp = None  # Not provided, keep current
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Invalid arguments. Usage: /modify <ticket> [sl] [tp]\nExample: /modify 123456 1.1000 1.1100\nUse 0 to remove SL/TP")
            return
        
        # Convert -1 back to 0 for the modify_position method (which treats 0 as remove)
        sl_to_send = 0.0 if sl == -1 else sl
        tp_to_send = 0.0 if tp == -1 else tp
        
        result = self.mt5_monitor.modify_position(ticket, sl=sl_to_send, tp=tp_to_send)
        
        if result.get('success'):
            message = f"✅ <b>Position Modified</b>\n\n"
            message += f"Ticket: {result.get('ticket')}\n"
            message += f"Symbol: {result.get('symbol')}\n"
            if result.get('sl') is not None:
                message += f"Stop Loss: {result.get('sl')}\n"
            else:
                message += f"Stop Loss: Removed\n"
            if result.get('tp') is not None:
                message += f"Take Profit: {result.get('tp')}\n"
            else:
                message += f"Take Profit: Removed\n"
        else:
            message = f"❌ <b>Failed to Modify Position</b>\n\n"
            message += f"Error: {result.get('error', 'Unknown error')}"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_partial(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /partial <ticket> <volume> command"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.mt5_monitor:
            await update.message.reply_text("❌ MT5 monitor not available.")
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("❌ Usage: /partial <ticket> <volume>\nExample: /partial 123456 0.5")
            return
        
        try:
            ticket = int(context.args[0])
            volume = float(context.args[1])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Invalid arguments. Usage: /partial <ticket> <volume>\nExample: /partial 123456 0.5")
            return
        
        result = self.mt5_monitor.partial_close(ticket, volume)
        
        if result.get('success'):
            message = f"✅ <b>Position Partially Closed</b>\n\n"
            message += f"Ticket: {result.get('ticket')}\n"
            message += f"Symbol: {result.get('symbol')}\n"
            message += f"Volume Closed: {result.get('volume_closed')}\n"
            message += f"Volume Remaining: {result.get('volume_remaining')}\n"
            message += f"Price: {result.get('price')}\n"
            profit = result.get('profit', 0)
            profit_emoji = "💰" if profit >= 0 else "📉"
            message += f"Profit: {profit_emoji} {profit:.2f}\n"
            message += f"Deal Ticket: {result.get('deal_ticket')}"
        else:
            message = f"❌ <b>Failed to Partially Close Position</b>\n\n"
            message += f"Error: {result.get('error', 'Unknown error')}"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_chart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /chart command - Generate and send performance charts"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.trade_db or not self.chart_generator:
            await update.message.reply_text("❌ Trade history or charts not available.")
            return
        
        # Parse chart type (default: summary)
        chart_type = 'summary'
        if context.args and len(context.args) > 0:
            chart_type = context.args[0].lower()
        
        # Parse period (default: 30 days)
        days = 30
        if context.args and len(context.args) > 1:
            try:
                days = int(context.args[1])
            except ValueError:
                pass
        
        start_date = datetime.now() - timedelta(days=days)
        trades = self.trade_db.get_trades(start_date=start_date)
        
        if not trades:
            await update.message.reply_text(f"❌ No trades found in the last {days} days.")
            return
        
        try:
            # Generate chart based on type
            chart_bytes = None
            chart_name = ""
            
            if chart_type == 'equity':
                chart_bytes = self.chart_generator.generate_equity_curve(trades)
                chart_name = "Equity Curve"
            elif chart_type == 'daily':
                chart_bytes = self.chart_generator.generate_daily_pnl_chart(trades)
                chart_name = "Daily P/L"
            elif chart_type == 'distribution':
                chart_bytes = self.chart_generator.generate_win_loss_distribution(trades)
                chart_name = "Win/Loss Distribution"
            else:  # summary
                chart_bytes = self.chart_generator.generate_performance_summary_chart(trades)
                chart_name = "Performance Summary"
            
            if chart_bytes:
                await update.message.reply_photo(
                    photo=io.BytesIO(chart_bytes),
                    caption=f"📊 <b>{chart_name}</b>\nPeriod: Last {days} days\nTrades: {len(trades)}",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text("❌ Failed to generate chart.")
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            await update.message.reply_text(f"❌ Error generating chart: {str(e)}")
    
    async def handle_note(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /note <ticket> <note> command - Add note to a trade"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.trade_db:
            await update.message.reply_text("❌ Trade history not available.")
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("❌ Usage: /note <ticket> <note text>\nExample: /note 123456 Good entry, followed trend")
            return
        
        try:
            ticket = int(context.args[0])
            note = ' '.join(context.args[1:])
            
            if self.trade_db.add_trade_note(ticket, note):
                trade = self.trade_db.get_trade(ticket)
                if trade:
                    message = f"✅ <b>Note Added</b>\n\n"
                    message += f"Ticket: {ticket}\n"
                    message += f"Symbol: {trade.get('symbol', 'N/A')}\n"
                    message += f"Note: {note}"
                else:
                    message = f"✅ Note added to trade {ticket}\n\nNote: {note}"
            else:
                message = f"❌ Trade {ticket} not found in history."
            
            await update.message.reply_text(message, parse_mode='HTML')
        except ValueError:
            await update.message.reply_text("❌ Invalid ticket number.")
        except Exception as e:
            logger.error(f"Error adding note: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def handle_export(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /export command - Export trade data to CSV"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.trade_db:
            await update.message.reply_text("❌ Trade history not available.")
            return
        
        # Parse optional filters
        days = None
        symbol = None
        
        if context.args:
            for arg in context.args:
                if arg.startswith('days='):
                    try:
                        days = int(arg.split('=')[1])
                    except ValueError:
                        pass
                elif arg.startswith('symbol='):
                    symbol = arg.split('=')[1]
        
        start_date = None
        if days:
            start_date = datetime.now() - timedelta(days=days)
        
        # Generate CSV file
        csv_path = f"trades_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if self.trade_db.export_to_csv(csv_path, start_date=start_date, symbol=symbol):
            try:
                with open(csv_path, 'rb') as f:
                    filters = []
                    if days:
                        filters.append(f"Last {days} days")
                    if symbol:
                        filters.append(f"Symbol: {symbol}")
                    filter_text = f"\nFilters: {', '.join(filters)}" if filters else ""
                    
                    await update.message.reply_document(
                        document=f,
                        caption=f"📊 <b>Trade History Export</b>{filter_text}",
                        parse_mode='HTML'
                    )
                os.remove(csv_path)  # Clean up
            except Exception as e:
                logger.error(f"Error sending CSV: {e}")
                await update.message.reply_text(f"❌ Error sending file: {str(e)}")
        else:
            await update.message.reply_text("❌ No trades found to export.")
    
    async def handle_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command - View trade history"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.trade_db:
            await update.message.reply_text("❌ Trade history not available.")
            return
        
        # Parse optional filters
        days = 7
        symbol = None
        limit = 20
        
        if context.args:
            for arg in context.args:
                if arg.startswith('days='):
                    try:
                        days = int(arg.split('=')[1])
                    except ValueError:
                        pass
                elif arg.startswith('symbol='):
                    symbol = arg.split('=')[1]
                elif arg.startswith('limit='):
                    try:
                        limit = int(arg.split('=')[1])
                    except ValueError:
                        pass
        
        start_date = datetime.now() - timedelta(days=days)
        trades = self.trade_db.get_trades(start_date=start_date, symbol=symbol, limit=limit)
        
        if not trades:
            await update.message.reply_text(f"❌ No trades found in the last {days} days.")
            return
        
        message = f"📊 <b>Trade History</b>\n\n"
        message += f"Period: Last {days} days\n"
        if symbol:
            message += f"Symbol: {symbol}\n"
        message += f"Total: {len(trades)} trades\n\n"
        
        total_profit = 0.0
        for i, trade in enumerate(trades[:limit], 1):
            profit = trade.get('profit', 0)
            total_profit += profit
            profit_emoji = "💰" if profit >= 0 else "📉"
            
            time_close = trade.get('time_close') or trade.get('time', 'N/A')
            if isinstance(time_close, str) and len(time_close) > 10:
                time_close = time_close[:10]  # Just date
            
            message += f"{i}. <b>{trade.get('symbol', 'N/A')}</b> {trade.get('type', 'N/A')}\n"
            message += f"   Ticket: {trade.get('ticket')} | {profit_emoji} {profit:.2f}\n"
            message += f"   {time_close}\n\n"
        
        message += f"<b>Total P/L: {total_profit:.2f}</b>"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_ml_insights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mlinsights command - Show ML trading insights"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not self.trade_db:
            await update.message.reply_text("❌ Trade history not available.")
            return
        
        # Get ML analyzer from main service (will be set)
        if not hasattr(self, 'ml_analyzer') or not self.ml_analyzer:
            await update.message.reply_text("❌ ML analyzer not available.")
            return
        
        symbol = None
        if context.args and len(context.args) > 0:
            symbol = context.args[0]
        
        # Get insights
        insights = self.ml_analyzer.get_insights(symbol=symbol)
        
        if not insights.get('available'):
            await update.message.reply_text(f"❌ {insights.get('message', 'No insights available')}")
            return
        
        message = "🤖 <b>ML Trading Insights</b>\n\n"
        if symbol:
            message += f"Symbol: {symbol}\n"
        message += f"Trades Analyzed: {insights['trades_analyzed']}\n"
        message += f"Winning Trades: {insights['winning_trades']}\n"
        message += f"Losing Trades: {insights['losing_trades']}\n"
        message += f"Win Rate: {insights['win_rate']:.1f}%\n\n"
        
        message += "<b>Learned Patterns:</b>\n"
        message += f"Avg Winning Profit: {insights['avg_winning_profit']:.2f}\n"
        message += f"Avg Profit Target: {insights['avg_profit_target_pct']:.2f}%\n"
        message += f"Avg Hold Time: {insights['avg_hold_time_hours']:.1f} hours\n"
        message += f"Risk/Reward Ratio: {insights['risk_reward_ratio']:.2f}\n"
        
        if insights.get('profit_distribution'):
            message += f"\n<b>Profit Distribution:</b>\n"
            for range_name, count in insights['profit_distribution'].items():
                message += f"{range_name}: {count} trades\n"
        
        message += f"\n<i>Last updated: {insights.get('last_updated', 'N/A')}</i>"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_volatility(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /volatility <symbol> command - Show volatility info and position sizing suggestion"""
        if not self._check_authorized(update):
            await update.message.reply_text("❌ Unauthorized access.")
            return
        
        if not context.args or len(context.args) == 0:
            await update.message.reply_text("❌ Usage: /volatility <symbol>\nExample: /volatility EURUSD")
            return
        
        symbol = context.args[0]
        
        # Get volatility calculator from main service (will be set)
        if not hasattr(self, 'volatility_calc') or not self.volatility_calc:
            await update.message.reply_text("❌ Volatility calculator not available.")
            return
        
        # Get account balance
        if not self.mt5_monitor:
            await update.message.reply_text("❌ MT5 monitor not available.")
            return
        
        account_info = self.mt5_monitor.get_account_info()
        if not account_info:
            await update.message.reply_text("❌ Could not get account information.")
            return
        
        account_balance = account_info.get('balance', 0)
        
        # Get volatility metrics
        volatility = self.volatility_calc.calculate_volatility(symbol)
        if not volatility:
            await update.message.reply_text(f"❌ Could not calculate volatility for {symbol}")
            return
        
        # Get position size suggestion
        suggestion = self.volatility_calc.suggest_position_size(
            symbol=symbol,
            account_balance=account_balance
        )
        
        message = f"📊 <b>Volatility Analysis: {symbol}</b>\n\n"
        message += f"Current Price: {volatility['current_price']}\n"
        message += f"Volatility Level: {volatility['volatility_level'].upper()}\n"
        message += f"Std Deviation: {volatility['volatility_std']:.2f}%\n"
        message += f"ATR: {volatility['atr']:.5f} ({volatility['atr_pct']:.2f}%)\n"
        message += f"Avg Move: {volatility['avg_move_pct']:.2f}%\n"
        message += f"Max Move: {volatility['max_move_pct']:.2f}%\n"
        
        if suggestion:
            message += f"\n<b>Position Size Suggestion:</b>\n"
            message += f"Suggested Volume: {suggestion['suggested_volume']}\n"
            message += f"Risk Amount: {suggestion['risk_amount']:.2f}\n"
            message += f"Actual Risk: {suggestion['actual_risk_pct']:.2f}%\n"
            message += f"Adjustment: {suggestion['adjustment_factor']:.1f}x\n"
            message += f"\n<i>{suggestion['reason']}</i>"
        
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
            self.application.add_handler(CommandHandler("close", self.handle_close))
            self.application.add_handler(CommandHandler("closeall", self.handle_closeall))
            self.application.add_handler(CommandHandler("modify", self.handle_modify))
            self.application.add_handler(CommandHandler("partial", self.handle_partial))
            self.application.add_handler(CommandHandler("chart", self.handle_chart))
            self.application.add_handler(CommandHandler("note", self.handle_note))
            self.application.add_handler(CommandHandler("export", self.handle_export))
            self.application.add_handler(CommandHandler("history", self.handle_history))
            self.application.add_handler(CommandHandler("mlinsights", self.handle_ml_insights))
            self.application.add_handler(CommandHandler("volatility", self.handle_volatility))
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

