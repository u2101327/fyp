from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    BlogPost, MonitoredCredential, DataSource, CredentialLeak, 
    Alert, MonitoringSession, UserProfile
)

class BlogPostSerializer(serializers.ModelSerializer): 
    class Meta:
        model = BlogPost
        fields = ['id', 'tittle', 'content', 'published_date']

# User Serializers
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'email_notifications', 'sms_notifications', 
            'webhook_url', 'default_severity_threshold', 
            'auto_resolve_false_positives', 'api_key', 'api_rate_limit',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'api_key', 'created_at', 'updated_at']

# Data Source Serializers
class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = [
            'id', 'name', 'source_type', 'url', 'is_active', 
            'last_checked', 'check_interval', 'created_at', 'configuration'
        ]
        read_only_fields = ['id', 'created_at', 'last_checked']

# Monitored Credential Serializers
class MonitoredCredentialSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = MonitoredCredential
        fields = [
            'id', 'user', 'credential_type', 'value', 'is_active',
            'created_at', 'updated_at', 'tags', 'notes'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

class MonitoredCredentialCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoredCredential
        fields = ['credential_type', 'value', 'is_active', 'tags', 'notes']

# Credential Leak Serializers
class CredentialLeakSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    monitored_credential = MonitoredCredentialSerializer(read_only=True)
    source = DataSourceSerializer(read_only=True)
    
    class Meta:
        model = CredentialLeak
        fields = [
            'id', 'user', 'monitored_credential', 'source', 'credential_type',
            'leaked_value', 'leak_content', 'leak_url', 'severity', 'status',
            'confidence_score', 'leak_date', 'discovered_at', 'updated_at',
            'tags', 'metadata', 'is_verified'
        ]
        read_only_fields = [
            'id', 'user', 'discovered_at', 'updated_at'
        ]

class CredentialLeakCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CredentialLeak
        fields = [
            'monitored_credential', 'source', 'credential_type', 'leaked_value',
            'leak_content', 'leak_url', 'severity', 'status', 'confidence_score',
            'leak_date', 'tags', 'metadata', 'is_verified'
        ]

class CredentialLeakUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CredentialLeak
        fields = ['status', 'severity', 'confidence_score', 'tags', 'is_verified']

# Alert Serializers
class AlertSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    credential_leak = CredentialLeakSerializer(read_only=True)
    source = DataSourceSerializer(read_only=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'user', 'alert_type', 'title', 'message', 'credential_leak',
            'source', 'is_read', 'is_resolved', 'priority', 'created_at',
            'read_at', 'resolved_at', 'email_sent', 'sms_sent'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'read_at', 'resolved_at'
        ]

class AlertCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            'alert_type', 'title', 'message', 'credential_leak', 'source', 'priority'
        ]

class AlertUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ['is_read', 'is_resolved']

# Monitoring Session Serializers
class MonitoringSessionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    source = DataSourceSerializer(read_only=True)
    
    class Meta:
        model = MonitoringSession
        fields = [
            'id', 'user', 'source', 'started_at', 'ended_at', 'is_active',
            'items_scanned', 'leaks_found', 'errors_encountered', 'configuration'
        ]
        read_only_fields = [
            'id', 'user', 'started_at', 'ended_at', 'items_scanned',
            'leaks_found', 'errors_encountered'
        ]

class MonitoringSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringSession
        fields = ['source', 'configuration']

# Dashboard Analytics Serializers
class DashboardStatsSerializer(serializers.Serializer):
    total_monitored_credentials = serializers.IntegerField()
    active_sources = serializers.IntegerField()
    total_leaks = serializers.IntegerField()
    critical_leaks = serializers.IntegerField()
    high_leaks = serializers.IntegerField()
    medium_leaks = serializers.IntegerField()
    low_leaks = serializers.IntegerField()
    unread_alerts = serializers.IntegerField()
    recent_leaks = CredentialLeakSerializer(many=True, read_only=True)
    recent_alerts = AlertSerializer(many=True, read_only=True)

class LeakAnalyticsSerializer(serializers.Serializer):
    leaks_by_severity = serializers.DictField()
    leaks_by_source = serializers.DictField()
    leaks_over_time = serializers.DictField()
    top_leaked_credentials = serializers.ListField()

class SourceAnalyticsSerializer(serializers.Serializer):
    source_name = serializers.CharField()
    source_type = serializers.CharField()
    total_leaks = serializers.IntegerField()
    last_checked = serializers.DateTimeField()
    is_active = serializers.BooleanField()
    success_rate = serializers.FloatField()

# Bulk Operations Serializers
class BulkCredentialCreateSerializer(serializers.Serializer):
    credentials = MonitoredCredentialCreateSerializer(many=True)
    
    def create(self, validated_data):
        user = self.context['request'].user
        credentials_data = validated_data['credentials']
        created_credentials = []
        
        for credential_data in credentials_data:
            credential = MonitoredCredential.objects.create(
                user=user,
                **credential_data
            )
            created_credentials.append(credential)
        
        return created_credentials

class BulkLeakUpdateSerializer(serializers.Serializer):
    leak_ids = serializers.ListField(child=serializers.IntegerField())
    status = serializers.ChoiceField(choices=CredentialLeak.STATUS_CHOICES)
    severity = serializers.ChoiceField(choices=CredentialLeak.SEVERITY_LEVELS, required=False)
    
    def update(self, instance, validated_data):
        leak_ids = validated_data['leak_ids']
        status = validated_data['status']
        severity = validated_data.get('severity')
        
        queryset = CredentialLeak.objects.filter(id__in=leak_ids, user=instance)
        
        update_data = {'status': status}
        if severity:
            update_data['severity'] = severity
            
        queryset.update(**update_data)
        return queryset