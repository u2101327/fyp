#!/usr/bin/env python3
"""
Add sample real data to fyptest channel for testing
"""

import os
import sys
from datetime import datetime, timedelta

# Django setup
import django
from django.conf import settings

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from socradar.models import TelegramChannel, TelegramMessage, DataLeak

def add_sample_fyptest_data():
    """Add sample real data to fyptest channel"""
    
    print("Adding sample real data to fyptest channel...")
    
    # Find or create fyptest channel
    fyptest_channel, created = TelegramChannel.objects.get_or_create(
        username='fyptest',
        defaults={
            'name': 'FYP Test Channel',
            'url': 'https://t.me/fyptest',
            'description': 'Test channel for FYP project',
            'is_active': True,
        }
    )
    
    if created:
        print(f"Created new channel: {fyptest_channel.name}")
    else:
        print(f"Found existing channel: {fyptest_channel.name}")
    
    # Sample real messages that might contain credential data
    sample_messages = [
        {
            'text': 'Email: john.doe@example.com Password: mypassword123',
            'sender_username': 'testuser1',
            'sender_id': 1001,
        },
        {
            'text': 'Found leaked credentials: admin@company.com / admin123',
            'sender_username': 'leakfinder',
            'sender_id': 1002,
        },
        {
            'text': 'Database dump contains: user@domain.com:secretpass',
            'sender_username': 'dataminer',
            'sender_id': 1003,
        },
        {
            'text': 'New breach detected: test@email.com password: testpass456',
            'sender_username': 'securitybot',
            'sender_id': 1004,
        },
        {
            'text': 'Credentials found: username: admin password: password123',
            'sender_username': 'scanner',
            'sender_id': 1005,
        },
        {
            'text': 'Leaked data: email@test.com / mypassword',
            'sender_username': 'finder',
            'sender_id': 1006,
        },
        {
            'text': 'Just a regular message without credentials',
            'sender_username': 'normaluser',
            'sender_id': 1007,
        },
        {
            'text': 'Another leak: user@example.org password: 123456',
            'sender_username': 'leakbot',
            'sender_id': 1008,
        }
    ]
    
    # Add messages to database
    messages_added = 0
    for i, msg_data in enumerate(sample_messages):
        message, created = TelegramMessage.objects.get_or_create(
            channel=fyptest_channel,
            message_id=1000 + i,  # Unique message IDs
            defaults={
                'text': msg_data['text'],
                'sender_username': msg_data['sender_username'],
                'sender_id': msg_data['sender_id'],
                'date': datetime.now() - timedelta(hours=i),
            }
        )
        
        if created:
            messages_added += 1
            print(f"Added message: {msg_data['text'][:50]}...")
        else:
            print(f"Message already exists: {msg_data['text'][:50]}...")
    
    print(f"Added {messages_added} new messages to fyptest channel")
    
    # Update channel last_scanned
    fyptest_channel.last_scanned = datetime.now()
    fyptest_channel.save()
    print(f"Updated last_scanned timestamp for {fyptest_channel.name}")
    
    # Now process the messages to extract credential data
    print("Processing messages to extract credential data...")
    
    from data_processor import CredentialProcessor
    processor = CredentialProcessor()
    
    leaks_created = 0
    for message in TelegramMessage.objects.filter(channel=fyptest_channel):
        # Process each line of the message
        for line in message.text.split('\n'):
            if line.strip():
                cred = processor.process_line(line)
                if cred:
                    # Create DataLeak record
                    data_leak, created = DataLeak.objects.get_or_create(
                        email=cred.get('email', ''),
                        username=cred.get('username', ''),
                        password=cred.get('password', ''),
                        source='fyptest',
                        source_url='https://t.me/fyptest',
                        telegram_message=message,
                        raw_data=line,
                        severity=cred.get('severity', 'medium'),
                        defaults={
                            'leak_date': message.date,
                            'is_processed': True,
                        }
                    )
                    
                    if created:
                        leaks_created += 1
                        print(f"Created data leak: {cred.get('email', cred.get('username', 'Unknown'))}")
    
    print(f"Created {leaks_created} data leaks from fyptest messages")
    print("Sample data added successfully!")

if __name__ == "__main__":
    add_sample_fyptest_data()
