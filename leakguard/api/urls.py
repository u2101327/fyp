from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for ViewSets (if we add any later)
router = DefaultRouter()

urlpatterns = [
    # Blog Posts (keeping existing)
    path('blogposts/', views.BlogPostListCreate.as_view(), name='blogpost-list-create'),
    path('blogposts/<int:pk>/', views.BlogPostRetrieveUpdateDestroy.as_view(), name='blogpost-detail'),
    
    # User Management
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    
    # Data Sources
    path('sources/', views.DataSourceListCreateView.as_view(), name='source-list-create'),
    path('sources/<int:pk>/', views.DataSourceDetailView.as_view(), name='source-detail'),
    
    # Monitored Credentials
    path('credentials/', views.MonitoredCredentialListCreateView.as_view(), name='credential-list-create'),
    path('credentials/<int:pk>/', views.MonitoredCredentialDetailView.as_view(), name='credential-detail'),
    path('credentials/bulk/', views.BulkCredentialCreateView.as_view(), name='credential-bulk-create'),
    
    # Credential Leaks
    path('leaks/', views.CredentialLeakListCreateView.as_view(), name='leak-list-create'),
    path('leaks/<int:pk>/', views.CredentialLeakDetailView.as_view(), name='leak-detail'),
    path('leaks/bulk-update/', views.BulkLeakUpdateView.as_view(), name='leak-bulk-update'),
    path('leaks/search/', views.LeakSearchView.as_view(), name='leak-search'),
    
    # Alerts
    path('alerts/', views.AlertListCreateView.as_view(), name='alert-list-create'),
    path('alerts/<int:pk>/', views.AlertDetailView.as_view(), name='alert-detail'),
    path('alerts/mark-read/', views.MarkAlertsReadView.as_view(), name='alert-mark-read'),
    
    # Monitoring Sessions
    path('sessions/', views.MonitoringSessionListCreateView.as_view(), name='session-list-create'),
    path('sessions/<int:pk>/', views.MonitoringSessionDetailView.as_view(), name='session-detail'),
    
    # Monitoring Control
    path('monitoring/start/', views.StartMonitoringView.as_view(), name='monitoring-start'),
    path('monitoring/stop/', views.StopMonitoringView.as_view(), name='monitoring-stop'),
    
    # Dashboard & Analytics
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('analytics/leaks/', views.LeakAnalyticsView.as_view(), name='leak-analytics'),
    path('analytics/sources/', views.SourceAnalyticsView.as_view(), name='source-analytics'),
    
    # Include router URLs
    path('', include(router.urls)),
]
