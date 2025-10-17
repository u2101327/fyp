"""
OpenSearch configuration for the Telegram scraper integration
"""

# OpenSearch connection settings
OPENSEARCH_CONFIG = {
    'hosts': [{'host': 'localhost', 'port': 9200}],
    'http_auth': ('admin', 'admin'),  # Update with your actual credentials
    'use_ssl': False,
    'verify_certs': False,
    'ssl_assert_hostname': False,
    'ssl_show_warn': False,
    'timeout': 30,
    'max_retries': 3,
    'retry_on_timeout': True
}

# Index settings for different data types
INDEX_SETTINGS = {
    'telegram_messages': {
        'index_name': 'telegram-messages',
        'mapping': {
            "mappings": {
                "properties": {
                    "message_id": {"type": "long"},
                    "date": {"type": "date"},
                    "timestamp": {"type": "date"},
                    "sender_id": {"type": "long"},
                    "sender_first_name": {"type": "text"},
                    "sender_last_name": {"type": "text"},
                    "sender_username": {"type": "keyword"},
                    "message_text": {"type": "text", "analyzer": "standard"},
                    "media_type": {"type": "keyword"},
                    "media_path": {"type": "keyword"},
                    "reply_to": {"type": "long"},
                    "channel_id": {"type": "keyword"},
                    "channel_name": {"type": "keyword"},
                    "scraped_at": {"type": "date"},
                    "source": {"type": "keyword"}
                }
            }
        }
    },
    'telegram_extracted_data': {
        'index_name': 'telegram-extracted-data',
        'mapping': {
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
    },
    'data_leaks': {
        'index_name': 'data-leaks',
        'mapping': {
            "mappings": {
                "properties": {
                    "source": {"type": "keyword"},
                    "source_id": {"type": "keyword"},
                    "leak_type": {"type": "keyword"},
                    "content": {"type": "text", "analyzer": "standard"},
                    "detected_at": {"type": "date"},
                    "severity": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "channel_id": {"type": "keyword"},
                    "channel_name": {"type": "keyword"},
                    "message_id": {"type": "long"}
                }
            }
        }
    }
}

# Data extraction patterns
EXTRACTION_PATTERNS = {
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

# Leak detection patterns with severity levels
LEAK_PATTERNS = {
    'high': {
        'password': r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?',
        'api_key': r'(?i)(api[_-]?key|apikey|access[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
        'secret': r'(?i)(secret|token|key)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?',
        'credit_card': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b',
        'ssn': r'\b\d{3}-?\d{2}-?\d{4}\b'
    },
    'medium': {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
        'ip_address': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    },
    'low': {
        'url': r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        'bitcoin_address': r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
        'ethereum_address': r'\b0x[a-fA-F0-9]{40}\b'
    }
}
