import os
import sys
import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import django
from django.conf import settings

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from opensearchpy import OpenSearch
from opensearchpy.exceptions import OpenSearchException
from socradar.models import TelegramMessage, DataLeak, TelegramChannel
from django.utils import timezone

class TelegramDataExtractor:
    def __init__(self):
        self.opensearch_client = self.setup_opensearch()
        self.media_base_dir = Path(settings.BASE_DIR) / 'media' / 'telegram'
        
        # Common patterns for data extraction
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            'credit_card': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
            'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b',
            'api_key': r'(?i)(api[_-]?key|apikey|access[_-]?key|secret[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
            'password': r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]{6,})["\']?',
            'url': r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'bitcoin_address': r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
            'ethereum_address': r'\b0x[a-fA-F0-9]{40}\b'
        }

    def setup_opensearch(self):
        """Setup OpenSearch client"""
        try:
            client = OpenSearch(
                hosts=[{'host': 'localhost', 'port': 9200}],
                http_auth=('admin', 'admin'),  # Update with your credentials
                use_ssl=False,
                verify_certs=False,
                ssl_assert_hostname=False,
                ssl_show_warn=False,
            )
            
            # Test connection
            client.info()
            print("✅ OpenSearch connection established")
            return client
        except Exception as e:
            print(f"❌ Failed to connect to OpenSearch: {e}")
            return None

    def extract_structured_data(self, message_text: str) -> Dict[str, List[str]]:
        """Extract structured data from message text"""
        extracted_data = {}
        
        for data_type, pattern in self.patterns.items():
            matches = re.findall(pattern, message_text, re.IGNORECASE)
            if matches:
                # Flatten matches if they're tuples
                if isinstance(matches[0], tuple):
                    matches = [match[1] if len(match) > 1 and match[1] else match[0] for match in matches]
                extracted_data[data_type] = list(set(matches))  # Remove duplicates
        
        return extracted_data

    def calculate_content_hash(self, content: str) -> str:
        """Calculate hash of content for deduplication"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def process_telegram_messages(self, limit: int = None):
        """Process Telegram messages and extract structured data"""
        print("🔍 Processing Telegram messages for data extraction...")
        
        # Get messages to process
        messages = TelegramMessage.objects.all().order_by('-message_date')
        if limit:
            messages = messages[:limit]
        
        total_messages = messages.count()
        processed = 0
        extracted_count = 0
        
        for message in messages:
            try:
                # Extract structured data
                extracted_data = self.extract_structured_data(message.message_text)
                
                if extracted_data:
                    # Save to OpenSearch with extracted data
                    self.save_extracted_data_to_opensearch(message, extracted_data)
                    extracted_count += 1
                
                processed += 1
                
                # Progress update
                if processed % 100 == 0:
                    progress = (processed / total_messages) * 100
                    print(f"📊 Progress: {progress:.1f}% ({processed}/{total_messages}) - Extracted: {extracted_count}")
                
            except Exception as e:
                print(f"❌ Error processing message {message.id}: {e}")
        
        print(f"✅ Processing complete! Processed {processed} messages, extracted data from {extracted_count}")

    def save_extracted_data_to_opensearch(self, message: TelegramMessage, extracted_data: Dict[str, List[str]]):
        """Save extracted data to OpenSearch"""
        if not self.opensearch_client:
            return False

        try:
            # Create document with extracted data
            doc = {
                'message_id': message.message_id,
                'channel_id': message.channel.channel_id,
                'channel_name': message.channel.name,
                'sender_id': message.sender_id,
                'sender_username': message.sender_username,
                'message_text': message.message_text,
                'message_date': message.message_date.isoformat(),
                'scraped_at': message.scraped_at.isoformat(),
                'extracted_data': extracted_data,
                'content_hash': self.calculate_content_hash(message.message_text),
                'data_types_found': list(extracted_data.keys()),
                'extraction_timestamp': timezone.now().isoformat(),
                'source': 'telegram_extraction'
            }

            # Index name for extracted data
            index_name = "telegram-extracted-data"
            
            # Create index if it doesn't exist
            if not self.opensearch_client.indices.exists(index=index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "message_id": {"type": "long"},
                            "channel_id": {"type": "keyword"},
                            "channel_name": {"type": "keyword"},
                            "sender_id": {"type": "long"},
                            "sender_username": {"type": "keyword"},
                            "message_text": {"type": "text", "analyzer": "standard"},
                            "message_date": {"type": "date"},
                            "scraped_at": {"type": "date"},
                            "extracted_data": {"type": "object"},
                            "content_hash": {"type": "keyword"},
                            "data_types_found": {"type": "keyword"},
                            "extraction_timestamp": {"type": "date"},
                            "source": {"type": "keyword"}
                        }
                    }
                }
                self.opensearch_client.indices.create(index=index_name, body=mapping)

            # Index the document
            doc_id = f"{message.channel.channel_id}_{message.message_id}_{self.calculate_content_hash(message.message_text)}"
            self.opensearch_client.index(
                index=index_name,
                id=doc_id,
                body=doc
            )
            return True

        except Exception as e:
            print(f"Error saving extracted data to OpenSearch: {e}")
            return False

    def detect_sensitive_data_leaks(self, message: TelegramMessage) -> List[Dict[str, Any]]:
        """Detect sensitive data leaks in message"""
        leaks = []
        message_text = message.message_text.lower()
        
        # High-risk patterns
        high_risk_patterns = {
            'password': r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?',
            'api_key': r'(?i)(api[_-]?key|apikey|access[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
            'secret': r'(?i)(secret|token|key)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?',
            'credit_card': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b',
            'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b'
        }
        
        for leak_type, pattern in high_risk_patterns.items():
            matches = re.findall(pattern, message_text)
            if matches:
                for match in matches:
                    if isinstance(match, tuple) and len(match) > 1:
                        leak_value = match[1]
                    else:
                        leak_value = match
                    
                    leaks.append({
                        'type': leak_type,
                        'value': leak_value,
                        'severity': 'high' if leak_type in ['password', 'api_key', 'secret', 'credit_card', 'ssn'] else 'medium',
                        'context': message.message_text[max(0, message.message_text.lower().find(leak_value) - 50):message.message_text.lower().find(leak_value) + len(leak_value) + 50]
                    })
        
        return leaks

    def process_data_leaks(self):
        """Process messages for data leak detection"""
        print("🚨 Processing messages for data leak detection...")
        
        messages = TelegramMessage.objects.all()
        total_messages = messages.count()
        processed = 0
        leaks_found = 0
        
        for message in messages:
            try:
                # Check if we already processed this message for leaks
                if DataLeak.objects.filter(telegram_message=message).exists():
                    continue
                
                leaks = self.detect_sensitive_data_leaks(message)
                
                if leaks:
                    for leak in leaks:
                        DataLeak.objects.create(
                            source='telegram',
                            source_id=f"{message.channel.channel_id}_{message.message_id}",
                            leak_type=leak['type'],
                            content=leak['context'],
                            detected_at=timezone.now(),
                            severity=leak['severity'],
                            status='detected',
                            telegram_message=message
                        )
                        leaks_found += 1
                
                processed += 1
                
                # Progress update
                if processed % 100 == 0:
                    progress = (processed / total_messages) * 100
                    print(f"📊 Progress: {progress:.1f}% ({processed}/{total_messages}) - Leaks found: {leaks_found}")
                
            except Exception as e:
                print(f"❌ Error processing message {message.id} for leaks: {e}")
        
        print(f"✅ Leak detection complete! Processed {processed} messages, found {leaks_found} potential leaks")

    def export_extracted_data(self, output_file: str = None):
        """Export extracted data to JSON file"""
        if not output_file:
            output_file = f"telegram_extracted_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        print(f"📤 Exporting extracted data to {output_file}...")
        
        try:
            # Get all messages with extracted data
            messages = TelegramMessage.objects.all()
            export_data = []
            
            for message in messages:
                extracted_data = self.extract_structured_data(message.message_text)
                
                if extracted_data:
                    export_data.append({
                        'message_id': message.message_id,
                        'channel_id': message.channel.channel_id,
                        'channel_name': message.channel.name,
                        'sender_username': message.sender_username,
                        'message_text': message.message_text,
                        'message_date': message.message_date.isoformat(),
                        'extracted_data': extracted_data,
                        'data_types_found': list(extracted_data.keys())
                    })
            
            # Save to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Exported {len(export_data)} messages with extracted data to {output_file}")
            
        except Exception as e:
            print(f"❌ Error exporting data: {e}")

    def get_statistics(self):
        """Get statistics about extracted data"""
        print("📊 Telegram Data Extraction Statistics")
        print("=" * 50)
        
        # Basic counts
        total_messages = TelegramMessage.objects.count()
        total_channels = TelegramChannel.objects.count()
        total_leaks = DataLeak.objects.count()
        
        print(f"Total Messages: {total_messages}")
        print(f"Total Channels: {total_channels}")
        print(f"Total Data Leaks Detected: {total_leaks}")
        
        # Leak statistics by type
        leak_types = DataLeak.objects.values('leak_type').distinct()
        print(f"\nLeak Types Found:")
        for leak_type in leak_types:
            count = DataLeak.objects.filter(leak_type=leak_type['leak_type']).count()
            print(f"  - {leak_type['leak_type']}: {count}")
        
        # Channel statistics
        print(f"\nMessages per Channel:")
        for channel in TelegramChannel.objects.all():
            count = TelegramMessage.objects.filter(channel=channel).count()
            print(f"  - {channel.name}: {count} messages")

def main():
    """Main function for command line usage"""
    import sys
    
    extractor = TelegramDataExtractor()
    
    if len(sys.argv) < 2:
        print("Usage: python telegram_data_extractor.py [command]")
        print("Commands:")
        print("  extract [limit] - Extract structured data from messages")
        print("  leaks - Detect data leaks in messages")
        print("  export [filename] - Export extracted data to JSON")
        print("  stats - Show statistics")
        return
    
    command = sys.argv[1]
    
    if command == 'extract':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
        extractor.process_telegram_messages(limit)
    elif command == 'leaks':
        extractor.process_data_leaks()
    elif command == 'export':
        filename = sys.argv[2] if len(sys.argv) > 2 else None
        extractor.export_extracted_data(filename)
    elif command == 'stats':
        extractor.get_statistics()
    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()
