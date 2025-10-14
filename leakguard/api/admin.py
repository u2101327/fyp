from django.contrib import admin
from .models import (
    BlogPost,
    MonitoredCredential as APIMonitoredCredential,
    DataSource,
    CredentialLeak as APICredentialLeak,
    Alert
)

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['tittle', 'published_date']
    list_filter = ['published_date']
    search_fields = ['tittle', 'content']

@admin.register(APIMonitoredCredential)
class APIMonitoredCredentialAdmin(admin.ModelAdmin):
    list_display = ['credential_type', 'value', 'user', 'is_active', 'created_at']
    list_filter = ['credential_type', 'is_active', 'created_at']
    search_fields = ['value', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'is_active', 'last_checked', 'created_at']
    list_filter = ['source_type', 'is_active', 'created_at']
    search_fields = ['name', 'url']
    readonly_fields = ['created_at']

@admin.register(APICredentialLeak)
class APICredentialLeakAdmin(admin.ModelAdmin):
    list_display = ['credential_type', 'leaked_value', 'source', 'severity', 'status', 'discovered_at']
    list_filter = ['credential_type', 'severity', 'status', 'discovered_at']
    search_fields = ['leaked_value', 'source__name']
    readonly_fields = ['discovered_at', 'updated_at']

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'alert_type', 'priority', 'is_read', 'is_resolved', 'created_at']
    list_filter = ['alert_type', 'priority', 'is_read', 'is_resolved', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at']
