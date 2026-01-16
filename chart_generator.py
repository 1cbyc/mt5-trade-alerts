"""
Chart generation module for trade performance visualization
"""
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import io
import os

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generate performance charts for trades"""
    
    def __init__(self):
        plt.style.use('dark_background')  # Use dark theme for better visibility
    
    def generate_equity_curve(self, trades: List[Dict], output_path: Optional[str] = None) -> Optional[bytes]:
        """
        Generate equity curve chart from trades
        
        Args:
            trades: List of trade dictionaries
            output_path: Optional path to save image (if None, returns bytes)
        
        Returns:
            Image bytes if output_path is None, otherwise None
        """
        if not trades:
            return None
        
        try:
            # Sort trades by close time
            sorted_trades = sorted(
                [t for t in trades if t.get('time_close')],
                key=lambda x: datetime.fromisoformat(x['time_close']) if isinstance(x['time_close'], str) else x['time_close']
            )
            
            if not sorted_trades:
                return None
            
            # Calculate cumulative equity
            cumulative_profit = 0.0
            equity_data = []
            dates = []
            
            for trade in sorted_trades:
                profit = trade.get('profit', 0)
                cumulative_profit += profit
                equity_data.append(cumulative_profit)
                
                time_close = trade.get('time_close')
                if isinstance(time_close, str):
                    dates.append(datetime.fromisoformat(time_close))
                else:
                    dates.append(time_close)
            
            # Create chart
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(dates, equity_data, linewidth=2, color='#00ff88')
            ax.axhline(y=0, color='white', linestyle='--', alpha=0.5)
            ax.fill_between(dates, 0, equity_data, where=[x >= 0 for x in equity_data], 
                           alpha=0.3, color='green', label='Profit')
            ax.fill_between(dates, 0, equity_data, where=[x < 0 for x in equity_data], 
                           alpha=0.3, color='red', label='Loss')
            
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Cumulative Profit', fontsize=12)
            ax.set_title('Equity Curve', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            if output_path:
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()
                return None
            else:
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                buf.seek(0)
                plt.close()
                return buf.getvalue()
        except Exception as e:
            logger.error(f"Error generating equity curve: {e}")
            plt.close()
            return None
    
    def generate_daily_pnl_chart(self, trades: List[Dict], output_path: Optional[str] = None) -> Optional[bytes]:
        """
        Generate daily P/L chart
        
        Args:
            trades: List of trade dictionaries
            output_path: Optional path to save image
        
        Returns:
            Image bytes if output_path is None, otherwise None
        """
        if not trades:
            return None
        
        try:
            # Group trades by day
            daily_pnl = {}
            
            for trade in trades:
                if not trade.get('time_close'):
                    continue
                
                time_close = trade.get('time_close')
                if isinstance(time_close, str):
                    date = datetime.fromisoformat(time_close).date()
                else:
                    date = time_close.date() if hasattr(time_close, 'date') else datetime.fromtimestamp(time_close).date()
                
                if date not in daily_pnl:
                    daily_pnl[date] = 0.0
                
                daily_pnl[date] += trade.get('profit', 0)
            
            if not daily_pnl:
                return None
            
            # Sort by date
            sorted_dates = sorted(daily_pnl.keys())
            dates = [datetime.combine(d, datetime.min.time()) for d in sorted_dates]
            pnl_values = [daily_pnl[d] for d in sorted_dates]
            
            # Create chart
            fig, ax = plt.subplots(figsize=(12, 6))
            colors = ['green' if p >= 0 else 'red' for p in pnl_values]
            ax.bar(dates, pnl_values, color=colors, alpha=0.7, width=0.8)
            ax.axhline(y=0, color='white', linestyle='-', linewidth=1)
            
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Daily P/L', fontsize=12)
            ax.set_title('Daily Profit/Loss', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            if output_path:
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()
                return None
            else:
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                buf.seek(0)
                plt.close()
                return buf.getvalue()
        except Exception as e:
            logger.error(f"Error generating daily P/L chart: {e}")
            plt.close()
            return None
    
    def generate_win_loss_distribution(self, trades: List[Dict], output_path: Optional[str] = None) -> Optional[bytes]:
        """
        Generate win/loss distribution chart
        
        Args:
            trades: List of trade dictionaries
            output_path: Optional path to save image
        
        Returns:
            Image bytes if output_path is None, otherwise None
        """
        if not trades:
            return None
        
        try:
            wins = [t.get('profit', 0) for t in trades if t.get('profit', 0) > 0]
            losses = [abs(t.get('profit', 0)) for t in trades if t.get('profit', 0) < 0]
            
            if not wins and not losses:
                return None
            
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            # Win distribution
            if wins:
                ax1.hist(wins, bins=20, color='green', alpha=0.7, edgecolor='white')
                ax1.set_xlabel('Profit', fontsize=12)
                ax1.set_ylabel('Frequency', fontsize=12)
                ax1.set_title('Win Distribution', fontsize=12, fontweight='bold')
                ax1.grid(True, alpha=0.3)
            
            # Loss distribution
            if losses:
                ax2.hist(losses, bins=20, color='red', alpha=0.7, edgecolor='white')
                ax2.set_xlabel('Loss', fontsize=12)
                ax2.set_ylabel('Frequency', fontsize=12)
                ax2.set_title('Loss Distribution', fontsize=12, fontweight='bold')
                ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if output_path:
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()
                return None
            else:
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                buf.seek(0)
                plt.close()
                return buf.getvalue()
        except Exception as e:
            logger.error(f"Error generating win/loss distribution: {e}")
            plt.close()
            return None
    
    def generate_performance_summary_chart(self, trades: List[Dict], output_path: Optional[str] = None) -> Optional[bytes]:
        """
        Generate comprehensive performance summary chart
        
        Args:
            trades: List of trade dictionaries
            output_path: Optional path to save image
        
        Returns:
            Image bytes if output_path is None, otherwise None
        """
        if not trades:
            return None
        
        try:
            fig = plt.figure(figsize=(16, 10))
            gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
            
            # 1. Equity Curve (top left)
            ax1 = fig.add_subplot(gs[0, 0])
            sorted_trades = sorted(
                [t for t in trades if t.get('time_close')],
                key=lambda x: datetime.fromisoformat(x['time_close']) if isinstance(x['time_close'], str) else x['time_close']
            )
            if sorted_trades:
                cumulative = 0.0
                equity = []
                dates = []
                for trade in sorted_trades:
                    cumulative += trade.get('profit', 0)
                    equity.append(cumulative)
                    time_close = trade.get('time_close')
                    if isinstance(time_close, str):
                        dates.append(datetime.fromisoformat(time_close))
                    else:
                        dates.append(time_close)
                ax1.plot(dates, equity, linewidth=2, color='#00ff88')
                ax1.axhline(y=0, color='white', linestyle='--', alpha=0.5)
                ax1.set_title('Equity Curve', fontweight='bold')
                ax1.set_ylabel('Cumulative Profit')
                ax1.grid(True, alpha=0.3)
                ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
            
            # 2. Daily P/L (top right)
            ax2 = fig.add_subplot(gs[0, 1])
            daily_pnl = {}
            for trade in trades:
                if not trade.get('time_close'):
                    continue
                time_close = trade.get('time_close')
                if isinstance(time_close, str):
                    date = datetime.fromisoformat(time_close).date()
                else:
                    date = time_close.date() if hasattr(time_close, 'date') else datetime.fromtimestamp(time_close).date()
                if date not in daily_pnl:
                    daily_pnl[date] = 0.0
                daily_pnl[date] += trade.get('profit', 0)
            if daily_pnl:
                sorted_dates = sorted(daily_pnl.keys())
                dates = [datetime.combine(d, datetime.min.time()) for d in sorted_dates]
                pnl_values = [daily_pnl[d] for d in sorted_dates]
                colors = ['green' if p >= 0 else 'red' for p in pnl_values]
                ax2.bar(dates, pnl_values, color=colors, alpha=0.7)
                ax2.axhline(y=0, color='white', linestyle='-', linewidth=1)
                ax2.set_title('Daily P/L', fontweight='bold')
                ax2.set_ylabel('Profit/Loss')
                ax2.grid(True, alpha=0.3, axis='y')
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
            
            # 3. Win/Loss Pie Chart (bottom left)
            ax3 = fig.add_subplot(gs[1, 0])
            wins = len([t for t in trades if t.get('profit', 0) > 0])
            losses = len([t for t in trades if t.get('profit', 0) < 0])
            break_even = len([t for t in trades if t.get('profit', 0) == 0])
            if wins + losses + break_even > 0:
                sizes = [wins, losses, break_even]
                labels = [f'Wins ({wins})', f'Losses ({losses})', f'Break-even ({break_even})']
                colors_pie = ['green', 'red', 'gray']
                ax3.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%', startangle=90)
                ax3.set_title('Win/Loss Ratio', fontweight='bold')
            
            # 4. Monthly P/L (bottom right)
            ax4 = fig.add_subplot(gs[1, 1])
            monthly_pnl = {}
            for trade in trades:
                if not trade.get('time_close'):
                    continue
                time_close = trade.get('time_close')
                if isinstance(time_close, str):
                    dt = datetime.fromisoformat(time_close)
                else:
                    dt = time_close if hasattr(time_close, 'year') else datetime.fromtimestamp(time_close)
                month_key = f"{dt.year}-{dt.month:02d}"
                if month_key not in monthly_pnl:
                    monthly_pnl[month_key] = 0.0
                monthly_pnl[month_key] += trade.get('profit', 0)
            if monthly_pnl:
                sorted_months = sorted(monthly_pnl.keys())
                months = sorted_months
                pnl_values = [monthly_pnl[m] for m in months]
                colors = ['green' if p >= 0 else 'red' for p in pnl_values]
                ax4.bar(months, pnl_values, color=colors, alpha=0.7)
                ax4.axhline(y=0, color='white', linestyle='-', linewidth=1)
                ax4.set_title('Monthly P/L', fontweight='bold')
                ax4.set_ylabel('Profit/Loss')
                ax4.set_xlabel('Month')
                ax4.grid(True, alpha=0.3, axis='y')
                plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)
            
            plt.suptitle('Performance Summary', fontsize=16, fontweight='bold', y=0.98)
            
            if output_path:
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()
                return None
            else:
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                buf.seek(0)
                plt.close()
                return buf.getvalue()
        except Exception as e:
            logger.error(f"Error generating performance summary chart: {e}")
            plt.close()
            return None
    
    def generate_price_chart(
        self,
        symbol: str,
        timeframe: int = 16385,  # MT5 TIMEFRAME_H1
        periods: int = 50,
        highlight_price: Optional[float] = None,
        highlight_label: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Generate a price chart for a symbol (for alerts)
        
        Args:
            symbol: Symbol to chart
            timeframe: MT5 timeframe
            periods: Number of periods to show
            highlight_price: Optional price level to highlight
            highlight_label: Optional label for highlighted price
        
        Returns:
            Image bytes
        """
        try:
            import MetaTrader5 as mt5
            
            # Get historical data
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, periods)
            if rates is None or len(rates) == 0:
                logger.warning(f"No data available for {symbol}")
                return None
            
            # Convert to DataFrame-like structure
            import numpy as np
            times = [datetime.fromtimestamp(r[0]) for r in rates]
            opens = [r[1] for r in rates]
            highs = [r[2] for r in rates]
            lows = [r[3] for r in rates]
            closes = [r[4] for r in rates]
            volumes = [r[5] for r in rates]
            
            # Create chart
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot candlesticks (simplified as line chart)
            ax.plot(times, closes, linewidth=2, color='#00ff88', label='Close Price')
            ax.fill_between(times, lows, highs, alpha=0.2, color='gray', label='High/Low Range')
            
            # Highlight price level if provided
            if highlight_price is not None:
                ax.axhline(
                    y=highlight_price,
                    color='yellow',
                    linestyle='--',
                    linewidth=2,
                    label=highlight_label or f'Level: {highlight_price}'
                )
            
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel('Price', fontsize=12)
            ax.set_title(f'{symbol} Price Chart', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Return as bytes
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            return buf.getvalue()
        except Exception as e:
            logger.error(f"Error generating price chart for {symbol}: {e}")
            plt.close()
            return None
