#!/usr/bin/env python3
"""
Find newly scraped data and sync it to OpenSearch
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from socradar.models import TelegramChannel, TelegramMessage
from opensearchpy import OpenSearch
from datetime import datetime, timedelta

def find_new_scraped_data():
    print("=== Finding Newly Scraped Data ===")
    
    # Check for recent messages (last 24 hours)
    recent_time = datetime.now() - timedelta(hours=24)
    
    # Get all channels
    channels = TelegramChannel.objects.all()
    print(f"Total channels: {channels.count()}")
    
    # Check for recent messages
    recent_messages = TelegramMessage.objects.filter(
        created_at__gte=recent_time
    ).order_by('-created_at')
    
    print(f"Recent messages (last 24 hours): {recent_messages.count()}")
    
    if recent_messages.count() > 0:
        print("\nRecent messages:")
        for message in recent_messages:
            print(f"  - {message.text[:50]}... (from @{message.channel.username})")
            print(f"    Created: {message.created_at}")
            print(f"    Message ID: {message.message_id}")
            print()
    
    # Check fyptest channel specifically
    try:
        fyptest_channel = TelegramChannel.objects.get(username='fyptest')
        fyptest_messages = TelegramMessage.objects.filter(channel=fyptest_channel)
        
        print(f"fyptest channel messages: {fyptest_messages.count()}")
        for message in fyptest_messages:
            print(f"  - {message.text} (ID: {message.message_id}, Created: {message.created_at})")
    except TelegramChannel.DoesNotExist:
        print("fyptest channel not found")
    
    # Check OpenSearch
    print("\n=== OpenSearch Check ===")
    client = OpenSearch(
        hosts=[{'host': 'localhost', 'port': 9200}],
        http_auth=('admin', 'admin'),
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )
    
    # Get total message count in OpenSearch
    result = client.search(
        index='telegram_messages',
        body={
            'query': {'match_all': {}},
            'size': 0
        }
    )
    
    total_opensearch = result['hits']['total']['value']
    total_django = TelegramMessage.objects.count()
    
    print(f"Messages in Django: {total_django}")
    print(f"Messages in OpenSearch: {total_opensearch}")
    
    if total_django > total_opensearch:
        print(f"SYNC NEEDED: {total_django - total_opensearch} messages not in OpenSearch")
        
        # Sync missing messages
        print("Syncing missing messages to OpenSearch...")
        sync_missing_messages(client)
    else:
        print("Data appears to be in sync")
    
    # Check for fyptest messages in OpenSearch
    try:
        fyptest_channel = TelegramChannel.objects.get(username='fyptest')
        fyptest_result = client.search(
            index='telegram_messages',
            body={
                'query': {
                    'term': {
                        'channel.id': fyptest_channel.id
                    }
                }
            }
        )
        
        print(f"fyptest messages in OpenSearch: {fyptest_result['hits']['total']['value']}")
        
        if fyptest_result['hits']['total']['value'] > 0:
            print("Sample fyptest messages in OpenSearch:")
            for hit in fyptest_result['hits']['hits'][:3]:
                doc = hit['_source']
                print(f"  - {doc.get('text', '')[:50]}...")
        
    except TelegramChannel.DoesNotExist:
        print("fyptest channel not found")

def sync_missing_messages(client):
    """Sync missing messages to OpenSearch"""
    print("Syncing messages to OpenSearch...")
    
    # Get all messages
    messages = TelegramMessage.objects.all()
    synced_count = 0
    
    for message in messages:
        try:
            # Check if message exists in OpenSearch
            try:
                client.get(index='telegram_messages', id=message.id)
                continue  # Already exists
            except:
                pass  # Doesn't exist, need to sync
            
            # Create message document
            message_doc = {
                'id': message.id,
                'text': message.text,
                'sender_username': message.sender_username,
                'sender_id': message.sender_id,
                'message_id': message.message_id,
                'date': message.date.isoformat() if message.date else None,
                'created_at': message.created_at.isoformat() if message.created_at else None,
                'is_forwarded': message.is_forwarded,
                'forwarded_from': message.forwarded_from,
                'media_type': message.media_type,
                'file_path': message.file_path,
                'channel': {
                    'id': message.channel.id,
                    'name': message.channel.name,
                    'username': message.channel.username
                }
            }
            
            # Index the message
            client.index(
                index='telegram_messages',
                id=message.id,
                body=message_doc
            )
            synced_count += 1
            
        except Exception as e:
            print(f"Error syncing message {message.id}: {e}")
    
    print(f"Synced {synced_count} messages to OpenSearch")

if __name__ == '__main__':
    find_new_scraped_data()


