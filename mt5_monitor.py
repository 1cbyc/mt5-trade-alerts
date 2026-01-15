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
        
        # Get instruments from orders (including pending limits)
        orders = mt5.orders_get()
        if orders:
            for order in orders:
                instruments.add(order.symbol)
        
        return instruments
    
    def get_pending_orders_by_symbol(self) -> Dict[str, List[Dict]]:
        """Get all pending orders grouped by symbol"""
        if not self.connected:
            return {}
        
        orders_by_symbol = {}
        orders = mt5.orders_get()
        
        if orders:
            for order in orders:
                symbol = order.symbol
                if symbol not in orders_by_symbol:
                    orders_by_symbol[symbol] = []
                
                order_type_map = {
                    mt5.ORDER_TYPE_BUY_LIMIT: 'BUY LIMIT',
                    mt5.ORDER_TYPE_SELL_LIMIT: 'SELL LIMIT',
                    mt5.ORDER_TYPE_BUY_STOP: 'BUY STOP',
                    mt5.ORDER_TYPE_SELL_STOP: 'SELL STOP',
                    mt5.ORDER_TYPE_BUY_STOP_LIMIT: 'BUY STOP LIMIT',
                    mt5.ORDER_TYPE_SELL_STOP_LIMIT: 'SELL STOP LIMIT'
                }
                
                orders_by_symbol[symbol].append({
                    'ticket': order.ticket,
                    'type': order_type_map.get(order.type, 'UNKNOWN'),
                    'volume': order.volume_initial,
                    'price_open': order.price_open,
                    'price_current': order.price_current,
                    'time_setup': datetime.fromtimestamp(order.time_setup).strftime('%Y-%m-%d %H:%M:%S'),
                    'time_expiration': datetime.fromtimestamp(order.time_expiration).strftime('%Y-%m-%d %H:%M:%S') if order.time_expiration > 0 else None
                })
        
        return orders_by_symbol
    
    def check_pending_order_proximity(self, symbol: str, threshold_pct: float = 1.0) -> List[Dict]:
        """Check if current price is close to any pending order prices for a symbol"""
        if not self.connected:
            return []
        
        price_info = self.get_symbol_price(symbol)
        if not price_info:
            return []
        
        current_price = (price_info['bid'] + price_info['ask']) / 2
        pending_orders = self.get_pending_orders_by_symbol().get(symbol, [])
        
        alerts = []
        for order in pending_orders:
            order_price = order['price_open']
            price_diff = abs(current_price - order_price)
            price_diff_pct = (price_diff / current_price * 100) if current_price > 0 else 0
            
            if price_diff_pct <= threshold_pct:
                alerts.append({
                    'symbol': symbol,
                    'ticket': order['ticket'],
                    'order_type': order['type'],
                    'order_price': order_price,
                    'current_price': current_price,
                    'distance_pct': round(price_diff_pct, 2),
                    'volume': order['volume'],
                    'time': price_info['time']
                })
        
        return alerts
    
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
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information"""
        if not self.connected:
            return None
        
        account_info = mt5.account_info()
        if not account_info:
            return None
        
        positions = mt5.positions_get()
        open_positions_count = len(positions) if positions else 0
        
        # Calculate total profit from open positions
        total_profit = sum(pos.profit for pos in positions) if positions else 0.0
        
        return {
            'login': account_info.login,
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'free_margin': account_info.margin_free,
            'margin_level': account_info.margin_level if account_info.margin > 0 else 0,
            'profit': total_profit,
            'open_positions': open_positions_count,
            'currency': account_info.currency,
            'server': account_info.server,
            'leverage': account_info.leverage
        }
    
    def get_all_positions(self) -> List[Dict]:
        """Get all open positions with detailed information"""
        if not self.connected:
            return []
        
        positions = mt5.positions_get()
        if not positions:
            return []
        
        result = []
        for pos in positions:
            result.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'swap': getattr(pos, 'swap', 0.0),
                'commission': getattr(pos, 'commission', 0.0),
                'time': datetime.fromtimestamp(pos.time).strftime('%Y-%m-%d %H:%M:%S'),
                'time_update': datetime.fromtimestamp(pos.time_update).strftime('%Y-%m-%d %H:%M:%S'),
                'sl': pos.sl if pos.sl > 0 else None,
                'tp': pos.tp if pos.tp > 0 else None
            })
        
        return result
    
    def get_all_orders(self) -> List[Dict]:
        """Get all pending orders"""
        if not self.connected:
            return []
        
        orders = mt5.orders_get()
        if not orders:
            return []
        
        order_type_map = {
            mt5.ORDER_TYPE_BUY_LIMIT: 'BUY LIMIT',
            mt5.ORDER_TYPE_SELL_LIMIT: 'SELL LIMIT',
            mt5.ORDER_TYPE_BUY_STOP: 'BUY STOP',
            mt5.ORDER_TYPE_SELL_STOP: 'SELL STOP',
            mt5.ORDER_TYPE_BUY_STOP_LIMIT: 'BUY STOP LIMIT',
            mt5.ORDER_TYPE_SELL_STOP_LIMIT: 'SELL STOP LIMIT'
        }
        
        result = []
        for order in orders:
            result.append({
                'ticket': order.ticket,
                'symbol': order.symbol,
                'type': order_type_map.get(order.type, 'UNKNOWN'),
                'volume': order.volume_initial,
                'volume_current': order.volume_current,
                'price_open': order.price_open,
                'price_current': order.price_current,
                'sl': order.sl,
                'tp': order.tp,
                'time_setup': datetime.fromtimestamp(order.time_setup).strftime('%Y-%m-%d %H:%M:%S'),
                'time_expiration': datetime.fromtimestamp(order.time_expiration).strftime('%Y-%m-%d %H:%M:%S') if order.time_expiration > 0 else None
            })
        
        return result
    
    def get_pl_summary(self, period: str = 'daily') -> Dict:
        """Get profit/loss summary for a period (daily, weekly, monthly)"""
        if not self.connected:
            return {}
        
        from datetime import timedelta
        import time
        
        now = datetime.now()
        
        if period == 'daily':
            start_time = datetime(now.year, now.month, now.day)
        elif period == 'weekly':
            # Start of week (Monday)
            days_since_monday = now.weekday()
            start_time = datetime(now.year, now.month, now.day) - timedelta(days=days_since_monday)
        elif period == 'monthly':
            start_time = datetime(now.year, now.month, 1)
        else:
            start_time = datetime(now.year, now.month, now.day)
        
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(datetime.now().timestamp())
        
        # Get deal history (returns tuple or None)
        deals = mt5.history_deals_get(start_timestamp, end_timestamp)
        
        if deals is None or len(deals) == 0:
            return {
                'period': period,
                'total_profit': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        total_profit = 0.0
        trades = {}
        winning_trades = 0
        losing_trades = 0
        largest_win = 0.0
        largest_loss = 0.0
        
        # Group deals by position ticket
        for deal in deals:
            if deal.entry == mt5.DEAL_ENTRY_OUT:  # Only count exit deals
                ticket = deal.position_id
                profit = deal.profit
                
                if ticket not in trades:
                    trades[ticket] = 0.0
                
                trades[ticket] += profit
                total_profit += profit
        
        # Analyze trades
        for ticket, profit in trades.items():
            if profit > 0:
                winning_trades += 1
                if profit > largest_win:
                    largest_win = profit
            elif profit < 0:
                losing_trades += 1
                if profit < largest_loss:
                    largest_loss = profit
        
        # Get current open positions profit
        positions = mt5.positions_get()
        open_profit = sum(pos.profit for pos in positions) if positions else 0.0
        
        return {
            'period': period,
            'total_profit': total_profit,
            'open_profit': open_profit,
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / len(trades) * 100) if trades else 0.0,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S')
        }

