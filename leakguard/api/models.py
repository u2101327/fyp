from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class BlogPost(models.Model):
     tittle = models.CharField(max_length=100)
     content = models.TextField()
     published_date = models.DateTimeField(auto_now_add=True)

     def __str__(self):
          return self.tittle

# API Models for LeakGuard System
class MonitoredCredential(models.Model):
    """Model for credentials that users want to monitor"""
    CREDENTIAL_TYPES = [
        ('email', 'Email'),
        ('username', 'Username'),
        ('domain', 'Domain'),
        ('phone', 'Phone Number'),
        ('api_key', 'API Key'),
        ('password', 'Password'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_monitored_credentials')
    credential_type = models.CharField(max_length=20, choices=CREDENTIAL_TYPES)
    value = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['user', 'credential_type', 'value']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.credential_type}: {self.value[:30]}"

class DataSource(models.Model):
    """Model for tracking different data sources"""
    SOURCE_TYPES = [
        ('telegram', 'Telegram'),
        ('dark_web', 'Dark Web'),
        ('paste_site', 'Paste Site'),
        ('github', 'GitHub'),
        ('data_breach', 'Data Breach'),
        ('social_media', 'Social Media'),
        ('forum', 'Forum'),
    ]
    
    name = models.CharField(max_length=100)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    check_interval = models.IntegerField(default=3600)  # seconds
    created_at = models.DateTimeField(auto_now_add=True)
    configuration = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.source_type})"

class CredentialLeak(models.Model):
    """Model for storing discovered credential leaks"""
    SEVERITY_LEVELS = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('info', 'Informational'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('investigating', 'Investigating'),
        ('confirmed', 'Confirmed'),
        ('false_positive', 'False Positive'),
        ('resolved', 'Resolved'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_credential_leaks')
    monitored_credential = models.ForeignKey(MonitoredCredential, on_delete=models.CASCADE, null=True, blank=True)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    
    # Leak details
    credential_type = models.CharField(max_length=20)
    leaked_value = models.CharField(max_length=500)
    leak_content = models.TextField()
    leak_url = models.URLField(blank=True)
    
    # Metadata
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    confidence_score = models.FloatField(default=0.0)  # 0.0 to 1.0
    
    # Timestamps
    leak_date = models.DateTimeField(null=True, blank=True)
    discovered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional data
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-discovered_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['severity', 'discovered_at']),
            models.Index(fields=['source', 'discovered_at']),
        ]
    
    def __str__(self):
        return f"{self.credential_type}: {self.leaked_value[:30]}"

class Alert(models.Model):
    """Model for managing alerts and notifications"""
    ALERT_TYPES = [
        ('leak_detected', 'Leak Detected'),
        ('source_offline', 'Source Offline'),
        ('high_volume', 'High Volume Alert'),
        ('system_error', 'System Error'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    credential_leak = models.ForeignKey(CredentialLeak, on_delete=models.CASCADE, null=True, blank=True)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)
    
    # Alert status
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    priority = models.CharField(max_length=20, choices=CredentialLeak.SEVERITY_LEVELS, default='medium')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Notification settings
    email_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.alert_type}: {self.title}"

class MonitoringSession(models.Model):
    """Model for tracking monitoring sessions and statistics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_monitoring_sessions')
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    
    # Session details
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Statistics
    items_scanned = models.IntegerField(default=0)
    leaks_found = models.IntegerField(default=0)
    errors_encountered = models.IntegerField(default=0)
    
    # Configuration
    configuration = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Session {self.id} - {self.source.name}"

class UserProfile(models.Model):
    """Extended user profile for LeakGuard specific settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='api_profile')
    
    # Notification preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    webhook_url = models.URLField(blank=True)
    
    # Monitoring preferences
    default_severity_threshold = models.CharField(max_length=20, choices=CredentialLeak.SEVERITY_LEVELS, default='medium')
    auto_resolve_false_positives = models.BooleanField(default=False)
    
    # API settings
    api_key = models.CharField(max_length=64, unique=True, blank=True)
    api_rate_limit = models.IntegerField(default=1000)  # requests per hour
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile for {self.user.username}"