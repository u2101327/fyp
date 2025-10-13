# socradar/models.py
from django.db import models
from django.contrib.auth.models import User

# ✅ Define a shared enum for credential kinds
class CredentialKind(models.TextChoices):
    EMAIL = 'email', 'Email'
    USERNAME = 'username', 'Username'
    DOMAIN = 'domain', 'Domain'

class MonitoredCredential(models.Model):
    email = models.EmailField(blank=True, default="")   # ← allow empty
    username = models.CharField(max_length=150, blank=True)
    domain = models.CharField(max_length=255, blank=True, default="")
    owner = models.ForeignKey(User, on_delete=models.CASCADE,
                              related_name="monitored_credentials",
                              null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.email or self.username or f"Credential #{self.pk}" 

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
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, unique=True)
    url = models.URLField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_scanned = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"@{self.username}"

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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['channel', 'message_id']

    def __str__(self):
        return f"Message {self.message_id} from {self.channel.username}"

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