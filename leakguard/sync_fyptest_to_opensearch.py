#!/usr/bin/env python3
"""
Sync fyptest channel messages to OpenSearch
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from socradar.models import TelegramChannel, TelegramMessage
from opensearchpy import OpenSearch

def sync_fyptest_to_opensearch():
    print("Syncing fyptest channel to OpenSearch...")
    
    # Setup OpenSearch client
    client = OpenSearch(
        hosts=[{'host': 'localhost', 'port': 9200}],
        http_auth=('admin', 'admin'),
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )
    
    try:
        # Get fyptest channel
        channel = TelegramChannel.objects.get(username='fyptest')
        print(f"Channel: {channel.name} (@{channel.username})")
        
        # Get all messages for this channel
        messages = TelegramMessage.objects.filter(channel=channel)
        print(f"Messages in Django: {messages.count()}")
        
        # Sync channel to OpenSearch
        channel_doc = {
            'id': channel.id,
            'name': channel.name,
            'username': channel.username,
            'url': channel.url,
            'is_active': channel.is_active,
            'created_at': channel.created_at.isoformat() if channel.created_at else None,
            'updated_at': channel.updated_at.isoformat() if channel.updated_at else None,
            'last_scanned': channel.last_scanned.isoformat() if channel.last_scanned else None
        }
        
        client.index(
            index='telegram_channels',
            id=channel.id,
            body=channel_doc
        )
        print("Channel synced to OpenSearch")
        
        # Sync messages to OpenSearch
        synced_count = 0
        for message in messages:
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
                    'id': channel.id,
                    'name': channel.name,
                    'username': channel.username
                }
            }
            
            client.index(
                index='telegram_messages',
                id=message.id,
                body=message_doc
            )
            synced_count += 1
            print(f"Synced message {message.message_id}: {message.text[:30]}...")
        
        print(f"Synced {synced_count} messages to OpenSearch")
        
        # Verify sync
        result = client.search(
            index='telegram_messages',
            body={
                'query': {
                    'term': {
                        'channel.id': channel.id
                    }
                }
            }
        )
        
        print(f"Verification: {result['hits']['total']['value']} messages found in OpenSearch")
        
        # Show what's now in OpenSearch
        print("\nMessages now in OpenSearch:")
        for hit in result['hits']['hits']:
            doc = hit['_source']
            print(f"  - {doc.get('text', '')[:50]}... (ID: {doc.get('message_id')})")
        
    except TelegramChannel.DoesNotExist:
        print("fyptest channel not found in database")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    sync_fyptest_to_opensearch()


