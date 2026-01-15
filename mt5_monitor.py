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
        current_time = datetime.now()
        
        for level in levels:
            level_price = level.get('price')
            level_type = level.get('type', 'both')  # 'above', 'below', 'both'
            level_id = level.get('id', 'unknown')
            
            if level_price is None:
                continue
            
            # Check expiration date
            expiration = level.get('expiration')
            if expiration:
                try:
                    if isinstance(expiration, str):
                        exp_time = datetime.fromisoformat(expiration)
                    else:
                        exp_time = datetime.fromtimestamp(expiration)
                    if current_time > exp_time:
                        continue  # Level has expired, skip it
                except (ValueError, TypeError):
                    logger.warning(f"Invalid expiration format for level {level_id}")
            
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
                    'time': price_info['time'],
                    'recurring': level.get('recurring', False),  # Default to one-time
                    'group': level.get('group'),  # Group identifier
                    'description': level.get('description', '')
                })
        
        return triggered
    
    def detect_support_resistance(self, symbol: str, timeframe: int = mt5.TIMEFRAME_H1, 
                                  periods: int = 100, min_touches: int = 2, 
                                  tolerance_pct: float = 0.5) -> Dict[str, List[float]]:
        """
        Automatically detect support and resistance levels from historical price data
        
        Args:
            symbol: Symbol to analyze
            timeframe: MT5 timeframe (default: H1)
            periods: Number of periods to analyze (default: 100)
            min_touches: Minimum number of price touches to consider a level valid (default: 2)
            tolerance_pct: Percentage tolerance for level detection (default: 0.5%)
        
        Returns:
            Dictionary with 'support' and 'resistance' lists of price levels
        """
        if not self.connected:
            return {'support': [], 'resistance': []}
        
        # Get historical data
        rates = mt5.copy_rates_from(symbol, timeframe, 0, periods)
        if rates is None or len(rates) == 0:
            logger.warning(f"Could not retrieve historical data for {symbol}")
            return {'support': [], 'resistance': []}
        
        # Extract high, low, close prices
        highs = rates['high']
        lows = rates['low']
        closes = rates['close']
        
        # Find local maxima (resistance) and minima (support)
        resistance_levels = []
        support_levels = []
        
        # Use a simple approach: find pivot highs and lows
        for i in range(2, len(rates) - 2):
            # Check for resistance (local high)
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance_levels.append(float(highs[i]))
            
            # Check for support (local low)
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support_levels.append(float(lows[i]))
        
        # Group similar levels within tolerance
        def group_levels(levels: List[float], tolerance_pct: float) -> List[float]:
            if not levels:
                return []
            
            levels = sorted(levels)
            grouped = []
            current_group = [levels[0]]
            
            for level in levels[1:]:
                # Check if level is within tolerance of current group
                avg_group = sum(current_group) / len(current_group)
                tolerance = avg_group * (tolerance_pct / 100)
                
                if abs(level - avg_group) <= tolerance:
                    current_group.append(level)
                else:
                    # Finalize current group if it has enough touches
                    if len(current_group) >= min_touches:
                        grouped.append(sum(current_group) / len(current_group))
                    current_group = [level]
            
            # Add final group
            if len(current_group) >= min_touches:
                grouped.append(sum(current_group) / len(current_group))
            
            return grouped
        
        resistance = group_levels(resistance_levels, tolerance_pct)
        support = group_levels(support_levels, tolerance_pct)
        
        return {
            'support': sorted(support),
            'resistance': sorted(resistance, reverse=True)
        }
    
    def check_level_groups(self, symbol: str, levels: List[Dict], 
                          triggered_levels: List[str]) -> List[Dict]:
        """
        Check if multiple levels in a group have been triggered
        
        Args:
            symbol: Symbol being checked
            levels: List of price levels
            triggered_levels: List of level IDs that have been triggered
        
        Returns:
            List of group alerts if group conditions are met
        """
        # Group levels by their group identifier
        groups = {}
        for level in levels:
            group_id = level.get('group')
            if group_id:
                if group_id not in groups:
                    groups[group_id] = {
                        'levels': [],
                        'required_count': level.get('group_required_count', 2),  # Default: 2 levels
                        'description': level.get('group_description', f'Group {group_id}')
                    }
                groups[group_id]['levels'].append(level)
        
        group_alerts = []
        for group_id, group_info in groups.items():
            triggered_in_group = [
                level for level in group_info['levels'] 
                if level.get('id') in triggered_levels
            ]
            
            if len(triggered_in_group) >= group_info['required_count']:
                group_alerts.append({
                    'symbol': symbol,
                    'group_id': group_id,
                    'description': group_info['description'],
                    'triggered_count': len(triggered_in_group),
                    'required_count': group_info['required_count'],
                    'triggered_levels': [l.get('id') for l in triggered_in_group],
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        
        return group_alerts
    
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
                'best_trade': None,
                'worst_trade': None,
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        total_profit = 0.0
        trades = {}
        winning_trades = 0
        losing_trades = 0
        largest_win = 0.0
        largest_loss = 0.0
        best_trade = None
        worst_trade = None
        
        # Group deals by position ticket and collect detailed info
        for deal in deals:
            ticket = deal.position_id
            if ticket not in trades:
                trades[ticket] = {
                    'profit': 0.0,
                    'symbol': deal.symbol,
                    'volume': 0.0,
                    'entry_time': None,
                    'exit_time': None,
                    'entry_price': None,
                    'exit_price': None,
                    'commission': 0.0,
                    'swap': 0.0,
                    'type': None
                }
            
            if deal.entry == mt5.DEAL_ENTRY_IN:
                # Entry deal
                trades[ticket]['entry_time'] = datetime.fromtimestamp(deal.time)
                trades[ticket]['entry_price'] = deal.price
                trades[ticket]['volume'] = deal.volume
                trades[ticket]['type'] = 'BUY' if deal.type == mt5.DEAL_TYPE_BUY else 'SELL'
            elif deal.entry == mt5.DEAL_ENTRY_OUT:
                # Exit deal
                trades[ticket]['exit_time'] = datetime.fromtimestamp(deal.time)
                trades[ticket]['exit_price'] = deal.price
                trades[ticket]['profit'] += deal.profit
                trades[ticket]['commission'] += deal.commission
                trades[ticket]['swap'] += deal.swap
                total_profit += deal.profit
        
        # Analyze trades and find best/worst
        for ticket, trade_info in trades.items():
            profit = trade_info['profit']
            
            if profit > 0:
                winning_trades += 1
                if profit > largest_win:
                    largest_win = profit
                    best_trade = {
                        'ticket': ticket,
                        'symbol': trade_info['symbol'],
                        'type': trade_info['type'],
                        'profit': profit,
                        'volume': trade_info['volume'],
                        'entry_price': trade_info['entry_price'],
                        'exit_price': trade_info['exit_price'],
                        'entry_time': trade_info['entry_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_info['entry_time'] else None,
                        'exit_time': trade_info['exit_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_info['exit_time'] else None,
                        'duration': str(trade_info['exit_time'] - trade_info['entry_time']) if trade_info['entry_time'] and trade_info['exit_time'] else None,
                        'commission': trade_info['commission'],
                        'swap': trade_info['swap']
                    }
            elif profit < 0:
                losing_trades += 1
                if profit < largest_loss:
                    largest_loss = profit
                    worst_trade = {
                        'ticket': ticket,
                        'symbol': trade_info['symbol'],
                        'type': trade_info['type'],
                        'profit': profit,
                        'volume': trade_info['volume'],
                        'entry_price': trade_info['entry_price'],
                        'exit_price': trade_info['exit_price'],
                        'entry_time': trade_info['entry_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_info['entry_time'] else None,
                        'exit_time': trade_info['exit_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_info['exit_time'] else None,
                        'duration': str(trade_info['exit_time'] - trade_info['entry_time']) if trade_info['entry_time'] and trade_info['exit_time'] else None,
                        'commission': trade_info['commission'],
                        'swap': trade_info['swap']
                    }
        
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
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_trade_statistics(self, period: str = 'daily') -> Dict:
        """Get comprehensive trade statistics for a period"""
        if not self.connected:
            return {}
        
        from datetime import timedelta
        
        now = datetime.now()
        
        if period == 'daily':
            start_time = datetime(now.year, now.month, now.day)
        elif period == 'weekly':
            days_since_monday = now.weekday()
            start_time = datetime(now.year, now.month, now.day) - timedelta(days=days_since_monday)
        elif period == 'monthly':
            start_time = datetime(now.year, now.month, 1)
        else:
            start_time = datetime(now.year, now.month, now.day)
        
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(datetime.now().timestamp())
        
        deals = mt5.history_deals_get(start_timestamp, end_timestamp)
        
        if deals is None or len(deals) == 0:
            return {
                'period': period,
                'total_profit': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'break_even_trades': 0,
                'win_rate': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'profit_factor': 0.0,
                'best_trade': None,
                'worst_trade': None,
                'total_volume': 0.0,
                'total_commission': 0.0,
                'total_swap': 0.0,
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        trades = {}
        total_profit = 0.0
        total_commission = 0.0
        total_swap = 0.0
        total_volume = 0.0
        winning_profit = 0.0
        losing_profit = 0.0
        
        # Process deals
        for deal in deals:
            ticket = deal.position_id
            if ticket not in trades:
                trades[ticket] = {
                    'profit': 0.0,
                    'symbol': deal.symbol,
                    'volume': 0.0,
                    'entry_time': None,
                    'exit_time': None,
                    'entry_price': None,
                    'exit_price': None,
                    'commission': 0.0,
                    'swap': 0.0,
                    'type': None
                }
            
            if deal.entry == mt5.DEAL_ENTRY_IN:
                trades[ticket]['entry_time'] = datetime.fromtimestamp(deal.time)
                trades[ticket]['entry_price'] = deal.price
                trades[ticket]['volume'] = deal.volume
                trades[ticket]['type'] = 'BUY' if deal.type == mt5.DEAL_TYPE_BUY else 'SELL'
                total_volume += deal.volume
            elif deal.entry == mt5.DEAL_ENTRY_OUT:
                trades[ticket]['exit_time'] = datetime.fromtimestamp(deal.time)
                trades[ticket]['exit_price'] = deal.price
                trades[ticket]['profit'] += deal.profit
                trades[ticket]['commission'] += deal.commission
                trades[ticket]['swap'] += deal.swap
                total_profit += deal.profit
                total_commission += deal.commission
                total_swap += deal.swap
        
        # Analyze trades
        winning_trades = 0
        losing_trades = 0
        break_even_trades = 0
        best_trade = None
        worst_trade = None
        wins = []
        losses = []
        
        for ticket, trade_info in trades.items():
            profit = trade_info['profit']
            
            if profit > 0:
                winning_trades += 1
                winning_profit += profit
                wins.append(profit)
                
                if best_trade is None or profit > best_trade['profit']:
                    best_trade = {
                        'ticket': ticket,
                        'symbol': trade_info['symbol'],
                        'type': trade_info['type'],
                        'profit': profit,
                        'volume': trade_info['volume'],
                        'entry_price': trade_info['entry_price'],
                        'exit_price': trade_info['exit_price'],
                        'entry_time': trade_info['entry_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_info['entry_time'] else None,
                        'exit_time': trade_info['exit_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_info['exit_time'] else None,
                        'duration': str(trade_info['exit_time'] - trade_info['entry_time']) if trade_info['entry_time'] and trade_info['exit_time'] else None,
                        'commission': trade_info['commission'],
                        'swap': trade_info['swap']
                    }
            elif profit < 0:
                losing_trades += 1
                losing_profit += abs(profit)
                losses.append(profit)
                
                if worst_trade is None or profit < worst_trade['profit']:
                    worst_trade = {
                        'ticket': ticket,
                        'symbol': trade_info['symbol'],
                        'type': trade_info['type'],
                        'profit': profit,
                        'volume': trade_info['volume'],
                        'entry_price': trade_info['entry_price'],
                        'exit_price': trade_info['exit_price'],
                        'entry_time': trade_info['entry_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_info['entry_time'] else None,
                        'exit_time': trade_info['exit_time'].strftime('%Y-%m-%d %H:%M:%S') if trade_info['exit_time'] else None,
                        'duration': str(trade_info['exit_time'] - trade_info['entry_time']) if trade_info['entry_time'] and trade_info['exit_time'] else None,
                        'commission': trade_info['commission'],
                        'swap': trade_info['swap']
                    }
            else:
                break_even_trades += 1
        
        # Calculate statistics
        win_rate = (winning_trades / len(trades) * 100) if trades else 0.0
        average_win = (winning_profit / winning_trades) if winning_trades > 0 else 0.0
        average_loss = (losing_profit / losing_trades) if losing_trades > 0 else 0.0
        profit_factor = (winning_profit / losing_profit) if losing_profit > 0 else (winning_profit if winning_profit > 0 else 0.0)
        
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
            'break_even_trades': break_even_trades,
            'win_rate': win_rate,
            'average_win': average_win,
            'average_loss': average_loss,
            'profit_factor': profit_factor,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'total_volume': total_volume,
            'total_commission': total_commission,
            'total_swap': total_swap,
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def check_margin_level(self, warning_threshold: float, critical_threshold: float) -> Optional[Dict]:
        """Check margin level and return alert if below thresholds"""
        if not self.connected:
            return None
        
        account_info = mt5.account_info()
        if not account_info:
            return None
        
        margin_level = account_info.margin_level if account_info.margin > 0 else 0
        
        if margin_level <= critical_threshold:
            return {
                'type': 'critical',
                'margin_level': margin_level,
                'threshold': critical_threshold,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free
            }
        elif margin_level <= warning_threshold:
            return {
                'type': 'warning',
                'margin_level': margin_level,
                'threshold': warning_threshold,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free
            }
        
        return None
    
    def check_position_sizes(self, max_size_pct: float) -> List[Dict]:
        """Check if any positions exceed maximum size percentage of account"""
        if not self.connected:
            return []
        
        account_info = mt5.account_info()
        if not account_info:
            return []
        
        balance = account_info.balance
        if balance <= 0:
            return []
        
        positions = mt5.positions_get()
        if not positions:
            return []
        
        alerts = []
        # Use margin per position from account (more efficient than calculating)
        # Total margin / number of positions gives approximate margin per position
        # But MT5 doesn't expose per-position margin directly, so we use volume as proxy
        # Position size % can be approximated by volume * price_open relative to balance
        
        for pos in positions:
            # Simplified calculation using volume and price as proxy
            # This is faster and avoids symbol_info lookup for each position
            position_value_approx = pos.volume * pos.price_open
            
            # Rough estimate: for most instruments, this gives a reasonable approximation
            # For precise calculation, we'd need symbol_info but that's slow
            # Using equity instead of balance for more accurate representation
            equity = account_info.equity if account_info.equity > 0 else balance
            position_size_pct = (position_value_approx / equity * 100) if equity > 0 else 0
            
            # More conservative check - if approximate exceeds limit, flag it
            if position_size_pct > max_size_pct:
                # Only do expensive symbol_info lookup if we're close to the limit
                symbol_info = mt5.symbol_info(pos.symbol)
                if symbol_info:
                    contract_size = getattr(symbol_info, 'trade_contract_size', 1)
                    leverage = account_info.leverage
                    position_value = pos.volume * pos.price_open * contract_size
                    margin_used = position_value / leverage if leverage > 0 else position_value
                    position_size_pct = (margin_used / balance * 100) if balance > 0 else 0
                    
                    if position_size_pct > max_size_pct:
                        alerts.append({
                            'symbol': pos.symbol,
                            'ticket': pos.ticket,
                            'volume': pos.volume,
                            'position_size_pct': round(position_size_pct, 2),
                            'max_size_pct': max_size_pct,
                            'margin_used': margin_used,
                            'balance': balance
                        })
        
        return alerts
    
    def check_daily_loss_limit(self, loss_limit_pct: float, loss_limit_amount: float) -> Optional[Dict]:
        """Check if daily loss exceeds limits - optimized to avoid expensive queries when possible"""
        if not self.connected:
            return None
        
        account_info = mt5.account_info()
        if not account_info:
            return None
        
        # Fast path: Check open positions profit first (no history query needed)
        positions = mt5.positions_get()
        open_profit = sum(pos.profit for pos in positions) if positions else 0.0
        balance = account_info.balance
        
        # Quick check: If open profit is positive and well above any loss threshold, skip expensive query
        if open_profit > 0:
            # Still need to check closed trades, but only if open profit suggests we might be at limit
            estimated_threshold = balance * loss_limit_pct / 100 if loss_limit_pct > 0 else loss_limit_amount
            if open_profit > estimated_threshold:
                # Open profit is positive and large, likely no loss limit breached
                return None
        
        # Need to check closed trades (slower query) - only when necessary
        summary = self.get_pl_summary(period='daily')
        total_profit = summary.get('total_profit', 0) if summary else 0
        total_pl = total_profit + open_profit
        
        # Check if we have a loss
        if total_pl >= 0:
            return None
        
        daily_loss = abs(total_pl)
        loss_pct = (daily_loss / balance * 100) if balance > 0 else 0
        
        alert = None
        
        # Check percentage limit
        if loss_limit_pct > 0 and loss_pct >= loss_limit_pct:
            alert = {
                'type': 'daily_loss_pct',
                'daily_loss': daily_loss,
                'loss_pct': round(loss_pct, 2),
                'limit_pct': loss_limit_pct,
                'balance': balance,
                'closed_profit': total_profit,
                'open_profit': open_profit
            }
        
        # Check amount limit (takes precedence if both are set)
        if loss_limit_amount > 0 and daily_loss >= loss_limit_amount:
            alert = {
                'type': 'daily_loss_amount',
                'daily_loss': daily_loss,
                'loss_limit': loss_limit_amount,
                'balance': balance,
                'closed_profit': total_profit,
                'open_profit': open_profit
            }
        
        return alert
    
    def check_drawdown(self, drawdown_limit_pct: float, initial_balance: float = None) -> Optional[Dict]:
        """Check if current drawdown exceeds limit from initial balance"""
        if not self.connected:
            return None
        
        account_info = mt5.account_info()
        if not account_info:
            return None
        
        current_balance = account_info.balance
        equity = account_info.equity
        
        # Use provided initial balance or current balance if not provided
        if initial_balance is None:
            initial_balance = current_balance
        
        if initial_balance <= 0:
            return None
        
        # Calculate drawdown from equity (worst case)
        drawdown_amount = initial_balance - equity
        drawdown_pct = (drawdown_amount / initial_balance * 100) if initial_balance > 0 else 0
        
        if drawdown_pct >= drawdown_limit_pct:
            return {
                'drawdown_pct': round(drawdown_pct, 2),
                'drawdown_amount': drawdown_amount,
                'limit_pct': drawdown_limit_pct,
                'initial_balance': initial_balance,
                'current_balance': current_balance,
                'equity': equity,
                'profit': equity - initial_balance
            }
        
        return None

