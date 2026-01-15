"""
Volatility calculator for position sizing suggestions
"""
import MetaTrader5 as mt5
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class VolatilityCalculator:
    """Calculate volatility metrics and suggest position sizes"""
    
    def __init__(self, periods: int = 20):
        """
        Initialize volatility calculator
        
        Args:
            periods: Number of periods to use for volatility calculation
        """
        self.periods = periods
        self.cache = {}  # Cache volatility calculations
        self.cache_ttl = timedelta(minutes=5)  # Cache TTL
    
    def calculate_atr(self, symbol: str, timeframe: int = mt5.TIMEFRAME_H1, 
                     periods: int = 14) -> Optional[float]:
        """
        Calculate Average True Range (ATR) for a symbol
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe
            periods: Number of periods for ATR calculation
        
        Returns:
            ATR value or None
        """
        try:
            rates = mt5.copy_rates_from(symbol, timeframe, datetime.now(), periods + 1)
            if rates is None or len(rates) < periods + 1:
                return None
            
            true_ranges = []
            for i in range(1, len(rates)):
                high = rates[i]['high']
                low = rates[i]['low']
                prev_close = rates[i-1]['close']
                
                tr1 = high - low
                tr2 = abs(high - prev_close)
                tr3 = abs(low - prev_close)
                
                true_range = max(tr1, tr2, tr3)
                true_ranges.append(true_range)
            
            if true_ranges:
                atr = statistics.mean(true_ranges)
                return atr
            
            return None
        except Exception as e:
            logger.error(f"Error calculating ATR for {symbol}: {e}")
            return None
    
    def calculate_volatility(self, symbol: str, timeframe: int = mt5.TIMEFRAME_H1,
                            periods: int = None) -> Optional[Dict]:
        """
        Calculate volatility metrics for a symbol
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe
            periods: Number of periods (defaults to self.periods)
        
        Returns:
            Dictionary with volatility metrics
        """
        if periods is None:
            periods = self.periods
        
        # Check cache
        cache_key = f"{symbol}_{timeframe}_{periods}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data
        
        try:
            # Get historical rates
            rates = mt5.copy_rates_from(symbol, timeframe, datetime.now(), periods + 1)
            if rates is None or len(rates) < periods:
                return None
            
            # Calculate price changes
            price_changes = []
            price_changes_pct = []
            
            for i in range(1, len(rates)):
                change = rates[i]['close'] - rates[i-1]['close']
                change_pct = (change / rates[i-1]['close']) * 100
                price_changes.append(change)
                price_changes_pct.append(change_pct)
            
            if not price_changes:
                return None
            
            # Calculate metrics
            current_price = rates[-1]['close']
            volatility_std = statistics.stdev(price_changes_pct) if len(price_changes_pct) > 1 else 0
            volatility_mean = abs(statistics.mean(price_changes_pct))
            max_move = max([abs(c) for c in price_changes_pct])
            avg_move = statistics.mean([abs(c) for c in price_changes_pct])
            
            # Calculate ATR
            atr = self.calculate_atr(symbol, timeframe, 14)
            atr_pct = (atr / current_price * 100) if atr and current_price > 0 else 0
            
            # Determine volatility level
            if volatility_std < 0.5:
                volatility_level = 'low'
            elif volatility_std < 1.5:
                volatility_level = 'medium'
            elif volatility_std < 3.0:
                volatility_level = 'high'
            else:
                volatility_level = 'very_high'
            
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'volatility_std': volatility_std,
                'volatility_mean': volatility_mean,
                'max_move_pct': max_move,
                'avg_move_pct': avg_move,
                'atr': atr,
                'atr_pct': atr_pct,
                'volatility_level': volatility_level,
                'periods_analyzed': len(price_changes),
                'timeframe': timeframe,
                'timestamp': datetime.now()
            }
            
            # Cache result
            self.cache[cache_key] = (result, datetime.now())
            
            return result
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return None
    
    def suggest_position_size(self, symbol: str, account_balance: float,
                            risk_per_trade_pct: float = 2.0,
                            stop_loss_pips: float = 50.0) -> Optional[Dict]:
        """
        Suggest position size based on volatility
        
        Args:
            symbol: Trading symbol
            account_balance: Account balance
            risk_per_trade_pct: Risk percentage per trade (default 2%)
            stop_loss_pips: Stop loss in pips
        
        Returns:
            Dictionary with position size suggestion
        """
        # Get volatility metrics
        volatility = self.calculate_volatility(symbol)
        if not volatility:
            return None
        
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return None
        
        # Calculate risk amount
        risk_amount = account_balance * (risk_per_trade_pct / 100)
        
        # Get pip value
        point = symbol_info.point
        pip_value = point * 10 if symbol_info.digits == 5 or symbol_info.digits == 3 else point
        
        # Calculate position size based on stop loss
        # Risk = Position Size * Stop Loss Pips * Pip Value
        # Position Size = Risk / (Stop Loss Pips * Pip Value)
        
        if stop_loss_pips * pip_value > 0:
            base_position_size = risk_amount / (stop_loss_pips * pip_value)
        else:
            return None
        
        # Adjust based on volatility
        volatility_std = volatility['volatility_std']
        atr_pct = volatility['atr_pct']
        
        # Volatility adjustment factor
        # Higher volatility = smaller position size
        if volatility['volatility_level'] == 'very_high':
            adjustment_factor = 0.5  # Reduce position by 50%
        elif volatility['volatility_level'] == 'high':
            adjustment_factor = 0.7  # Reduce position by 30%
        elif volatility['volatility_level'] == 'medium':
            adjustment_factor = 1.0  # No adjustment
        else:  # low
            adjustment_factor = 1.2  # Can increase slightly
        
        # Apply adjustment
        suggested_size = base_position_size * adjustment_factor
        
        # Round to symbol's volume step
        volume_step = getattr(symbol_info, 'volume_step', 0.01)
        if volume_step > 0:
            suggested_size = round(suggested_size / volume_step) * volume_step
        
        # Ensure minimum and maximum constraints
        min_volume = getattr(symbol_info, 'volume_min', 0.01)
        max_volume = getattr(symbol_info, 'volume_max', 100.0)
        
        suggested_size = max(min_volume, min(suggested_size, max_volume))
        
        # Calculate actual risk with suggested size
        actual_risk = suggested_size * stop_loss_pips * pip_value
        actual_risk_pct = (actual_risk / account_balance * 100) if account_balance > 0 else 0
        
        return {
            'symbol': symbol,
            'suggested_volume': round(suggested_size, 2),
            'base_volume': round(base_position_size, 2),
            'adjustment_factor': adjustment_factor,
            'volatility_level': volatility['volatility_level'],
            'volatility_std': volatility_std,
            'atr_pct': atr_pct,
            'risk_amount': round(risk_amount, 2),
            'actual_risk': round(actual_risk, 2),
            'actual_risk_pct': round(actual_risk_pct, 2),
            'stop_loss_pips': stop_loss_pips,
            'account_balance': account_balance,
            'reason': f"Volatility: {volatility['volatility_level']} ({volatility_std:.2f}% std dev)"
        }
    
    def get_volatility_alert(self, symbol: str, current_volume: float,
                           account_balance: float) -> Optional[Dict]:
        """
        Check if current position size is appropriate for volatility
        
        Args:
            symbol: Trading symbol
            current_volume: Current position volume
            account_balance: Account balance
        
        Returns:
            Alert dictionary if position size needs adjustment, None otherwise
        """
        suggestion = self.suggest_position_size(symbol, account_balance)
        if not suggestion:
            return None
        
        suggested_volume = suggestion['suggested_volume']
        current_volume = float(current_volume)
        
        # Check if current volume differs significantly from suggestion
        if suggested_volume > 0:
            ratio = current_volume / suggested_volume
            
            # Alert if position is 30% larger or smaller than suggested
            if ratio > 1.3:
                return {
                    'type': 'position_too_large',
                    'symbol': symbol,
                    'current_volume': current_volume,
                    'suggested_volume': suggested_volume,
                    'ratio': ratio,
                    'volatility_level': suggestion['volatility_level'],
                    'message': f'Position size ({current_volume}) is {ratio:.1f}x larger than volatility-based suggestion ({suggested_volume})',
                    'recommendation': 'Consider reducing position size due to high volatility'
                }
            elif ratio < 0.7:
                return {
                    'type': 'position_too_small',
                    'symbol': symbol,
                    'current_volume': current_volume,
                    'suggested_volume': suggested_volume,
                    'ratio': ratio,
                    'volatility_level': suggestion['volatility_level'],
                    'message': f'Position size ({current_volume}) is smaller than volatility-based suggestion ({suggested_volume})',
                    'recommendation': 'Could increase position size as volatility is manageable'
                }
        
        return None
