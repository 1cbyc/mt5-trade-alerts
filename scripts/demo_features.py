"""
Demo script to show how the historical data & analytics features work
"""
import os
import sys
import io
from datetime import datetime, timedelta
from src.analytics.trade_history import TradeHistoryDB
from src.analytics.chart_generator import ChartGenerator

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def demo_trade_history():
    """Demonstrate trade history database"""
    print("\n" + "="*60)
    print("📊 TRADE HISTORY DATABASE DEMO")
    print("="*60)
    
    # Initialize database
    db = TradeHistoryDB(db_path='demo_trade_history.db')
    
    # Add some sample trades
    print("\n1. Adding sample trades to database...")
    sample_trades = [
        {
            'ticket': 100001,
            'symbol': 'EURUSD',
            'type': 'BUY',
            'volume': 0.1,
            'price_open': 1.1000,
            'price_close': 1.1020,
            'profit': 20.0,
            'commission': -0.5,
            'swap': 0.1,
            'time_open': (datetime.now() - timedelta(days=5)).isoformat(),
            'time_close': (datetime.now() - timedelta(days=5) + timedelta(hours=2)).isoformat(),
            'duration_seconds': 7200,
            'sl': 1.0980,
            'tp': 1.1050
        },
        {
            'ticket': 100002,
            'symbol': 'EURUSD',
            'type': 'SELL',
            'volume': 0.1,
            'price_open': 1.1020,
            'price_close': 1.1005,
            'profit': 15.0,
            'commission': -0.5,
            'swap': -0.1,
            'time_open': (datetime.now() - timedelta(days=4)).isoformat(),
            'time_close': (datetime.now() - timedelta(days=4) + timedelta(hours=1)).isoformat(),
            'duration_seconds': 3600,
            'sl': 1.1040,
            'tp': 1.0990
        },
        {
            'ticket': 100003,
            'symbol': 'GBPUSD',
            'type': 'BUY',
            'volume': 0.2,
            'price_open': 1.2500,
            'price_close': 1.2480,
            'profit': -40.0,
            'commission': -1.0,
            'swap': 0.2,
            'time_open': (datetime.now() - timedelta(days=3)).isoformat(),
            'time_close': (datetime.now() - timedelta(days=3) + timedelta(hours=3)).isoformat(),
            'duration_seconds': 10800,
            'sl': 1.2450,
            'tp': 1.2550
        },
        {
            'ticket': 100004,
            'symbol': 'EURUSD',
            'type': 'BUY',
            'volume': 0.15,
            'price_open': 1.1010,
            'price_close': 1.1035,
            'profit': 37.5,
            'commission': -0.75,
            'swap': 0.15,
            'time_open': (datetime.now() - timedelta(days=2)).isoformat(),
            'time_close': (datetime.now() - timedelta(days=2) + timedelta(hours=4)).isoformat(),
            'duration_seconds': 14400,
            'sl': 1.0990,
            'tp': 1.1060
        },
        {
            'ticket': 100005,
            'symbol': 'GBPUSD',
            'type': 'SELL',
            'volume': 0.1,
            'price_open': 1.2490,
            'price_close': 1.2510,
            'profit': -20.0,
            'commission': -0.5,
            'swap': -0.1,
            'time_open': (datetime.now() - timedelta(days=1)).isoformat(),
            'time_close': (datetime.now() - timedelta(days=1) + timedelta(hours=2)).isoformat(),
            'duration_seconds': 7200,
            'sl': 1.2520,
            'tp': 1.2460
        }
    ]
    
    for trade in sample_trades:
        db.add_trade(trade)
        print(f"   ✓ Added trade {trade['ticket']}: {trade['symbol']} {trade['type']} - P/L: {trade['profit']:.2f}")
    
    # Add a note to one trade
    print("\n2. Adding note to trade 100001...")
    db.add_trade_note(100001, "Good entry, followed trend perfectly")
    print("   ✓ Note added")
    
    # Get trade statistics
    print("\n3. Trade Statistics (Last 7 days):")
    stats = db.get_trade_statistics(
        start_date=datetime.now() - timedelta(days=7)
    )
    print(f"   Total Trades: {stats['total_trades']}")
    print(f"   Winning Trades: {stats['winning_trades']}")
    print(f"   Losing Trades: {stats['losing_trades']}")
    print(f"   Win Rate: {stats['win_rate']:.1f}%")
    print(f"   Total Profit: {stats['total_profit']:.2f}")
    print(f"   Average Win: {stats['average_win']:.2f}")
    print(f"   Average Loss: {stats['average_loss']:.2f}")
    print(f"   Profit Factor: {stats['profit_factor']:.2f}")
    
    # Get recent trades
    print("\n4. Recent Trades:")
    trades = db.get_trades(limit=5)
    for trade in trades:
        note = f" (Note: {trade['notes']})" if trade.get('notes') else ""
        print(f"   Ticket {trade['ticket']}: {trade['symbol']} {trade['type']} - P/L: {trade['profit']:.2f}{note}")
    
    # Export to CSV
    print("\n5. Exporting to CSV...")
    csv_path = 'demo_trades_export.csv'
    if db.export_to_csv(csv_path):
        print(f"   ✓ Exported to {csv_path}")
        print(f"   File size: {os.path.getsize(csv_path)} bytes")
    
    return db, trades


def demo_charts():
    """Demonstrate chart generation"""
    print("\n" + "="*60)
    print("📈 CHART GENERATION DEMO")
    print("="*60)
    
    # Get trades from database
    db = TradeHistoryDB(db_path='demo_trade_history.db')
    trades = db.get_trades()
    
    if not trades:
        print("\n❌ No trades found. Run demo_trade_history() first.")
        return
    
    chart_gen = ChartGenerator()
    
    print("\n1. Generating Equity Curve...")
    equity_bytes = chart_gen.generate_equity_curve(trades, output_path='demo_equity_curve.png')
    if equity_bytes or os.path.exists('demo_equity_curve.png'):
        print("   ✓ Equity curve saved to demo_equity_curve.png")
    
    print("\n2. Generating Daily P/L Chart...")
    daily_bytes = chart_gen.generate_daily_pnl_chart(trades, output_path='demo_daily_pnl.png')
    if daily_bytes or os.path.exists('demo_daily_pnl.png'):
        print("   ✓ Daily P/L chart saved to demo_daily_pnl.png")
    
    print("\n3. Generating Win/Loss Distribution...")
    dist_bytes = chart_gen.generate_win_loss_distribution(trades, output_path='demo_distribution.png')
    if dist_bytes or os.path.exists('demo_distribution.png'):
        print("   ✓ Win/Loss distribution saved to demo_distribution.png")
    
    print("\n4. Generating Performance Summary...")
    summary_bytes = chart_gen.generate_performance_summary_chart(trades, output_path='demo_summary.png')
    if summary_bytes or os.path.exists('demo_summary.png'):
        print("   ✓ Performance summary saved to demo_summary.png")
    
    print("\n✓ All charts generated successfully!")
    print("   Check the generated PNG files in the current directory.")


def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("🚀 MT5 TRADE ALERTS - HISTORICAL DATA & ANALYTICS DEMO")
    print("="*60)
    
    # Demo trade history
    db, trades = demo_trade_history()
    
    # Demo charts
    demo_charts()
    
    print("\n" + "="*60)
    print("✅ DEMO COMPLETE")
    print("="*60)
    print("\nGenerated files:")
    print("  - demo_trade_history.db (SQLite database)")
    print("  - demo_trades_export.csv (CSV export)")
    print("  - demo_equity_curve.png (Equity curve chart)")
    print("  - demo_daily_pnl.png (Daily P/L chart)")
    print("  - demo_distribution.png (Win/Loss distribution)")
    print("  - demo_summary.png (Performance summary)")
    print("\nHow it works in the real application:")
    print("  1. When a position closes, it's automatically recorded to the database")
    print("  2. Use /chart command in Telegram to generate and view charts")
    print("  3. Use /history command to view trade history")
    print("  4. Use /note <ticket> <note> to add notes to trades")
    print("  5. Use /export to download trade data as CSV")
    print("\n")


if __name__ == "__main__":
    main()
