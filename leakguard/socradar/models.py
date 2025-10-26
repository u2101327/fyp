# socradar/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# ✅ Define a shared enum for credential kinds
class CredentialKind(models.TextChoices):
    EMAIL = 'email', 'Email'
    USERNAME = 'username', 'Username'
    DOMAIN = 'domain', 'Domain'
    CUSTOM = 'custom', 'Custom Pattern'

class MonitoredCredential(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    # Core credential fields
    email = models.EmailField(blank=True, default="")
    username = models.CharField(max_length=150, blank=True)
    domain = models.CharField(max_length=255, blank=True, default="")
    # Removed fields: phone, credit_card, ssn (kept in DB for migration drop)
    custom_value = models.CharField(max_length=500, blank=True, default="")
    
    # Additional fields from frontend form
    credential_type = models.CharField(max_length=20, choices=CredentialKind.choices, default='email')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    tags = models.JSONField(default=list, blank=True)
    
    # User relationship
    owner = models.ForeignKey(User, on_delete=models.CASCADE,
                              related_name="monitored_credentials",
                              null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        # Return the primary credential value based on type
        if self.email:
            return f"Email: {self.email}"
        elif self.username:
            return f"Username: {self.username}"
        elif self.domain:
            return f"Domain: {self.domain}"
        elif self.custom_value:
            return f"Custom: {self.custom_value[:30]}..."
        else:
            return f"Credential #{self.pk}"
    
    @property
    def display_value(self):
        """Return a safe display value for the credential"""
        if self.credential_type == 'email':
            return self.email
        elif self.credential_type == 'username':
            return self.username
        elif self.credential_type == 'domain':
            return self.domain
        elif self.credential_type == 'custom':
            return self.custom_value
        else:
            return "Unknown" 

class CredentialLeak(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cred_type = models.CharField(max_length=20, choices=CredentialKind.choices)
    value = models.CharField(max_length=320)
    source = models.CharField(max_length=64)
    source_url = models.URLField(blank=True)
    leak_date = models.DateTimeField(null=True, blank=True)
    severity = models.IntegerField(default=50)
    plaintext = models.BooleanField(default=False)
    content = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.cred_type}: {self.value[:30]}"

class TelegramChannel(models.Model):
    VALIDATION_STATUS_CHOICES = [
        ('PUBLIC_OK', 'Public & Active'),
        ('NOT_FOUND', 'Not Found'),
        ('AUTH_ERROR', 'Authentication Error'),
        ('AUTH_TIMEOUT', 'Authentication Timeout'),
        ('FLOODWAIT', 'Rate Limited'),
        ('RPC_ERROR', 'API Error'),
        ('NO_API_CREDENTIALS', 'No API Credentials'),
        ('TELEGRAM_LIBRARY_MISSING', 'Library Missing'),
        ('ERROR', 'Connection Error'),
        ('PENDING', 'Pending Validation'),
    ]

    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, unique=True)
    url = models.URLField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    validation_status = models.CharField(
        max_length=50, 
        choices=VALIDATION_STATUS_CHOICES, 
        default='PENDING'
    )
    validation_date = models.DateTimeField(null=True, blank=True)
    validation_error = models.TextField(blank=True, null=True)
    last_scanned = models.DateTimeField(null=True, blank=True)
    
    # Scraping fields
    last_scraped_msg_id = models.BigIntegerField(default=0, help_text="Last scraped message ID for incremental scraping")
    scraping_status = models.CharField(
        max_length=20,
        choices=[
            ('IDLE', 'Idle'),
            ('PENDING', 'Pending'),
            ('RUNNING', 'Running'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
        ],
        default='IDLE'
    )
    scraping_task_id = models.CharField(max_length=255, blank=True, null=True, help_text="Celery task ID for current scraping job")
    scraping_error = models.TextField(blank=True, null=True, help_text="Last scraping error message")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"@{self.username}"

    def get_status_display_info(self):
        """Get status display information including color and text"""
        status_info = {
            'PUBLIC_OK': {'text': 'Active', 'color': 'green', 'bg_class': 'bg-green-100 text-green-800 dark:bg-green-700 dark:text-green-200'},
            'NOT_FOUND': {'text': 'Not Found', 'color': 'red', 'bg_class': 'bg-red-100 text-red-800 dark:bg-red-700 dark:text-red-200'},
            'AUTH_ERROR': {'text': 'Auth Error', 'color': 'orange', 'bg_class': 'bg-orange-100 text-orange-800 dark:bg-orange-700 dark:text-orange-200'},
            'AUTH_TIMEOUT': {'text': 'Auth Timeout', 'color': 'orange', 'bg_class': 'bg-orange-100 text-orange-800 dark:bg-orange-700 dark:text-orange-200'},
            'FLOODWAIT': {'text': 'Rate Limited', 'color': 'yellow', 'bg_class': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-700 dark:text-yellow-200'},
            'RPC_ERROR': {'text': 'API Error', 'color': 'red', 'bg_class': 'bg-red-100 text-red-800 dark:bg-red-700 dark:text-red-200'},
            'NO_API_CREDENTIALS': {'text': 'No API', 'color': 'gray', 'bg_class': 'bg-gray-100 text-gray-800 dark:bg-gray-600 dark:text-gray-300'},
            'TELEGRAM_LIBRARY_MISSING': {'text': 'Library Missing', 'color': 'gray', 'bg_class': 'bg-gray-100 text-gray-800 dark:bg-gray-600 dark:text-gray-300'},
            'ERROR': {'text': 'Error', 'color': 'red', 'bg_class': 'bg-red-100 text-red-800 dark:bg-red-700 dark:text-red-200'},
            'PENDING': {'text': 'Pending', 'color': 'blue', 'bg_class': 'bg-blue-100 text-blue-800 dark:bg-blue-700 dark:text-blue-200'},
        }
        
        return status_info.get(self.validation_status, {
            'text': 'Unknown', 
            'color': 'gray', 
            'bg_class': 'bg-gray-100 text-gray-800 dark:bg-gray-600 dark:text-gray-300'
        })

class TelegramMessage(models.Model):
    channel = models.ForeignKey(TelegramChannel, on_delete=models.CASCADE, related_name='messages')
    message_id = models.BigIntegerField()
    text = models.TextField()
    date = models.DateTimeField()
    sender_id = models.BigIntegerField(null=True, blank=True)
    sender_username = models.CharField(max_length=255, blank=True)
    is_forwarded = models.BooleanField(default=False)
    forwarded_from = models.CharField(max_length=255, blank=True)
    media_type = models.CharField(max_length=50, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    # Link-related fields
    has_links = models.BooleanField(default=False)
    link_count = models.IntegerField(default=0)
    validation_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('error', 'Error')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['channel', 'message_id']
        ordering = ['-date']

    def __str__(self):
        return f"Message {self.message_id} from {self.channel.username}"
    
    @property
    def valid_links_count(self):
        """Return count of valid links in this message"""
        return self.links.filter(validation_status='valid').count()
    
    @property
    def invalid_links_count(self):
        """Return count of invalid links in this message"""
        return self.links.filter(validation_status='invalid').count()

class TelegramLink(models.Model):
    """Model to track individual links found in Telegram messages"""
    VALIDATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
        ('redirect', 'Redirect'),
    ]
    
    # Core fields
    url = models.URLField(max_length=2000)
    message = models.ForeignKey(TelegramMessage, on_delete=models.CASCADE, related_name='links')
    channel = models.ForeignKey(TelegramChannel, on_delete=models.CASCADE, related_name='links')
    
    # Validation fields
    validation_status = models.CharField(
        max_length=20, 
        choices=VALIDATION_STATUS_CHOICES, 
        default='pending'
    )
    validation_date = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Response data
    final_url = models.URLField(max_length=2000, blank=True)  # After redirects
    status_code = models.IntegerField(null=True, blank=True)
    response_time = models.FloatField(null=True, blank=True)  # In seconds
    content_type = models.CharField(max_length=100, blank=True)
    content_length = models.BigIntegerField(null=True, blank=True)
    
    # Metadata
    is_telegram_link = models.BooleanField(default=False)
    is_suspicious = models.BooleanField(default=False)
    risk_score = models.IntegerField(default=0)  # 0-100 risk assessment
    tags = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['message', 'url']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['validation_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_suspicious']),
        ]
    
    def __str__(self):
        return f"{self.url[:50]}... ({self.validation_status})"
    
    @property
    def is_valid(self):
        """Check if the link is valid"""
        return self.validation_status == 'valid'
    
    @property
    def is_invalid(self):
        """Check if the link is invalid"""
        return self.validation_status == 'invalid'
    
    @property
    def needs_retry(self):
        """Check if the link needs retry validation"""
        return (self.validation_status in ['error', 'timeout'] and 
                self.retry_count < 3)
    
    def mark_as_valid(self, final_url=None, status_code=None, response_time=None):
        """Mark link as valid with response data"""
        self.validation_status = 'valid'
        self.validation_date = timezone.now()
        if final_url:
            self.final_url = final_url
        if status_code:
            self.status_code = status_code
        if response_time:
            self.response_time = response_time
        self.save()
    
    def mark_as_invalid(self, error_message=None):
        """Mark link as invalid with error message"""
        self.validation_status = 'invalid'
        self.validation_date = timezone.now()
        if error_message:
            self.error_message = error_message
        self.save()
    
    def mark_as_error(self, error_message, increment_retry=True):
        """Mark link as error with retry logic"""
        self.validation_status = 'error'
        self.validation_date = timezone.now()
        self.error_message = error_message
        if increment_retry:
            self.retry_count += 1
        self.save()

class DataLeak(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    email = models.EmailField(blank=True)
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=500, blank=True)
    domain = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=255)
    source_url = models.URLField(blank=True)
    leak_date = models.DateTimeField(null=True, blank=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    telegram_message = models.ForeignKey(TelegramMessage, on_delete=models.SET_NULL, null=True, blank=True)
    raw_data = models.TextField()
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email or self.username} - {self.source}"

class CrawledURL(models.Model):
    """Model to track URLs crawled from GitHub for investigation purposes"""
    url = models.URLField()
    username = models.CharField(max_length=255)
    channel_name = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=100, default='github')
    source_url = models.URLField(blank=True)
    crawl_session_id = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    credential_leaks_found = models.BooleanField(default=False)
    leak_count = models.IntegerField(default=0)
    investigation_notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    crawled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['username', 'crawl_session_id']
        ordering = ['-crawled_at']

    def __str__(self):
        return f"@{self.username} - {self.source}"

    @property
    def telegram_channel_url(self):
        """Return the Telegram channel URL for easy access"""
        return f"https://t.me/{self.username}"


class ProcessedFile(models.Model):
    """Model for storing processed file information"""
    
    # File identification
    message = models.ForeignKey(TelegramMessage, on_delete=models.CASCADE, related_name='processed_files')
    s3_uri = models.CharField(max_length=1000, help_text="S3 URI of the file in MinIO")
    
    # File metadata
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)
    file_extension = models.CharField(max_length=10)
    
    # Processing status
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('PROCESSING', 'Processing'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
        ],
        default='PENDING'
    )
    processing_error = models.TextField(blank=True, null=True)
    
    # Extracted data counts
    emails_count = models.IntegerField(default=0)
    passwords_count = models.IntegerField(default=0)
    usernames_count = models.IntegerField(default=0)
    domains_count = models.IntegerField(default=0)
    ip_addresses_count = models.IntegerField(default=0)
    phones_count = models.IntegerField(default=0)
    credit_cards_count = models.IntegerField(default=0)
    ssns_count = models.IntegerField(default=0)
    credentials_count = models.IntegerField(default=0)
    
    # Risk assessment
    risk_score = models.IntegerField(default=0, help_text="Risk score 0-100")
    is_sensitive = models.BooleanField(default=False)
    
    # Timestamps
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['message', 's3_uri']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['processing_status']),
            models.Index(fields=['risk_score']),
            models.Index(fields=['is_sensitive']),
            models.Index(fields=['processed_at']),
        ]
    
    def __str__(self):
        return f"{self.filename} - {self.processing_status}"


class ExtractedCredential(models.Model):
    """Model for storing extracted credentials"""
    
    # Source information
    processed_file = models.ForeignKey(ProcessedFile, on_delete=models.CASCADE, related_name='credentials')
    message = models.ForeignKey(TelegramMessage, on_delete=models.CASCADE, related_name='extracted_credentials')
    
    # Credential data
    email = models.EmailField(blank=True, null=True)
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=500, blank=True)
    domain = models.CharField(max_length=255, blank=True)
    
    # Additional data
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    credit_card = models.CharField(max_length=20, blank=True)
    ssn = models.CharField(max_length=15, blank=True)
    
    # Metadata
    extraction_method = models.CharField(max_length=50, default='regex')
    confidence_score = models.FloatField(default=0.0, help_text="Confidence score 0.0-1.0")
    is_verified = models.BooleanField(default=False)
    
    # Risk assessment
    risk_level = models.CharField(
        max_length=10,
        choices=[
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical'),
        ],
        default='LOW'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['processed_file', 'email', 'password']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['domain']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['is_verified']),
        ]
    
    def __str__(self):
        if self.email:
            return f"{self.email} - {self.risk_level}"
        elif self.username:
            return f"{self.username} - {self.risk_level}"
        else:
            return f"Credential {self.id} - {self.risk_level}"
    
    def calculate_risk_level(self):
        """Calculate risk level based on data types present"""
        score = 0
        
        if self.email:
            score += 1
        if self.password:
            score += 2
        if self.credit_card:
            score += 5
        if self.ssn:
            score += 5
        if self.ip_address:
            score += 1
        
        if score >= 5:
            return 'CRITICAL'
        elif score >= 3:
            return 'HIGH'
        elif score >= 2:
            return 'MEDIUM'
        else:
            return 'LOW'