#!/usr/bin/env python3
"""
Check fyptest channel data in database
"""

import os
import sys

# Django setup
import django
from django.conf import settings

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from socradar.models import TelegramChannel, TelegramMessage, DataLeak

def check_fyptest_data():
    """Check fyptest channel data"""
    
    print("=== FYP TEST CHANNEL DATA ===")
    
    # Find fyptest channel
    try:
        fyptest_channel = TelegramChannel.objects.get(name__icontains='fyptest')
        print(f"Channel: {fyptest_channel.name}")
        print(f"Username: @{fyptest_channel.username}")
        print(f"URL: {fyptest_channel.url}")
        print(f"Active: {fyptest_channel.is_active}")
        print(f"Last Scanned: {fyptest_channel.last_scanned}")
        print()
        
        # Get messages from fyptest channel
        messages = TelegramMessage.objects.filter(channel=fyptest_channel)
        print(f"Total Messages: {messages.count()}")
        print()
        
        if messages.exists():
            print("=== RECENT MESSAGES ===")
            for i, msg in enumerate(messages[:5], 1):
                print(f"{i}. From: {msg.sender_username}")
                print(f"   Text: {msg.text[:100]}...")
                print(f"   Date: {msg.date}")
                print()
        
        # Check for data leaks from fyptest
        leaks = DataLeak.objects.filter(source='fyptest')
        print(f"=== DATA LEAKS FROM FYP TEST ===")
        print(f"Total Leaks: {leaks.count()}")
        print()
        
        if leaks.exists():
            for i, leak in enumerate(leaks[:3], 1):
                print(f"{i}. Email: {leak.email}")
                print(f"   Username: {leak.username}")
                print(f"   Password: {leak.password}")
                print(f"   Severity: {leak.severity}")
                print(f"   Source: {leak.source}")
                print()
        
    except TelegramChannel.DoesNotExist:
        print("fyptest channel not found in database")
        
        # List all channels
        print("\n=== ALL CHANNELS ===")
        channels = TelegramChannel.objects.all()
        for ch in channels:
            print(f"- {ch.name} (@{ch.username})")

if __name__ == "__main__":
    check_fyptest_data()
