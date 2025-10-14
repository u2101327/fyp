from django_opensearch_dsl import Document, fields
from django_opensearch_dsl.registries import registry
from .models import TelegramChannel, TelegramMessage, DataLeak, MonitoredCredential, CredentialLeak


@registry.register_document
class TelegramChannelDocument(Document):
    """OpenSearch document for TelegramChannel model"""
    
    class Index:
        name = 'telegram_channels'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = TelegramChannel
        fields = [
            'id',
            'name',
            'username', 
            'description',
            'is_active',
            'last_scanned',
            'created_at',
            'updated_at',
        ]


@registry.register_document
class TelegramMessageDocument(Document):
    """OpenSearch document for TelegramMessage model"""
    
    class Index:
        name = 'telegram_messages'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = TelegramMessage
        fields = [
            'id',
            'text',
            'sender_username',
            'sender_id',
            'message_id',
            'date',
            'created_at',
        ]
        related_models = [TelegramChannel]


@registry.register_document
class DataLeakDocument(Document):
    """OpenSearch document for DataLeak model"""
    
    class Index:
        name = 'data_leaks'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = DataLeak
        fields = [
            'id',
            'email',
            'username',
            'password',
            'domain',
            'phone',
            'source',
            'source_url',
            'severity',
            'leak_date',
            'raw_data',
            'is_processed',
            'created_at',
        ]


@registry.register_document
class MonitoredCredentialDocument(Document):
    """OpenSearch document for MonitoredCredential model"""
    
    class Index:
        name = 'monitored_credentials'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = MonitoredCredential
        fields = [
            'id',
            'email',
            'username',
            'domain',
            'created_at',
        ]


@registry.register_document
class CredentialLeakDocument(Document):
    """OpenSearch document for CredentialLeak model"""
    
    class Index:
        name = 'credential_leaks'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = CredentialLeak
        fields = [
            'id',
            'cred_type',
            'value',
            'source',
            'source_url',
            'leak_date',
            'severity',
            'plaintext',
            'content',
            'created_at',
        ]