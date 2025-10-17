#!/usr/bin/env python3
"""
Test script to verify OpenSearch connection and setup
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from opensearchpy import OpenSearch
from opensearchpy.exceptions import OpenSearchException
from config.opensearch_config import OPENSEARCH_CONFIG, INDEX_SETTINGS

def test_opensearch_connection():
    """Test OpenSearch connection and basic operations"""
    print("🔍 Testing OpenSearch connection...")
    
    try:
        # Create client
        client = OpenSearch(**OPENSEARCH_CONFIG)
        
        # Test connection
        info = client.info()
        print(f"✅ Connected to OpenSearch cluster: {info['cluster_name']}")
        print(f"   Version: {info['version']['number']}")
        
        # Test index creation
        for index_name, settings in INDEX_SETTINGS.items():
            index_name_actual = settings['index_name']
            
            if client.indices.exists(index=index_name_actual):
                print(f"✅ Index '{index_name_actual}' already exists")
            else:
                try:
                    client.indices.create(
                        index=index_name_actual,
                        body=settings['mapping']
                    )
                    print(f"✅ Created index '{index_name_actual}'")
                except Exception as e:
                    print(f"❌ Failed to create index '{index_name_actual}': {e}")
        
        # Test document indexing
        test_doc = {
            'test_field': 'test_value',
            'timestamp': '2024-01-01T00:00:00Z',
            'source': 'test_script'
        }
        
        try:
            result = client.index(
                index='telegram-messages',
                id='test_doc_1',
                body=test_doc
            )
            print(f"✅ Successfully indexed test document: {result['_id']}")
            
            # Clean up test document
            client.delete(index='telegram-messages', id='test_doc_1')
            print("✅ Cleaned up test document")
            
        except Exception as e:
            print(f"❌ Failed to index test document: {e}")
        
        # List all indices
        indices = client.indices.get_alias("*")
        print(f"\n📋 Available indices:")
        for index_name in indices.keys():
            print(f"   - {index_name}")
        
        return True
        
    except OpenSearchException as e:
        print(f"❌ OpenSearch error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_django_models():
    """Test Django models and database connection"""
    print("\n🔍 Testing Django models...")
    
    try:
        from socradar.models import TelegramChannel, TelegramMessage, DataLeak
        
        # Test model imports
        print("✅ Successfully imported Django models")
        
        # Test database connection
        channel_count = TelegramChannel.objects.count()
        message_count = TelegramMessage.objects.count()
        leak_count = DataLeak.objects.count()
        
        print(f"✅ Database connection successful")
        print(f"   - Channels: {channel_count}")
        print(f"   - Messages: {message_count}")
        print(f"   - Data Leaks: {leak_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Django models test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting integration tests...")
    print("=" * 50)
    
    # Test OpenSearch
    opensearch_ok = test_opensearch_connection()
    
    # Test Django
    django_ok = test_django_models()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   OpenSearch: {'✅ PASS' if opensearch_ok else '❌ FAIL'}")
    print(f"   Django: {'✅ PASS' if django_ok else '❌ FAIL'}")
    
    if opensearch_ok and django_ok:
        print("\n🎉 All tests passed! Integration is ready.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the configuration.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
