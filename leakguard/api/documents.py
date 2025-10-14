from django_opensearch_dsl import Document, fields
from django_opensearch_dsl.registries import registry
from .models import BlogPost, MonitoredCredential, DataSource, CredentialLeak, Alert


@registry.register_document
class BlogPostDocument(Document):
    """OpenSearch document for BlogPost model"""
    
    class Index:
        name = 'blog_posts'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = BlogPost
        fields = [
            'id',
            'tittle',
            'content',
            'published_date',
        ]


@registry.register_document
class APIMonitoredCredentialDocument(Document):
    """OpenSearch document for API MonitoredCredential model"""
    
    class Index:
        name = 'api_monitored_credentials'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = MonitoredCredential
        fields = [
            'id',
            'credential_type',
            'value',
            'is_active',
            'created_at',
            'updated_at',
        ]


@registry.register_document
class DataSourceDocument(Document):
    """OpenSearch document for DataSource model"""
    
    class Index:
        name = 'data_sources'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = DataSource
        fields = [
            'id',
            'name',
            'source_type',
            'url',
            'is_active',
            'last_checked',
            'check_interval',
            'created_at',
        ]


@registry.register_document
class APICredentialLeakDocument(Document):
    """OpenSearch document for API CredentialLeak model"""
    
    class Index:
        name = 'api_credential_leaks'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = CredentialLeak
        fields = [
            'id',
            'credential_type',
            'leaked_value',
            'leak_content',
            'leak_url',
            'severity',
            'status',
            'confidence_score',
            'leak_date',
            'discovered_at',
            'updated_at',
            'is_verified',
        ]


@registry.register_document
class AlertDocument(Document):
    """OpenSearch document for Alert model"""
    
    class Index:
        name = 'alerts'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = Alert
        fields = [
            'id',
            'title',
            'message',
            'alert_type',
            'priority',
            'is_read',
            'is_resolved',
            'created_at',
            'read_at',
            'resolved_at',
            'email_sent',
            'sms_sent',
        ]
