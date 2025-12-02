from telegram import Bot
from telegram.error import TelegramError
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
        self.enabled = True
    
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

