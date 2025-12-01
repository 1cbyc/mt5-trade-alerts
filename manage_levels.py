#!/usr/bin/env python3
"""
Utility script to manage price levels interactively
"""
import json
import sys
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
        'description': description if description else f"Price level at {price}"
    }
    
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


def main():
    """Main menu"""
    levels = load_levels()
    
    while True:
        print("\n=== Price Level Manager ===")
        print("1. Display all levels")
        print("2. Add new level")
        print("3. Remove level")
        print("4. Exit")
        
        choice = input("\nChoose an option: ").strip()
        
        if choice == '1':
            display_levels(levels)
        elif choice == '2':
            add_level(levels)
        elif choice == '3':
            remove_level(levels)
        elif choice == '4':
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

