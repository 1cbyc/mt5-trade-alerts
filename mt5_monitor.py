import MetaTrader5 as mt5
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MT5Monitor:
    def __init__(self, login: int, password: str, server: str, path: str = None):
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.connected = False
        self.last_trade_ticket = None
        self.last_order_ticket = None
        self.tracked_positions = {}
        self.tracked_orders = {}
        
    def connect(self) -> bool:
        """Initialize and connect to MT5 terminal"""
        if self.path:
            if not mt5.initialize(path=self.path):
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
        else:
            if not mt5.initialize():
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False
        
        authorized = mt5.login(self.login, password=self.password, server=self.server)
        if not authorized:
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False
        
        self.connected = True
        account_info = mt5.account_info()
        if account_info:
            logger.info(f"Connected to MT5. Account: {account_info.login}, Balance: {account_info.balance}")
        
        # Initialize tracking
        self._update_tracked_items()
        return True
    
    def disconnect(self):
        """Disconnect from MT5"""
        mt5.shutdown()
        self.connected = False
        logger.info("Disconnected from MT5")
    
    def _update_tracked_items(self):
        """Update tracked positions and orders"""
        # Track open positions
        positions = mt5.positions_get()
        if positions:
            for pos in positions:
                self.tracked_positions[pos.ticket] = {
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': pos.type,
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'profit': pos.profit,
                    'time': pos.time
                }
                if self.last_trade_ticket is None or pos.ticket > self.last_trade_ticket:
                    self.last_trade_ticket = pos.ticket
        
        # Track pending orders
        orders = mt5.orders_get()
        if orders:
            for order in orders:
                self.tracked_orders[order.ticket] = {
                    'ticket': order.ticket,
                    'symbol': order.symbol,
                    'type': order.type,
                    'volume': order.volume_initial,
                    'price_open': order.price_open,
                    'price_current': order.price_current,
                    'time_setup': order.time_setup,
                    'time_expiration': order.time_expiration
                }
                if self.last_order_ticket is None or order.ticket > self.last_order_ticket:
                    self.last_order_ticket = order.ticket
    
    def get_new_positions(self) -> List[Dict]:
        """Get newly opened positions since last check"""
        if not self.connected:
            return []
        
        new_positions = []
        positions = mt5.positions_get()
        
        if positions:
            for pos in positions:
                if pos.ticket not in self.tracked_positions:
                    new_positions.append({
                        'ticket': pos.ticket,
                        'symbol': pos.symbol,
                        'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                        'volume': pos.volume,
                        'price_open': pos.price_open,
                        'price_current': pos.price_current,
                        'profit': pos.profit,
                        'time': datetime.fromtimestamp(pos.time).strftime('%Y-%m-%d %H:%M:%S')
                    })
                    self.tracked_positions[pos.ticket] = {
                        'ticket': pos.ticket,
                        'symbol': pos.symbol,
                        'type': pos.type,
                        'volume': pos.volume,
                        'price_open': pos.price_open,
                        'price_current': pos.price_current,
                        'profit': pos.profit,
                        'time': pos.time
                    }
                else:
                    # Update existing position
                    tracked = self.tracked_positions[pos.ticket]
                    tracked['price_current'] = pos.price_current
                    tracked['profit'] = pos.profit
        
        # Check for closed positions
        tracked_tickets = set(self.tracked_positions.keys())
        current_tickets = {pos.ticket for pos in positions} if positions else set()
        closed_tickets = tracked_tickets - current_tickets
        
        for ticket in closed_tickets:
            closed_pos = self.tracked_positions.pop(ticket)
            new_positions.append({
                'ticket': closed_pos['ticket'],
                'symbol': closed_pos['symbol'],
                'type': 'CLOSED',
                'volume': closed_pos['volume'],
                'price_open': closed_pos['price_open'],
                'profit': closed_pos['profit'],
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return new_positions
    
    def get_new_orders(self) -> List[Dict]:
        """Get newly placed or modified orders since last check"""
        if not self.connected:
            return []
        
        new_orders = []
        orders = mt5.orders_get()
        
        if orders:
            for order in orders:
                if order.ticket not in self.tracked_orders:
                    order_type_map = {
                        mt5.ORDER_TYPE_BUY_LIMIT: 'BUY LIMIT',
                        mt5.ORDER_TYPE_SELL_LIMIT: 'SELL LIMIT',
                        mt5.ORDER_TYPE_BUY_STOP: 'BUY STOP',
                        mt5.ORDER_TYPE_SELL_STOP: 'SELL STOP',
                        mt5.ORDER_TYPE_BUY_STOP_LIMIT: 'BUY STOP LIMIT',
                        mt5.ORDER_TYPE_SELL_STOP_LIMIT: 'SELL STOP LIMIT'
                    }
                    
                    new_orders.append({
                        'ticket': order.ticket,
                        'symbol': order.symbol,
                        'type': order_type_map.get(order.type, 'UNKNOWN'),
                        'volume': order.volume_initial,
                        'price_open': order.price_open,
                        'price_current': order.price_current,
                        'time_setup': datetime.fromtimestamp(order.time_setup).strftime('%Y-%m-%d %H:%M:%S'),
                        'time_expiration': datetime.fromtimestamp(order.time_expiration).strftime('%Y-%m-%d %H:%M:%S') if order.time_expiration > 0 else 'No expiration'
                    })
                    self.tracked_orders[order.ticket] = {
                        'ticket': order.ticket,
                        'symbol': order.symbol,
                        'type': order.type,
                        'volume': order.volume_initial,
                        'price_open': order.price_open,
                        'price_current': order.price_current,
                        'time_setup': order.time_setup,
                        'time_expiration': order.time_expiration
                    }
        
        # Check for executed/cancelled orders
        tracked_order_tickets = set(self.tracked_orders.keys())
        current_order_tickets = {order.ticket for order in orders} if orders else set()
        removed_orders = tracked_order_tickets - current_order_tickets
        
        for ticket in removed_orders:
            removed_order = self.tracked_orders.pop(ticket)
            order_type_map = {
                mt5.ORDER_TYPE_BUY_LIMIT: 'BUY LIMIT',
                mt5.ORDER_TYPE_SELL_LIMIT: 'SELL LIMIT',
                mt5.ORDER_TYPE_BUY_STOP: 'BUY STOP',
                mt5.ORDER_TYPE_SELL_STOP: 'SELL STOP',
            }
            new_orders.append({
                'ticket': removed_order['ticket'],
                'symbol': removed_order['symbol'],
                'type': f"{order_type_map.get(removed_order['type'], 'ORDER')} EXECUTED/CANCELLED",
                'volume': removed_order['volume'],
                'price_open': removed_order['price_open'],
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return new_orders
    
    def get_symbol_price(self, symbol: str) -> Optional[Dict]:
        """Get current price for a symbol"""
        if not self.connected:
            return None
        
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            return {
                'symbol': symbol,
                'bid': tick.bid,
                'ask': tick.ask,
                'time': datetime.fromtimestamp(tick.time).strftime('%Y-%m-%d %H:%M:%S')
            }
        return None
    
    def check_price_levels(self, symbol: str, levels: List[Dict]) -> List[Dict]:
        """Check if price has reached any of the specified levels"""
        if not self.connected:
            return []
        
        price_info = self.get_symbol_price(symbol)
        if not price_info:
            return []
        
        triggered = []
        current_price = (price_info['bid'] + price_info['ask']) / 2
        
        for level in levels:
            level_price = level.get('price')
            level_type = level.get('type', 'both')  # 'above', 'below', 'both'
            level_id = level.get('id', 'unknown')
            
            if level_price is None:
                continue
            
            triggered_flag = False
            if level_type == 'above' and current_price >= level_price:
                triggered_flag = True
            elif level_type == 'below' and current_price <= level_price:
                triggered_flag = True
            elif level_type == 'both' and abs(current_price - level_price) < 0.0001:
                triggered_flag = True
            
            if triggered_flag:
                triggered.append({
                    'symbol': symbol,
                    'level_id': level_id,
                    'level_price': level_price,
                    'current_price': current_price,
                    'level_type': level_type,
                    'time': price_info['time']
                })
        
        return triggered
    
    def get_active_instruments(self) -> set:
        """Get all instruments with active positions or orders"""
        if not self.connected:
            return set()
        
        instruments = set()
        
        # Get instruments from positions
        positions = mt5.positions_get()
        if positions:
            for pos in positions:
                instruments.add(pos.symbol)
        
        # Get instruments from orders
        orders = mt5.orders_get()
        if orders:
            for order in orders:
                instruments.add(order.symbol)
        
        return instruments
    
    def analyze_profitable_positions(self, min_profit: float = 10.0, profit_percentage: float = 5.0) -> List[Dict]:
        """Analyze positions and suggest partial closes for profitable trades"""
        if not self.connected:
            return []
        
        suggestions = []
        positions = mt5.positions_get()
        
        if not positions:
            return []
        
        account_info = mt5.account_info()
        account_balance = account_info.balance if account_info else 0
        
        for pos in positions:
            if pos.profit >= min_profit:
                # Calculate profit as percentage of account
                profit_pct = (pos.profit / account_balance * 100) if account_balance > 0 else 0
                
                # Suggest if profit meets threshold
                if profit_pct >= profit_percentage or pos.profit >= min_profit * 2:
                    suggestions.append({
                        'ticket': pos.ticket,
                        'symbol': pos.symbol,
                        'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                        'volume': pos.volume,
                        'volume_to_close': round(pos.volume / 2, 2),  # Suggest closing half
                        'price_open': pos.price_open,
                        'price_current': pos.price_current,
                        'profit': pos.profit,
                        'profit_percentage': round(profit_pct, 2),
                        'time': datetime.fromtimestamp(pos.time).strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        return suggestions

