#!/usr/bin/env python3
"""
Debug OpenSearch sync issues
"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from socradar.models import TelegramChannel, TelegramMessage
from opensearchpy import OpenSearch

def debug_opensearch_sync():
    print("Debugging OpenSearch sync...")
    
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
        print(f"Channel ID: {channel.id}")
        print(f"Channel: {channel.name} (@{channel.username})")
        
        # Get all messages for this channel
        messages = TelegramMessage.objects.filter(channel=channel)
        print(f"Messages in Django: {messages.count()}")
        
        # Check each message
        for message in messages:
            print(f"\nMessage {message.id}:")
            print(f"  Text: {message.text[:50]}...")
            print(f"  Message ID: {message.message_id}")
            print(f"  Channel ID: {message.channel.id}")
            
            # Try to get from OpenSearch
            try:
                result = client.get(index='telegram_messages', id=message.id)
                print(f"  Status: EXISTS in OpenSearch")
            except:
                print(f"  Status: NOT in OpenSearch")
                
                # Try to index it
                try:
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
                    
                    response = client.index(
                        index='telegram_messages',
                        id=message.id,
                        body=message_doc
                    )
                    print(f"  Indexed: {response['result']}")
                    
                except Exception as e:
                    print(f"  Error indexing: {e}")
        
        # Final verification
        print("\n=== Final Verification ===")
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
        
        print(f"Total fyptest messages in OpenSearch: {result['hits']['total']['value']}")
        
        for hit in result['hits']['hits']:
            doc = hit['_source']
            print(f"  - {doc.get('text', '')[:50]}... (ID: {doc.get('message_id')})")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_opensearch_sync()


