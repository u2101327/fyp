"""
OpenSearch document mappings for LeakGuard
Defines how data is indexed and searched in OpenSearch
"""

from django_opensearch_dsl import Document, fields
from django_opensearch_dsl.registries import registry
from .models import ExtractedCredential, ProcessedFile, TelegramChannel, TelegramMessage

@registry.register_document
class CredentialDocument(Document):
    """OpenSearch document for extracted credentials"""
    
    class Index:
        name = 'leakguard-credentials'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }
    
    # Basic credential data
    email = fields.TextField(
        analyzer='standard',
        fields={
            'keyword': fields.KeywordField(),
            'suggest': fields.CompletionField()
        }
    )
    username = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    password = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    domain = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    
    # Additional data
    ip_address = fields.IpField()
    phone = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    credit_card = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    ssn = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    
    # Metadata
    extraction_method = fields.KeywordField()
    confidence_score = fields.FloatField()
    is_verified = fields.BooleanField()
    risk_level = fields.KeywordField()
    
    # Source information
    channel_username = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    channel_name = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    message_id = fields.LongField()
    file_name = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    file_size = fields.LongField()
    file_mime_type = fields.KeywordField()
    
    # Risk assessment
    risk_score = fields.IntegerField()
    is_sensitive = fields.BooleanField()
    
    # Timestamps
    extracted_at = fields.DateField()
    message_date = fields.DateField()
    file_processed_at = fields.DateField()
    
    # Full text search
    content = fields.TextField(
        analyzer='standard',
        fields={
            'suggest': fields.CompletionField()
        }
    )
    
    class Django:
        model = ExtractedCredential
        fields = [
            'id',
            'created_at',
            'updated_at',
        ]
    
    def prepare_email(self, instance):
        """Prepare email field for indexing"""
        return instance.email or ''
    
    def prepare_username(self, instance):
        """Prepare username field for indexing"""
        return instance.username or ''
    
    def prepare_password(self, instance):
        """Prepare password field for indexing"""
        return instance.password or ''
    
    def prepare_domain(self, instance):
        """Prepare domain field for indexing"""
        if instance.email:
            return instance.email.split('@')[-1] if '@' in instance.email else ''
        return instance.domain or ''
    
    def prepare_ip_address(self, instance):
        """Prepare IP address field for indexing"""
        return instance.ip_address or None
    
    def prepare_phone(self, instance):
        """Prepare phone field for indexing"""
        return instance.phone or ''
    
    def prepare_credit_card(self, instance):
        """Prepare credit card field for indexing"""
        return instance.credit_card or ''
    
    def prepare_ssn(self, instance):
        """Prepare SSN field for indexing"""
        return instance.ssn or ''
    
    def prepare_extraction_method(self, instance):
        """Prepare extraction method field for indexing"""
        return instance.extraction_method or 'regex'
    
    def prepare_confidence_score(self, instance):
        """Prepare confidence score field for indexing"""
        return instance.confidence_score or 0.0
    
    def prepare_is_verified(self, instance):
        """Prepare is_verified field for indexing"""
        return instance.is_verified or False
    
    def prepare_risk_level(self, instance):
        """Prepare risk level field for indexing"""
        return instance.risk_level or 'LOW'
    
    def prepare_channel_username(self, instance):
        """Prepare channel username field for indexing"""
        return instance.message.channel.username if instance.message and instance.message.channel else ''
    
    def prepare_channel_name(self, instance):
        """Prepare channel name field for indexing"""
        return instance.message.channel.name if instance.message and instance.message.channel else ''
    
    def prepare_message_id(self, instance):
        """Prepare message ID field for indexing"""
        return instance.message.message_id if instance.message else None
    
    def prepare_file_name(self, instance):
        """Prepare file name field for indexing"""
        return instance.processed_file.filename if instance.processed_file else ''
    
    def prepare_file_size(self, instance):
        """Prepare file size field for indexing"""
        return instance.processed_file.file_size if instance.processed_file else 0
    
    def prepare_file_mime_type(self, instance):
        """Prepare file MIME type field for indexing"""
        return instance.processed_file.mime_type if instance.processed_file else ''
    
    def prepare_risk_score(self, instance):
        """Prepare risk score field for indexing"""
        return instance.processed_file.risk_score if instance.processed_file else 0
    
    def prepare_is_sensitive(self, instance):
        """Prepare is_sensitive field for indexing"""
        return instance.processed_file.is_sensitive if instance.processed_file else False
    
    def prepare_extracted_at(self, instance):
        """Prepare extracted_at field for indexing"""
        return instance.created_at.date() if instance.created_at else None
    
    def prepare_message_date(self, instance):
        """Prepare message date field for indexing"""
        return instance.message.date.date() if instance.message and instance.message.date else None
    
    def prepare_file_processed_at(self, instance):
        """Prepare file processed_at field for indexing"""
        return instance.processed_file.processed_at.date() if instance.processed_file and instance.processed_file.processed_at else None
    
    def prepare_content(self, instance):
        """Prepare full text content for searching"""
        content_parts = []
        
        if instance.email:
            content_parts.append(instance.email)
        if instance.username:
            content_parts.append(instance.username)
        if instance.domain:
            content_parts.append(instance.domain)
        if instance.message and instance.message.channel:
            content_parts.append(instance.message.channel.username)
            content_parts.append(instance.message.channel.name)
        if instance.processed_file:
            content_parts.append(instance.processed_file.filename)
        
        return ' '.join(content_parts)


@registry.register_document
class ProcessedFileDocument(Document):
    """OpenSearch document for processed files"""
    
    class Index:
        name = 'leakguard-processed-files'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }
    
    # File information
    filename = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    file_size = fields.LongField()
    mime_type = fields.KeywordField()
    file_extension = fields.KeywordField()
    
    # Processing status
    processing_status = fields.KeywordField()
    processing_error = fields.TextField()
    
    # Extracted data counts
    emails_count = fields.IntegerField()
    passwords_count = fields.IntegerField()
    usernames_count = fields.IntegerField()
    domains_count = fields.IntegerField()
    ip_addresses_count = fields.IntegerField()
    phones_count = fields.IntegerField()
    credit_cards_count = fields.IntegerField()
    ssns_count = fields.IntegerField()
    credentials_count = fields.IntegerField()
    
    # Risk assessment
    risk_score = fields.IntegerField()
    is_sensitive = fields.BooleanField()
    
    # Source information
    channel_username = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    channel_name = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    message_id = fields.LongField()
    s3_uri = fields.TextField(
        analyzer='standard',
        fields={'keyword': fields.KeywordField()}
    )
    
    # Timestamps
    processed_at = fields.DateField()
    message_date = fields.DateField()
    created_at = fields.DateField()
    
    class Django:
        model = ProcessedFile
        fields = [
            'id',
            'updated_at',
        ]
    
    def prepare_filename(self, instance):
        """Prepare filename field for indexing"""
        return instance.filename or ''
    
    def prepare_file_size(self, instance):
        """Prepare file size field for indexing"""
        return instance.file_size or 0
    
    def prepare_mime_type(self, instance):
        """Prepare MIME type field for indexing"""
        return instance.mime_type or ''
    
    def prepare_file_extension(self, instance):
        """Prepare file extension field for indexing"""
        return instance.file_extension or ''
    
    def prepare_processing_status(self, instance):
        """Prepare processing status field for indexing"""
        return instance.processing_status or 'PENDING'
    
    def prepare_processing_error(self, instance):
        """Prepare processing error field for indexing"""
        return instance.processing_error or ''
    
    def prepare_emails_count(self, instance):
        """Prepare emails count field for indexing"""
        return instance.emails_count or 0
    
    def prepare_passwords_count(self, instance):
        """Prepare passwords count field for indexing"""
        return instance.passwords_count or 0
    
    def prepare_usernames_count(self, instance):
        """Prepare usernames count field for indexing"""
        return instance.usernames_count or 0
    
    def prepare_domains_count(self, instance):
        """Prepare domains count field for indexing"""
        return instance.domains_count or 0
    
    def prepare_ip_addresses_count(self, instance):
        """Prepare IP addresses count field for indexing"""
        return instance.ip_addresses_count or 0
    
    def prepare_phones_count(self, instance):
        """Prepare phones count field for indexing"""
        return instance.phones_count or 0
    
    def prepare_credit_cards_count(self, instance):
        """Prepare credit cards count field for indexing"""
        return instance.credit_cards_count or 0
    
    def prepare_ssns_count(self, instance):
        """Prepare SSNs count field for indexing"""
        return instance.ssns_count or 0
    
    def prepare_credentials_count(self, instance):
        """Prepare credentials count field for indexing"""
        return instance.credentials_count or 0
    
    def prepare_risk_score(self, instance):
        """Prepare risk score field for indexing"""
        return instance.risk_score or 0
    
    def prepare_is_sensitive(self, instance):
        """Prepare is_sensitive field for indexing"""
        return instance.is_sensitive or False
    
    def prepare_channel_username(self, instance):
        """Prepare channel username field for indexing"""
        return instance.message.channel.username if instance.message and instance.message.channel else ''
    
    def prepare_channel_name(self, instance):
        """Prepare channel name field for indexing"""
        return instance.message.channel.name if instance.message and instance.message.channel else ''
    
    def prepare_message_id(self, instance):
        """Prepare message ID field for indexing"""
        return instance.message.message_id if instance.message else None
    
    def prepare_s3_uri(self, instance):
        """Prepare S3 URI field for indexing"""
        return instance.s3_uri or ''
    
    def prepare_processed_at(self, instance):
        """Prepare processed_at field for indexing"""
        return instance.processed_at.date() if instance.processed_at else None
    
    def prepare_message_date(self, instance):
        """Prepare message date field for indexing"""
        return instance.message.date.date() if instance.message and instance.message.date else None
    
    def prepare_created_at(self, instance):
        """Prepare created_at field for indexing"""
        return instance.created_at.date() if instance.created_at else None
