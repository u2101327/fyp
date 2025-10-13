from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Q, Count, F
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import generics, status, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    BlogPost, MonitoredCredential, DataSource, CredentialLeak, 
    Alert, MonitoringSession, UserProfile
)
from .serializers import (
    BlogPostSerializer, UserSerializer, UserProfileSerializer,
    DataSourceSerializer, MonitoredCredentialSerializer, MonitoredCredentialCreateSerializer,
    CredentialLeakSerializer, CredentialLeakCreateSerializer, CredentialLeakUpdateSerializer,
    AlertSerializer, AlertCreateSerializer, AlertUpdateSerializer,
    MonitoringSessionSerializer, MonitoringSessionCreateSerializer,
    DashboardStatsSerializer, LeakAnalyticsSerializer, SourceAnalyticsSerializer,
    BulkCredentialCreateSerializer, BulkLeakUpdateSerializer
)

# Blog Post Views (keeping existing)
class BlogPostListCreate(generics.ListCreateAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer

    def delete(self, request, *args, **kwargs):
        BlogPost.objects.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class BlogPostRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    lookup_field = "pk"

# User Management Views
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

# Data Source Views
class DataSourceListCreateView(generics.ListCreateAPIView):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source_type', 'is_active']
    search_fields = ['name', 'url']
    ordering_fields = ['name', 'created_at', 'last_checked']
    ordering = ['-created_at']

class DataSourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [permissions.IsAuthenticated]

# Monitored Credential Views
class MonitoredCredentialListCreateView(generics.ListCreateAPIView):
    serializer_class = MonitoredCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['credential_type', 'is_active']
    search_fields = ['value', 'notes']
    ordering_fields = ['credential_type', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return MonitoredCredential.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MonitoredCredentialCreateSerializer
        return MonitoredCredentialSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class MonitoredCredentialDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MonitoredCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return MonitoredCredential.objects.filter(user=self.request.user)

class BulkCredentialCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = BulkCredentialCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            credentials = serializer.save()
            response_serializer = MonitoredCredentialSerializer(credentials, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Credential Leak Views
class CredentialLeakListCreateView(generics.ListCreateAPIView):
    serializer_class = CredentialLeakSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['credential_type', 'severity', 'status', 'source', 'is_verified']
    search_fields = ['leaked_value', 'leak_content']
    ordering_fields = ['severity', 'discovered_at', 'leak_date', 'confidence_score']
    ordering = ['-discovered_at']
    
    def get_queryset(self):
        return CredentialLeak.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CredentialLeakCreateSerializer
        return CredentialLeakSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CredentialLeakDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CredentialLeakSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CredentialLeak.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return CredentialLeakUpdateSerializer
        return CredentialLeakSerializer

class BulkLeakUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def patch(self, request):
        serializer = BulkLeakUpdateSerializer(data=request.data)
        if serializer.is_valid():
            updated_leaks = serializer.update(self.request.user, serializer.validated_data)
            response_serializer = CredentialLeakSerializer(updated_leaks, many=True)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Alert Views
class AlertListCreateView(generics.ListCreateAPIView):
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['alert_type', 'priority', 'is_read', 'is_resolved']
    search_fields = ['title', 'message']
    ordering_fields = ['priority', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Alert.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AlertCreateSerializer
        return AlertSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class AlertDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Alert.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return AlertUpdateSerializer
        return AlertSerializer

class MarkAlertsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        alert_ids = request.data.get('alert_ids', [])
        if alert_ids:
            Alert.objects.filter(
                id__in=alert_ids, 
                user=request.user
            ).update(is_read=True, read_at=timezone.now())
        else:
            Alert.objects.filter(user=request.user).update(
                is_read=True, 
                read_at=timezone.now()
            )
        return Response({'message': 'Alerts marked as read'}, status=status.HTTP_200_OK)

# Monitoring Session Views
class MonitoringSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = MonitoringSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['source', 'is_active']
    ordering_fields = ['started_at', 'ended_at']
    ordering = ['-started_at']
    
    def get_queryset(self):
        return MonitoringSession.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MonitoringSessionCreateSerializer
        return MonitoringSessionSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class MonitoringSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MonitoringSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return MonitoringSession.objects.filter(user=self.request.user)

# Dashboard and Analytics Views
class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Basic stats
        total_monitored_credentials = MonitoredCredential.objects.filter(user=user, is_active=True).count()
        active_sources = DataSource.objects.filter(is_active=True).count()
        total_leaks = CredentialLeak.objects.filter(user=user).count()
        
        # Leaks by severity
        critical_leaks = CredentialLeak.objects.filter(user=user, severity='critical').count()
        high_leaks = CredentialLeak.objects.filter(user=user, severity='high').count()
        medium_leaks = CredentialLeak.objects.filter(user=user, severity='medium').count()
        low_leaks = CredentialLeak.objects.filter(user=user, severity='low').count()
        
        # Unread alerts
        unread_alerts = Alert.objects.filter(user=user, is_read=False).count()
        
        # Recent data
        recent_leaks = CredentialLeak.objects.filter(user=user)[:5]
        recent_alerts = Alert.objects.filter(user=user)[:5]
        
        stats_data = {
            'total_monitored_credentials': total_monitored_credentials,
            'active_sources': active_sources,
            'total_leaks': total_leaks,
            'critical_leaks': critical_leaks,
            'high_leaks': high_leaks,
            'medium_leaks': medium_leaks,
            'low_leaks': low_leaks,
            'unread_alerts': unread_alerts,
            'recent_leaks': recent_leaks,
            'recent_alerts': recent_alerts,
        }
        
        serializer = DashboardStatsSerializer(stats_data)
        return Response(serializer.data)

class LeakAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Leaks by severity
        leaks_by_severity = dict(
            CredentialLeak.objects.filter(user=user)
            .values('severity')
            .annotate(count=Count('id'))
            .values_list('severity', 'count')
        )
        
        # Leaks by source
        leaks_by_source = dict(
            CredentialLeak.objects.filter(user=user)
            .values('source__name')
            .annotate(count=Count('id'))
            .values_list('source__name', 'count')
        )
        
        # Leaks over time (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        leaks_over_time = dict(
            CredentialLeak.objects.filter(
                user=user, 
                discovered_at__gte=thirty_days_ago
            )
            .extra(select={'day': 'date(discovered_at)'})
            .values('day')
            .annotate(count=Count('id'))
            .values_list('day', 'count')
        )
        
        # Top leaked credentials
        top_leaked_credentials = list(
            CredentialLeak.objects.filter(user=user)
            .values('leaked_value', 'credential_type')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        analytics_data = {
            'leaks_by_severity': leaks_by_severity,
            'leaks_by_source': leaks_by_source,
            'leaks_over_time': leaks_over_time,
            'top_leaked_credentials': top_leaked_credentials,
        }
        
        serializer = LeakAnalyticsSerializer(analytics_data)
        return Response(serializer.data)

class SourceAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        sources = DataSource.objects.all()
        analytics_data = []
        
        for source in sources:
            total_leaks = CredentialLeak.objects.filter(source=source).count()
            successful_checks = MonitoringSession.objects.filter(
                source=source, 
                errors_encountered=0
            ).count()
            total_checks = MonitoringSession.objects.filter(source=source).count()
            success_rate = (successful_checks / total_checks * 100) if total_checks > 0 else 0
            
            source_data = {
                'source_name': source.name,
                'source_type': source.source_type,
                'total_leaks': total_leaks,
                'last_checked': source.last_checked,
                'is_active': source.is_active,
                'success_rate': success_rate,
            }
            analytics_data.append(source_data)
        
        serializer = SourceAnalyticsSerializer(analytics_data, many=True)
        return Response(serializer.data)

# Monitoring Control Views
class StartMonitoringView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        source_id = request.data.get('source_id')
        configuration = request.data.get('configuration', {})
        
        try:
            source = DataSource.objects.get(id=source_id)
            session = MonitoringSession.objects.create(
                user=request.user,
                source=source,
                configuration=configuration
            )
            serializer = MonitoringSessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except DataSource.DoesNotExist:
            return Response(
                {'error': 'Source not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class StopMonitoringView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        session_id = request.data.get('session_id')
        
        try:
            session = MonitoringSession.objects.get(
                id=session_id, 
                user=request.user,
                is_active=True
            )
            session.is_active = False
            session.ended_at = timezone.now()
            session.save()
            
            serializer = MonitoringSessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MonitoringSession.DoesNotExist:
            return Response(
                {'error': 'Active monitoring session not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

# Search and Filter Views
class LeakSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        query = request.GET.get('q', '')
        severity = request.GET.get('severity')
        source_type = request.GET.get('source_type')
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        queryset = CredentialLeak.objects.filter(user=request.user)
        
        if query:
            queryset = queryset.filter(
                Q(leaked_value__icontains=query) |
                Q(leak_content__icontains=query) |
                Q(credential_type__icontains=query)
            )
        
        if severity:
            queryset = queryset.filter(severity=severity)
        
        if source_type:
            queryset = queryset.filter(source__source_type=source_type)
        
        if date_from:
            queryset = queryset.filter(discovered_at__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(discovered_at__lte=date_to)
        
        serializer = CredentialLeakSerializer(queryset, many=True)
        return Response(serializer.data)