from django.contrib import admin
from .models import (
    MonitoredCredential, 
    CredentialLeak, 
    TelegramChannel, 
    TelegramMessage, 
    TelegramLink,
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
    list_display = ['channel', 'message_id', 'sender_username', 'has_links', 'link_count', 'validation_status', 'date', 'created_at']
    list_filter = ['channel', 'has_links', 'validation_status', 'date', 'created_at']
    search_fields = ['text', 'sender_username']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('channel')

@admin.register(TelegramLink)
class TelegramLinkAdmin(admin.ModelAdmin):
    list_display = ['url_short', 'channel', 'validation_status', 'status_code', 'is_suspicious', 'retry_count', 'created_at']
    list_filter = ['validation_status', 'is_suspicious', 'is_telegram_link', 'created_at', 'channel']
    search_fields = ['url', 'error_message']
    readonly_fields = ['created_at', 'updated_at', 'validation_date']
    raw_id_fields = ['message', 'channel']
    
    def url_short(self, obj):
        """Display shortened URL for admin list"""
        return obj.url[:60] + '...' if len(obj.url) > 60 else obj.url
    url_short.short_description = 'URL'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('message', 'channel')

@admin.register(DataLeak)
class DataLeakAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'source', 'severity', 'is_processed', 'created_at']
    list_filter = ['severity', 'is_processed', 'source', 'created_at']
    search_fields = ['email', 'username', 'source']
    readonly_fields = ['created_at']
