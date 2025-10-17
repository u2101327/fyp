#!/usr/bin/env python3
"""
Script to scrape messages specifically from fyptest channel
"""

import os
import asyncio
import sys
from datetime import datetime

# Django setup
import django
from django.conf import settings

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Channel
from socradar.models import TelegramChannel, TelegramMessage

# Telegram credentials
API_ID = 28362044
API_HASH = 'b0eacf843a2e57669a5fe96f8d22c9ba'
PHONE = '+60175861045'
SESSION_NAME = 'fyptest_session'

async def scrape_fyptest_channel():
    """Scrape messages from fyptest channel"""
    
    # Initialize Telegram client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    
    try:
        # Start the client
        await client.start(phone=PHONE)
        print("Telegram client started successfully")
        
        # Find the fyptest channel in database
        try:
            fyptest_channel = TelegramChannel.objects.get(name__icontains='fyptest')
            print(f"Found channel: {fyptest_channel.name} (@{fyptest_channel.username})")
        except TelegramChannel.DoesNotExist:
            print("fyptest channel not found in database")
            return
        
        # Get the actual Telegram channel
        try:
            telegram_entity = await client.get_entity(fyptest_channel.username)
            print(f"Connected to Telegram channel: {telegram_entity.title}")
        except Exception as e:
            print(f"Could not connect to Telegram channel: {e}")
            return
        
        # Scrape messages
        print("Scraping messages from fyptest channel...")
        messages_scraped = 0
        
        async for message in client.iter_messages(telegram_entity, limit=50):
            if message.text:  # Only process text messages
                # Create or update message in database
                telegram_msg, created = TelegramMessage.objects.get_or_create(
                    channel=fyptest_channel,
                    message_id=message.id,
                    defaults={
                        'text': message.text,
                        'sender_username': getattr(message.sender, 'username', '') if message.sender else '',
                        'sender_id': getattr(message.sender, 'id', 0) if message.sender else 0,
                        'date': message.date,
                    }
                )
                
                if created:
                    messages_scraped += 1
                    print(f"New message: {message.text[:50]}...")
                else:
                    print(f"Message already exists: {message.id}")
        
        print(f"Scraping completed! {messages_scraped} new messages added to database")
        
        # Update channel last_scanned
        fyptest_channel.last_scanned = datetime.now()
        fyptest_channel.save()
        print(f"Updated last_scanned timestamp for {fyptest_channel.name}")
        
    except Exception as e:
        print(f"Error during scraping: {e}")
    
    finally:
        await client.disconnect()
        print("Telegram client disconnected")

if __name__ == "__main__":
    print("Starting fyptest channel scraper...")
    asyncio.run(scrape_fyptest_channel())
