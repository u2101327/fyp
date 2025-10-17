#!/usr/bin/env python3
"""
Script to populate sample data for testing the dashboard
"""

import os
import sys
import django
from datetime import datetime, timezone, timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from socradar.models import TelegramChannel, TelegramMessage, DataLeak, MonitoredCredential
from django.contrib.auth.models import User

def create_sample_data():
    """Create sample data for testing"""
    print("Creating sample data...")
    
    # Create sample Telegram channels
    sample_channels = [
        {
            'username': 'leak_channel_1',
            'name': 'Data Leaks Channel 1',
            'url': 'https://t.me/leak_channel_1',
            'description': 'Channel for leaked credentials and data breaches'
        },
        {
            'username': 'breach_notifications',
            'name': 'Breach Notifications',
            'url': 'https://t.me/breach_notifications',
            'description': 'Real-time breach notifications and credential dumps'
        },
        {
            'username': 'edu_leaks',
            'name': 'Educational Leaks',
            'url': 'https://t.me/edu_leaks',
            'description': 'Educational institution data leaks and breaches'
        }
    ]
    
    channels_created = 0
    for channel_data in sample_channels:
        channel, created = TelegramChannel.objects.get_or_create(
            username=channel_data['username'],
            defaults=channel_data
        )
        if created:
            channels_created += 1
            print(f"Created channel: @{channel.username}")
    
    print(f"Created {channels_created} new channels")
    
    # Create sample messages
    sample_messages = [
        {
            'channel_username': 'leak_channel_1',
            'text': 'user@example.com:password123\nadmin@test.com:admin123\njohn.doe@company.com:secret456',
            'message_id': 1001
        },
        {
            'channel_username': 'breach_notifications',
            'text': 'student@university.edu:student123\nprofessor@college.edu:prof123\nresearcher@institute.edu:research456',
            'message_id': 1002
        },
        {
            'channel_username': 'edu_leaks',
            'text': 'alice@school.edu:alice123\nbob@university.edu:bob456\ncharlie@college.edu:charlie789',
            'message_id': 1003
        }
    ]
    
    messages_created = 0
    for msg_data in sample_messages:
        try:
            channel = TelegramChannel.objects.get(username=msg_data['channel_username'])
            message, created = TelegramMessage.objects.get_or_create(
                channel=channel,
                message_id=msg_data['message_id'],
                defaults={
                    'text': msg_data['text'],
                    'date': datetime.now(timezone.utc),
                    'sender_username': 'sample_user'
                }
            )
            if created:
                messages_created += 1
                print(f"Created message in @{channel.username}")
        except TelegramChannel.DoesNotExist:
            print(f"Channel @{msg_data['channel_username']} not found")
    
    print(f"Created {messages_created} new messages")
    
    # Create sample data leaks
    sample_leaks = [
        {
            'email': 'user@example.com',
            'password': 'password123',
            'domain': 'example.com',
            'source': 'Telegram @leak_channel_1',
            'severity': 'medium',
            'raw_data': 'user@example.com:password123'
        },
        {
            'email': 'student@university.edu',
            'password': 'student123',
            'domain': 'university.edu',
            'source': 'Telegram @breach_notifications',
            'severity': 'high',
            'raw_data': 'student@university.edu:student123'
        },
        {
            'email': 'alice@school.edu',
            'password': 'alice123',
            'domain': 'school.edu',
            'source': 'Telegram @edu_leaks',
            'severity': 'high',
            'raw_data': 'alice@school.edu:alice123'
        }
    ]
    
    leaks_created = 0
    for leak_data in sample_leaks:
        leak, created = DataLeak.objects.get_or_create(
            email=leak_data['email'],
            password=leak_data['password'],
            defaults={
                **leak_data,
                'is_processed': True,
                'created_at': datetime.now(timezone.utc)
            }
        )
        if created:
            leaks_created += 1
            print(f"Created leak for {leak.email}")
    
    print(f"Created {leaks_created} new data leaks")
    
    # Create sample monitored credentials for the first user
    try:
        user = User.objects.first()
        if user:
            sample_credentials = [
                {'email': 'user@example.com'},
                {'username': 'testuser'},
                {'domain': 'university.edu'}
            ]
            
            creds_created = 0
            for cred_data in sample_credentials:
                if 'email' in cred_data:
                    cred, created = MonitoredCredential.objects.get_or_create(
                        owner=user,
                        email=cred_data['email']
                    )
                elif 'username' in cred_data:
                    cred, created = MonitoredCredential.objects.get_or_create(
                        owner=user,
                        username=cred_data['username']
                    )
                elif 'domain' in cred_data:
                    cred, created = MonitoredCredential.objects.get_or_create(
                        owner=user,
                        domain=cred_data['domain']
                    )
                
                if created:
                    creds_created += 1
                    print(f"Created monitored credential: {cred}")
            
            print(f"Created {creds_created} new monitored credentials")
        else:
            print("No users found in database")
    except Exception as e:
        print(f"Error creating monitored credentials: {e}")
    
    print("\nSample data creation completed!")
    print(f"Summary:")
    print(f"- Channels: {TelegramChannel.objects.count()}")
    print(f"- Messages: {TelegramMessage.objects.count()}")
    print(f"- Data Leaks: {DataLeak.objects.count()}")
    print(f"- Monitored Credentials: {MonitoredCredential.objects.count()}")

if __name__ == "__main__":
    create_sample_data()
