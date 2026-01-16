"""
Trade history database module for storing and retrieving trade data
"""
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os

logger = logging.getLogger(__name__)


class TradeHistoryDB:
    """SQLite database for storing trade history"""
    
    def __init__(self, db_path: str = 'trade_history.db'):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket INTEGER UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                type TEXT NOT NULL,
                volume REAL NOT NULL,
                price_open REAL NOT NULL,
                price_close REAL,
                profit REAL NOT NULL,
                commission REAL DEFAULT 0,
                swap REAL DEFAULT 0,
                time_open TIMESTAMP NOT NULL,
                time_close TIMESTAMP,
                duration_seconds INTEGER,
                sl REAL,
                tp REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticket ON trades(ticket)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON trades(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_open ON trades(time_open)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_time_close ON trades(time_close)')
        
        conn.commit()
        conn.close()
        logger.info(f"Trade history database initialized: {self.db_path}")
    
    def add_trade(self, trade_data: Dict) -> bool:
        """
        Add or update a trade in the database
        
        Args:
            trade_data: Dictionary with trade information
        
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if trade already exists
            cursor.execute('SELECT id FROM trades WHERE ticket = ?', (trade_data.get('ticket'),))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing trade
                cursor.execute('''
                    UPDATE trades SET
                        symbol = ?, type = ?, volume = ?, price_open = ?, price_close = ?,
                        profit = ?, commission = ?, swap = ?, time_open = ?, time_close = ?,
                        duration_seconds = ?, sl = ?, tp = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE ticket = ?
                ''', (
                    trade_data.get('symbol'),
                    trade_data.get('type'),
                    trade_data.get('volume'),
                    trade_data.get('price_open'),
                    trade_data.get('price_close'),
                    trade_data.get('profit', 0),
                    trade_data.get('commission', 0),
                    trade_data.get('swap', 0),
                    trade_data.get('time_open'),
                    trade_data.get('time_close'),
                    trade_data.get('duration_seconds'),
                    trade_data.get('sl'),
                    trade_data.get('tp'),
                    trade_data.get('ticket')
                ))
            else:
                # Insert new trade
                cursor.execute('''
                    INSERT INTO trades (
                        ticket, symbol, type, volume, price_open, price_close,
                        profit, commission, swap, time_open, time_close,
                        duration_seconds, sl, tp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trade_data.get('ticket'),
                    trade_data.get('symbol'),
                    trade_data.get('type'),
                    trade_data.get('volume'),
                    trade_data.get('price_open'),
                    trade_data.get('price_close'),
                    trade_data.get('profit', 0),
                    trade_data.get('commission', 0),
                    trade_data.get('swap', 0),
                    trade_data.get('time_open'),
                    trade_data.get('time_close'),
                    trade_data.get('duration_seconds'),
                    trade_data.get('sl'),
                    trade_data.get('tp')
                ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding trade to database: {e}")
            return False
    
    def add_trade_note(self, ticket: int, note: str) -> bool:
        """
        Add or update notes for a trade
        
        Args:
            ticket: Trade ticket number
            note: Note text
        
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE trades SET notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE ticket = ?
            ''', (note, ticket))
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error adding trade note: {e}")
            return False
    
    def get_trade(self, ticket: int) -> Optional[Dict]:
        """Get a specific trade by ticket"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM trades WHERE ticket = ?', (ticket,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error getting trade: {e}")
            return None
    
    def get_trades(self, start_date: Optional[datetime] = None, 
                   end_date: Optional[datetime] = None,
                   symbol: Optional[str] = None,
                   limit: int = 1000) -> List[Dict]:
        """
        Get trades with optional filters
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            symbol: Symbol filter
            limit: Maximum number of trades to return
        
        Returns:
            List of trade dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM trades WHERE 1=1'
            params = []
            
            if start_date:
                query += ' AND time_close >= ?'
                params.append(start_date.isoformat())
            
            if end_date:
                query += ' AND time_close <= ?'
                params.append(end_date.isoformat())
            
            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)
            
            query += ' ORDER BY time_close DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def get_trade_statistics(self, start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Dict:
        """
        Get trade statistics for a period
        
        Returns:
            Dictionary with statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(profit) as total_profit,
                    AVG(CASE WHEN profit > 0 THEN profit ELSE NULL END) as avg_win,
                    AVG(CASE WHEN profit < 0 THEN profit ELSE NULL END) as avg_loss,
                    MAX(profit) as largest_win,
                    MIN(profit) as largest_loss,
                    SUM(commission) as total_commission,
                    SUM(swap) as total_swap
                FROM trades
                WHERE time_close IS NOT NULL
            '''
            params = []
            
            if start_date:
                query += ' AND time_close >= ?'
                params.append(start_date.isoformat())
            
            if end_date:
                query += ' AND time_close <= ?'
                params.append(end_date.isoformat())
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            conn.close()
            
            if row:
                stats = {
                    'total_trades': row[0] or 0,
                    'winning_trades': row[1] or 0,
                    'losing_trades': row[2] or 0,
                    'total_profit': row[3] or 0.0,
                    'average_win': row[4] or 0.0,
                    'average_loss': row[5] or 0.0,
                    'largest_win': row[6] or 0.0,
                    'largest_loss': row[7] or 0.0,
                    'total_commission': row[8] or 0.0,
                    'total_swap': row[9] or 0.0
                }
                
                if stats['total_trades'] > 0:
                    stats['win_rate'] = (stats['winning_trades'] / stats['total_trades']) * 100
                    stats['profit_factor'] = (
                        abs(stats['average_win'] * stats['winning_trades']) / 
                        abs(stats['average_loss'] * stats['losing_trades'])
                        if stats['average_loss'] != 0 and stats['losing_trades'] > 0 else 0.0
                    )
                else:
                    stats['win_rate'] = 0.0
                    stats['profit_factor'] = 0.0
                
                return stats
            
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_profit': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'total_commission': 0.0,
                'total_swap': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0
            }
        except Exception as e:
            logger.error(f"Error getting trade statistics: {e}")
            return {}
    
    def export_to_csv(self, file_path: str, start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None, symbol: Optional[str] = None) -> bool:
        """
        Export trades to CSV file
        
        Args:
            file_path: Path to save CSV file
            start_date: Start date filter
            end_date: End date filter
            symbol: Symbol filter
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import csv
            
            trades = self.get_trades(start_date=start_date, end_date=end_date, symbol=symbol)
            
            if not trades:
                return False
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                if trades:
                    writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                    writer.writeheader()
                    writer.writerows(trades)
            
            return True
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False
