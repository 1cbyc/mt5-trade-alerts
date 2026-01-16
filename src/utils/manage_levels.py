#!/usr/bin/env python3
"""
Utility script to manage price levels interactively
"""
import json
import sys
from datetime import datetime, timedelta
from config import Config


def load_levels():
    """Load price levels from file"""
    return Config.load_price_levels()


def save_levels(levels):
    """Save price levels to file"""
    Config.save_price_levels(levels)
    print("Price levels saved successfully!")


def display_levels(levels):
    """Display all configured price levels"""
    if not levels:
        print("No price levels configured.")
        return
    
    print("\n=== Current Price Levels ===\n")
    for symbol, symbol_levels in levels.items():
        print(f"Symbol: {symbol}")
        for level in symbol_levels:
            print(f"  - ID: {level.get('id', 'N/A')}")
            print(f"    Price: {level.get('price', 'N/A')}")
            print(f"    Type: {level.get('type', 'both')}")
            print(f"    Description: {level.get('description', 'N/A')}")
            if level.get('expiration'):
                print(f"    Expiration: {level.get('expiration')}")
            if level.get('recurring'):
                print(f"    Alert Type: 🔄 Recurring")
            else:
                print(f"    Alert Type: ⚡ One-time")
            if level.get('group'):
                print(f"    Group: {level.get('group')}")
            print()
        print("-" * 40)
        print()


def add_level(levels):
    """Add a new price level"""
    symbol = input("Enter symbol (e.g., EURUSD): ").upper().strip()
    if not symbol:
        print("Symbol cannot be empty!")
        return
    
    level_id = input("Enter level ID (unique identifier): ").strip()
    if not level_id:
        print("Level ID cannot be empty!")
        return
    
    try:
        price = float(input("Enter price level: "))
    except ValueError:
        print("Invalid price value!")
        return
    
    print("Level type options:")
    print("  1. above - Alert when price goes above")
    print("  2. below - Alert when price goes below")
    print("  3. both - Alert when price reaches exactly")
    type_choice = input("Choose type (1/2/3) [default: 3]: ").strip()
    
    type_map = {'1': 'above', '2': 'below', '3': 'both'}
    level_type = type_map.get(type_choice, 'both')
    
    description = input("Enter description (optional): ").strip()
    
    # Alert type (one-time vs recurring)
    print("\nAlert type:")
    print("  1. One-time - Alert only once when level is reached")
    print("  2. Recurring - Alert every time level is reached")
    alert_choice = input("Choose alert type (1/2) [default: 1]: ").strip()
    recurring = (alert_choice == '2')
    
    # Expiration date
    expiration = None
    exp_choice = input("Add expiration date? (y/n) [default: n]: ").strip().lower()
    if exp_choice == 'y':
        print("Enter expiration date/time:")
        print("Format: YYYY-MM-DD or YYYY-MM-DD HH:MM")
        exp_input = input("Expiration: ").strip()
        try:
            if len(exp_input) == 10:  # Date only
                expiration = datetime.strptime(exp_input, '%Y-%m-%d').isoformat()
            else:  # Date and time
                expiration = datetime.strptime(exp_input, '%Y-%m-%d %H:%M').isoformat()
        except ValueError:
            print("Invalid date format! Skipping expiration.")
    
    # Group
    group = None
    group_choice = input("Add to a group? (y/n) [default: n]: ").strip().lower()
    if group_choice == 'y':
        group = input("Enter group ID: ").strip()
        if not group:
            group = None
    
    if symbol not in levels:
        levels[symbol] = []
    
    # Check if level ID already exists
    for existing_level in levels[symbol]:
        if existing_level.get('id') == level_id:
            print(f"Level ID '{level_id}' already exists for {symbol}!")
            return
    
    new_level = {
        'id': level_id,
        'price': price,
        'type': level_type,
        'description': description if description else f"Price level at {price}",
        'recurring': recurring
    }
    
    if expiration:
        new_level['expiration'] = expiration
    
    if group:
        new_level['group'] = group
        # Ask for group settings if this is the first level in the group
        group_levels = [l for l in levels[symbol] if l.get('group') == group]
        if not group_levels:
            group_desc = input(f"Enter group description for '{group}' (optional): ").strip()
            if group_desc:
                new_level['group_description'] = group_desc
            try:
                required_count = int(input("How many levels must trigger to alert? [default: 2]: ").strip() or "2")
                new_level['group_required_count'] = required_count
            except ValueError:
                new_level['group_required_count'] = 2
    
    levels[symbol].append(new_level)
    save_levels(levels)
    print(f"Added level '{level_id}' for {symbol} at {price}")


def remove_level(levels):
    """Remove a price level"""
    symbol = input("Enter symbol: ").upper().strip()
    if symbol not in levels or not levels[symbol]:
        print(f"No levels configured for {symbol}")
        return
    
    print(f"\nLevels for {symbol}:")
    for i, level in enumerate(levels[symbol], 1):
        print(f"  {i}. {level.get('id')} - {level.get('price')} ({level.get('type')})")
    
    try:
        choice = int(input("Enter number to remove: "))
        if 1 <= choice <= len(levels[symbol]):
            removed = levels[symbol].pop(choice - 1)
            print(f"Removed level '{removed.get('id')}'")
            
            if not levels[symbol]:
                del levels[symbol]
            
            save_levels(levels)
        else:
            print("Invalid choice!")
    except ValueError:
        print("Invalid input!")


def detect_levels(levels):
    """Auto-detect support/resistance levels for a symbol"""
    try:
        from mt5_monitor import MT5Monitor
        from config import Config
        
        print("\n=== Auto-Detect Support/Resistance Levels ===")
        symbol = input("Enter symbol to analyze: ").upper().strip()
        if not symbol:
            print("Symbol cannot be empty!")
            return
        
        # Initialize MT5 monitor
        monitor = MT5Monitor(
            login=Config.MT5_LOGIN,
            password=Config.MT5_PASSWORD,
            server=Config.MT5_SERVER,
            path=Config.MT5_PATH
        )
        
        if not monitor.connect():
            print("Failed to connect to MT5. Please check your configuration.")
            return
        
        try:
            print(f"\nAnalyzing {symbol}...")
            detected = monitor.detect_support_resistance(
                symbol=symbol,
                timeframe=Config.DYNAMIC_LEVELS_TIMEFRAME,
                periods=Config.DYNAMIC_LEVELS_PERIODS,
                min_touches=Config.DYNAMIC_LEVELS_MIN_TOUCHES,
                tolerance_pct=Config.DYNAMIC_LEVELS_TOLERANCE_PCT
            )
            
            if not detected['support'] and not detected['resistance']:
                print("No support/resistance levels detected.")
                return
            
            print(f"\nDetected {len(detected['support'])} support levels:")
            for price in detected['support']:
                print(f"  - Support: {price}")
            
            print(f"\nDetected {len(detected['resistance'])} resistance levels:")
            for price in detected['resistance']:
                print(f"  - Resistance: {price}")
            
            add_choice = input("\nAdd these levels? (y/n): ").strip().lower()
            if add_choice == 'y':
                if symbol not in levels:
                    levels[symbol] = []
                
                # Remove old dynamic levels
                levels[symbol] = [
                    l for l in levels[symbol] 
                    if not l.get('id', '').startswith('dynamic_')
                ]
                
                # Add support levels
                for idx, price in enumerate(detected['support'], 1):
                    levels[symbol].append({
                        'id': f'dynamic_support_{idx}',
                        'price': price,
                        'type': 'below',
                        'description': f'Auto-detected support level #{idx}',
                        'recurring': True,
                        'dynamic': True
                    })
                
                # Add resistance levels
                for idx, price in enumerate(detected['resistance'], 1):
                    levels[symbol].append({
                        'id': f'dynamic_resistance_{idx}',
                        'price': price,
                        'type': 'above',
                        'description': f'Auto-detected resistance level #{idx}',
                        'recurring': True,
                        'dynamic': True
                    })
                
                save_levels(levels)
                print(f"Added {len(detected['support']) + len(detected['resistance'])} levels for {symbol}")
        
        finally:
            monitor.disconnect()
    
    except ImportError:
        print("MT5 monitor not available. Make sure MetaTrader5 is installed.")
    except Exception as e:
        print(f"Error detecting levels: {e}")


def main():
    """Main menu"""
    levels = load_levels()
    
    while True:
        print("\n=== Price Level Manager ===")
        print("1. Display all levels")
        print("2. Add new level")
        print("3. Remove level")
        print("4. Auto-detect support/resistance levels")
        print("5. Exit")
        
        choice = input("\nChoose an option: ").strip()
        
        if choice == '1':
            display_levels(levels)
        elif choice == '2':
            add_level(levels)
        elif choice == '3':
            remove_level(levels)
        elif choice == '4':
            detect_levels(levels)
        elif choice == '5':
            print("Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)

