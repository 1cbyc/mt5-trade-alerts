"""
ML-based profit-taking suggestion analyzer
Learns from user's trading behavior to provide personalized suggestions
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class MLProfitAnalyzer:
    """Machine learning-based profit analyzer that learns from trade history"""
    
    def __init__(self, trade_db, min_trades_for_learning: int = 10):
        """
        Initialize ML profit analyzer
        
        Args:
            trade_db: TradeHistoryDB instance
            min_trades_for_learning: Minimum number of trades needed to learn patterns
        """
        self.trade_db = trade_db
        self.min_trades_for_learning = min_trades_for_learning
        self.learned_patterns = {}
        self.last_analysis_time = None
    
    def learn_from_history(self, symbol: Optional[str] = None) -> Dict:
        """
        Learn patterns from trade history
        
        Args:
            symbol: Optional symbol to analyze (None = all symbols)
        
        Returns:
            Dictionary with learned patterns
        """
        # Get historical trades (last 90 days for learning)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        trades = self.trade_db.get_trades(
            start_date=start_date,
            end_date=end_date,
            symbol=symbol
        )
        
        if len(trades) < self.min_trades_for_learning:
            return {
                'learned': False,
                'reason': f'Insufficient trades ({len(trades)} < {self.min_trades_for_learning})',
                'trades_analyzed': len(trades)
            }
        
        # Analyze winning trades to learn exit patterns
        winning_trades = [t for t in trades if t.get('profit', 0) > 0]
        losing_trades = [t for t in trades if t.get('profit', 0) < 0]
        
        if len(winning_trades) < 3:
            return {
                'learned': False,
                'reason': f'Insufficient winning trades ({len(winning_trades)} < 3)',
                'trades_analyzed': len(trades)
            }
        
        patterns = self._analyze_patterns(winning_trades, losing_trades, trades)
        
        # Store patterns by symbol or globally
        key = symbol or 'global'
        self.learned_patterns[key] = {
            'patterns': patterns,
            'last_updated': datetime.now(),
            'trades_analyzed': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades)
        }
        
        self.last_analysis_time = datetime.now()
        
        return {
            'learned': True,
            'patterns': patterns,
            'trades_analyzed': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades)
        }
    
    def _analyze_patterns(self, winning_trades: List[Dict], 
                         losing_trades: List[Dict], 
                         all_trades: List[Dict]) -> Dict:
        """Analyze patterns from trade data"""
        patterns = {}
        
        # 1. Average profit at exit for winning trades
        winning_profits = [t.get('profit', 0) for t in winning_trades]
        patterns['avg_winning_profit'] = statistics.mean(winning_profits) if winning_profits else 0
        patterns['median_winning_profit'] = statistics.median(winning_profits) if winning_profits else 0
        
        # 2. Profit percentage patterns
        account_balance = 10000  # Default, will be adjusted if available
        profit_percentages = []
        for trade in winning_trades:
            profit = trade.get('profit', 0)
            if profit > 0:
                # Estimate profit percentage (simplified)
                profit_percentages.append(profit / account_balance * 100)
        
        patterns['avg_profit_percentage'] = statistics.mean(profit_percentages) if profit_percentages else 0
        patterns['median_profit_percentage'] = statistics.median(profit_percentages) if profit_percentages else 0
        
        # 3. Hold time patterns for winning trades
        hold_times = []
        for trade in winning_trades:
            time_open = trade.get('time_open')
            time_close = trade.get('time_close')
            if time_open and time_close:
                try:
                    if isinstance(time_open, str):
                        open_dt = datetime.fromisoformat(time_open.replace(' ', 'T'))
                    else:
                        open_dt = time_open
                    
                    if isinstance(time_close, str):
                        close_dt = datetime.fromisoformat(time_close.replace(' ', 'T'))
                    else:
                        close_dt = time_close
                    
                    hold_time = (close_dt - open_dt).total_seconds() / 3600  # Hours
                    if hold_time > 0:
                        hold_times.append(hold_time)
                except:
                    pass
        
        patterns['avg_hold_time_hours'] = statistics.mean(hold_times) if hold_times else 0
        patterns['median_hold_time_hours'] = statistics.median(hold_times) if hold_times else 0
        
        # 4. Profit target patterns (analyze price movements)
        profit_targets = []
        for trade in winning_trades:
            price_open = trade.get('price_open', 0)
            price_close = trade.get('price_close', 0)
            trade_type = trade.get('type', 'BUY')
            
            if price_open > 0 and price_close > 0:
                if trade_type == 'BUY':
                    price_move_pct = ((price_close - price_open) / price_open) * 100
                else:  # SELL
                    price_move_pct = ((price_open - price_close) / price_open) * 100
                
                if price_move_pct > 0:
                    profit_targets.append(price_move_pct)
        
        patterns['avg_profit_target_pct'] = statistics.mean(profit_targets) if profit_targets else 0
        patterns['median_profit_target_pct'] = statistics.median(profit_targets) if profit_targets else 0
        
        # 5. Optimal exit timing (when do you typically close winners?)
        # Analyze profit distribution at exit
        profit_ranges = defaultdict(int)
        for trade in winning_trades:
            profit = trade.get('profit', 0)
            if profit < 10:
                profit_ranges['0-10'] += 1
            elif profit < 25:
                profit_ranges['10-25'] += 1
            elif profit < 50:
                profit_ranges['25-50'] += 1
            elif profit < 100:
                profit_ranges['50-100'] += 1
            else:
                profit_ranges['100+'] += 1
        
        patterns['profit_distribution'] = dict(profit_ranges)
        
        # 6. Risk-reward patterns
        avg_loss = abs(statistics.mean([t.get('profit', 0) for t in losing_trades])) if losing_trades else 0
        avg_win = patterns['avg_winning_profit']
        patterns['risk_reward_ratio'] = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 7. Symbol-specific patterns
        symbol_patterns = defaultdict(lambda: {'wins': [], 'losses': []})
        for trade in all_trades:
            sym = trade.get('symbol', 'UNKNOWN')
            if trade.get('profit', 0) > 0:
                symbol_patterns[sym]['wins'].append(trade.get('profit', 0))
            else:
                symbol_patterns[sym]['losses'].append(abs(trade.get('profit', 0)))
        
        patterns['symbol_performance'] = {}
        for sym, data in symbol_patterns.items():
            if data['wins']:
                patterns['symbol_performance'][sym] = {
                    'avg_win': statistics.mean(data['wins']),
                    'win_count': len(data['wins']),
                    'loss_count': len(data['losses'])
                }
        
        return patterns
    
    def get_suggestion(self, position: Dict, symbol: Optional[str] = None) -> Optional[Dict]:
        """
        Get ML-based profit-taking suggestion for a position
        
        Args:
            position: Position dictionary with ticket, symbol, profit, etc.
            symbol: Optional symbol for symbol-specific learning
        
        Returns:
            Suggestion dictionary or None
        """
        # Check if we have learned patterns
        key = symbol or position.get('symbol') or 'global'
        
        if key not in self.learned_patterns:
            # Try to learn if we haven't yet
            self.learn_from_history(symbol=key)
        
        if key not in self.learned_patterns:
            return None
        
        patterns = self.learned_patterns[key]['patterns']
        
        current_profit = position.get('profit', 0)
        if current_profit <= 0:
            return None
        
        # Get position details
        price_open = position.get('price_open', 0)
        price_current = position.get('price_current', 0)
        position_type = position.get('type', 'BUY')
        volume = position.get('volume', 0)
        
        if price_open <= 0 or price_current <= 0:
            return None
        
        # Calculate current profit percentage
        if position_type == 'BUY':
            price_move_pct = ((price_current - price_open) / price_open) * 100
        else:  # SELL
            price_move_pct = ((price_open - price_current) / price_open) * 100
        
        # Compare with learned patterns
        avg_profit_target = patterns.get('avg_profit_target_pct', 0)
        median_profit_target = patterns.get('median_profit_target_pct', 0)
        
        # Determine suggestion based on learned behavior
        suggestion = {
            'ticket': position.get('ticket'),
            'symbol': position.get('symbol'),
            'type': position_type,
            'current_profit': current_profit,
            'current_profit_pct': price_move_pct,
            'learned_avg_target': avg_profit_target,
            'learned_median_target': median_profit_target,
            'confidence': 'low',
            'recommendation': 'hold',
            'volume_to_close': 0,
            'reason': ''
        }
        
        # Decision logic based on learned patterns
        if avg_profit_target > 0:
            # If current profit is close to or exceeds learned average
            if price_move_pct >= avg_profit_target * 0.8:
                suggestion['confidence'] = 'high'
                suggestion['recommendation'] = 'partial_close'
                # Suggest closing based on how much profit we've captured
                if price_move_pct >= avg_profit_target:
                    # At or above average target - suggest closing 50-70%
                    suggestion['volume_to_close'] = round(volume * 0.6, 2)
                    suggestion['reason'] = f'Profit ({price_move_pct:.2f}%) matches your average exit target ({avg_profit_target:.2f}%)'
                else:
                    # Approaching target - suggest closing 30-50%
                    suggestion['volume_to_close'] = round(volume * 0.4, 2)
                    suggestion['reason'] = f'Profit ({price_move_pct:.2f}%) approaching your average exit target ({avg_profit_target:.2f}%)'
            
            # If significantly above average, suggest larger close
            elif price_move_pct >= avg_profit_target * 1.5:
                suggestion['confidence'] = 'very_high'
                suggestion['recommendation'] = 'large_partial_close'
                suggestion['volume_to_close'] = round(volume * 0.75, 2)
                suggestion['reason'] = f'Profit ({price_move_pct:.2f}%) significantly exceeds your average target ({avg_profit_target:.2f}%) - consider securing profits'
        
        # Also check profit amount patterns
        avg_winning_profit = patterns.get('avg_winning_profit', 0)
        if avg_winning_profit > 0 and current_profit >= avg_winning_profit * 0.9:
            if suggestion['recommendation'] == 'hold':
                suggestion['confidence'] = 'medium'
                suggestion['recommendation'] = 'partial_close'
                suggestion['volume_to_close'] = round(volume * 0.5, 2)
                suggestion['reason'] = f'Profit amount ({current_profit:.2f}) matches your typical winning trade average ({avg_winning_profit:.2f})'
        
        return suggestion if suggestion['recommendation'] != 'hold' else None
    
    def get_insights(self, symbol: Optional[str] = None) -> Dict:
        """
        Get insights about trading patterns
        
        Args:
            symbol: Optional symbol to analyze
        
        Returns:
            Dictionary with insights
        """
        key = symbol or 'global'
        
        if key not in self.learned_patterns:
            return {
                'available': False,
                'message': 'No patterns learned yet. Need more trade history.'
            }
        
        patterns = self.learned_patterns[key]['patterns']
        meta = self.learned_patterns[key]
        
        insights = {
            'available': True,
            'trades_analyzed': meta['trades_analyzed'],
            'winning_trades': meta['winning_trades'],
            'losing_trades': meta['losing_trades'],
            'win_rate': (meta['winning_trades'] / meta['trades_analyzed'] * 100) if meta['trades_analyzed'] > 0 else 0,
            'avg_winning_profit': patterns.get('avg_winning_profit', 0),
            'avg_profit_target_pct': patterns.get('avg_profit_target_pct', 0),
            'avg_hold_time_hours': patterns.get('avg_hold_time_hours', 0),
            'risk_reward_ratio': patterns.get('risk_reward_ratio', 0),
            'profit_distribution': patterns.get('profit_distribution', {}),
            'last_updated': meta['last_updated'].isoformat() if isinstance(meta['last_updated'], datetime) else str(meta['last_updated'])
        }
        
        return insights
