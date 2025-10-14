from django.contrib import admin
from .models import (
    MonitoredCredential, 
    CredentialLeak, 
    TelegramChannel, 
    TelegramMessage, 
    DataLeak
)

@admin.register(MonitoredCredential)
class MonitoredCredentialAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'domain', 'owner', 'created_at']
    list_filter = ['created_at', 'owner']
    search_fields = ['email', 'username', 'domain']
    readonly_fields = ['created_at']

@admin.register(CredentialLeak)
class CredentialLeakAdmin(admin.ModelAdmin):
    list_display = ['cred_type', 'value', 'source', 'severity', 'leak_date', 'created_at']
    list_filter = ['cred_type', 'severity', 'leak_date', 'created_at']
    search_fields = ['value', 'source']
    readonly_fields = ['created_at']

@admin.register(TelegramChannel)
class TelegramChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'username', 'is_active', 'last_scanned', 'created_at']
    list_filter = ['is_active', 'created_at', 'last_scanned']
    search_fields = ['name', 'username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = ['channel', 'message_id', 'sender_username', 'date', 'created_at']
    list_filter = ['channel', 'date', 'created_at']
    search_fields = ['text', 'sender_username']
    readonly_fields = ['created_at']

@admin.register(DataLeak)
class DataLeakAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'source', 'severity', 'is_processed', 'created_at']
    list_filter = ['severity', 'is_processed', 'source', 'created_at']
    search_fields = ['email', 'username', 'source']
    readonly_fields = ['created_at']
