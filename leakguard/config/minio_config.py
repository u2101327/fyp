"""
MinIO configuration for LeakGuard system
"""

# MinIO connection settings
MINIO_CONFIG = {
    'endpoint': 'localhost:9000',
    'access_key': 'admin123',
    'secret_key': 'admin123456',
    'secure': False,
    'region': 'us-east-1'
}

# Bucket configurations
BUCKET_CONFIGS = {
    'telegram_raw': {
        'name': 'telegram-raw-files',
        'policy': 'private',
        'versioning': True
    },
    'telegram_media': {
        'name': 'telegram-media-files', 
        'policy': 'private',
        'versioning': True
    },
    'processed_data': {
        'name': 'processed-data',
        'policy': 'private',
        'versioning': False
    }
}

# File path templates
FILE_PATHS = {
    'telegram_message': 'telegram/{channel_id}/messages/{message_id}.json',
    'telegram_media': 'telegram/{channel_id}/media/{message_id}_{filename}',
    'processed_data': 'processed/{date}/{source_type}/{file_id}.json'
}
