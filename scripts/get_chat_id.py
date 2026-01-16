#!/usr/bin/env python3
"""
Helper script to get Telegram Chat ID
"""
import asyncio
from telegram import Bot
import sys

async def get_chat_id():
    """Get chat ID from bot updates"""
    print("Telegram Chat ID Helper")
    print("=" * 40)
    
    # Get bot token
    bot_token = input("Enter your Telegram bot token: ").strip()
    
    if not bot_token:
        print("Error: Bot token is required")
        sys.exit(1)
    
    try:
        bot = Bot(token=bot_token)
        
        print("\nFetching updates...")
        print("(Make sure you've sent a message to your bot or in a group where the bot is added)")
        print()
        
        updates = await bot.get_updates()
        
        if not updates:
            print("No updates found. Please:")
            print("1. Send a message to your bot (for personal chat)")
            print("2. OR add the bot to a group and send a message in the group")
            print("3. Then run this script again")
            sys.exit(1)
        
        print("Found the following chats:\n")
        
        seen_chats = set()
        for update in updates:
            if update.message:
                chat = update.message.chat
                chat_key = (chat.id, chat.type)
                
                if chat_key not in seen_chats:
                    seen_chats.add(chat_key)
                    chat_type = "Group" if chat.type in ['group', 'supergroup'] else "Private"
                    
                    print(f"Chat Type: {chat_type}")
                    print(f"Chat ID: {chat.id}")
                    
                    if chat.title:
                        print(f"Group Name: {chat.title}")
                    elif chat.first_name:
                        print(f"User Name: {chat.first_name}")
                    
                    print("-" * 40)
        
        if seen_chats:
            print("\n✅ Copy the Chat ID you need to your config.env file")
            print("   (For groups, the ID will be negative)")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. Your bot token is correct")
        print("2. You've sent at least one message to the bot or in the group")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(get_chat_id())

