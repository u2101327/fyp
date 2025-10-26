from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.registerPage, name='register'),
    path('login/', views.loginPage, name='login'),  
    path('logout/', views.logout_view, name='logout'),   
    path('dashboard/', views.dashboard, name='dashboard'),
    path('credentials/add/', views.add_monitored_credential, name='add_monitored_credential'),
    path('demo/', views.demo_leak_detection, name='demo_leak_detection'),
    path('demo/telegram/', views.demo_telegram_collection, name='demo_telegram_collection'),
    path('telegram/', views.telegram_monitor, name='telegram_monitor'),
    path('telegram/process/', views.process_telegram_data, name='process_telegram_data'),
    path('telegram/auto-collect/', views.auto_telegram_collection, name='auto_telegram_collection'),
    path('telegram/scrape/', views.start_telegram_scraping, name='start_telegram_scraping'),
    path('telegram/crawled-urls/', views.crawled_urls_investigation, name='crawled_urls_investigation'),
    path('investigate-alert/<int:alert_id>/', views.investigate_alert, name='investigate_alert'),
    path('mark-alert-read/<int:alert_id>/', views.mark_alert_read, name='mark_alert_read'),
    path('resolve-alert/<int:alert_id>/', views.resolve_alert, name='resolve_alert'),
    path('database-status/', views.database_status, name='database_status'),
    path('telegram/links/', views.telegram_links_dashboard, name='telegram_links_dashboard'),
    path('telegram/channels/add/', views.add_telegram_channel, name='add_telegram_channel'),
    path('telegram/channels/<int:channel_id>/toggle/', views.toggle_channel_monitoring, name='toggle_channel_monitoring'),
    path('telegram/channels/<int:channel_id>/remove/', views.remove_telegram_channel, name='remove_telegram_channel'),
    path('telegram/process-links/', views.process_telegram_links_view, name='process_telegram_links_view'),
    path('telegram/crawl-channels/', views.crawl_telegram_channels, name='crawl_telegram_channels'),
    path('telegram/channels/<int:channel_id>/scrape/', views.scrape_telegram_channel, name='scrape_telegram_channel'),
    path('telegram/channels/<int:channel_id>/progress/', views.get_scraping_progress, name='get_scraping_progress'),
    
    # OpenSearch API endpoints
    path('api/search/credentials/', views.search_credentials, name='search_credentials'),
    path('api/search/analytics/', views.get_search_analytics, name='get_search_analytics'),
    path('api/search/bulk-index/', views.bulk_index_existing_data, name='bulk_index_existing_data'),
    path('api/alerts/', views.get_alerts, name='get_alerts'),
    path('api/alerts/<int:alert_id>/update/', views.update_alert_status, name='update_alert_status'),
]
