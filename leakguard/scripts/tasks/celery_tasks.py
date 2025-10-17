"""
Celery tasks for LeakGuard real-time processing
Handles background processing of Telegram data and credential matching
"""

import os
import sys
import django
from celery import Celery
from celery.schedules import crontab
import logging

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from django.contrib.auth.models import User
from scripts.matching.credential_matcher import CredentialMatcher
from scripts.telegram.telegram_integrated_scraper import IntegratedTelegramScraper
from scripts.data_processing.telegram_data_extractor import TelegramDataExtractor

logger = logging.getLogger(__name__)

# Celery app configuration
app = Celery('leakguard')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks
app.autodiscover_tasks()

@app.task(bind=True, max_retries=3)
def process_new_telegram_data(self):
    """Process new Telegram data and extract indicators"""
    try:
        logger.info("Starting Telegram data processing task")
        
        # Initialize data extractor
        extractor = TelegramDataExtractor()
        
        # Process recent messages (last 100 messages)
        extractor.process_telegram_messages(limit=100)
        
        logger.info("Telegram data processing completed successfully")
        return "Telegram data processing completed"
        
    except Exception as e:
        logger.error(f"Error in process_new_telegram_data: {e}")
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries))

@app.task(bind=True, max_retries=3)
def match_credentials_for_all_users(self):
    """Match credentials for all active users"""
    try:
        logger.info("Starting credential matching task for all users")
        
        # Get all users with monitored credentials
        users = User.objects.filter(
            api_monitored_credentials__is_active=True
        ).distinct()
        
        matcher = CredentialMatcher()
        total_alerts = 0
        
        for user in users:
            try:
                alerts_created = matcher.process_matches_for_user(user.id, hours_back=24)
                total_alerts += alerts_created
                logger.info(f"Created {alerts_created} alerts for user {user.username}")
            except Exception as e:
                logger.error(f"Error processing matches for user {user.id}: {e}")
                continue
        
        logger.info(f"Credential matching completed. Total alerts created: {total_alerts}")
        return f"Credential matching completed. Total alerts: {total_alerts}"
        
    except Exception as e:
        logger.error(f"Error in match_credentials_for_all_users: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))

@app.task(bind=True, max_retries=3)
def match_credentials_for_user(self, user_id: int):
    """Match credentials for a specific user"""
    try:
        logger.info(f"Starting credential matching task for user {user_id}")
        
        matcher = CredentialMatcher()
        alerts_created = matcher.process_matches_for_user(user_id, hours_back=24)
        
        logger.info(f"Credential matching completed for user {user_id}. Alerts created: {alerts_created}")
        return f"Alerts created: {alerts_created}"
        
    except Exception as e:
        logger.error(f"Error in match_credentials_for_user: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))

@app.task(bind=True, max_retries=3)
def run_telegram_scraper(self, channels: list = None):
    """Run Telegram scraper for specified channels"""
    try:
        logger.info("Starting Telegram scraper task")
        
        from scripts.telegram.automated_telegram_scraper import run_automated_scraping_sync
        
        # Use the automated scraper
        run_automated_scraping_sync(channels)
        
        logger.info("Telegram scraper task completed")
        return "Telegram scraper completed"
        
    except Exception as e:
        logger.error(f"Error in run_telegram_scraper: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))

@app.task(bind=True, max_retries=3)
def cleanup_old_data(self, days_old: int = 30):
    """Clean up old data and files"""
    try:
        logger.info(f"Starting cleanup task for data older than {days_old} days")
        
        from datetime import datetime, timedelta
        from api.models import Alert, CredentialLeak
        from scripts.storage.minio_client import LeakGuardMinioClient
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Clean up old resolved alerts
        old_alerts = Alert.objects.filter(
            is_resolved=True,
            resolved_at__lt=cutoff_date
        )
        alerts_deleted = old_alerts.count()
        old_alerts.delete()
        
        # Clean up old false positive credential leaks
        old_leaks = CredentialLeak.objects.filter(
            status='false_positive',
            discovered_at__lt=cutoff_date
        )
        leaks_deleted = old_leaks.count()
        old_leaks.delete()
        
        logger.info(f"Cleanup completed. Deleted {alerts_deleted} alerts and {leaks_deleted} leaks")
        return f"Cleanup completed. Deleted {alerts_deleted} alerts and {leaks_deleted} leaks"
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_data: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))

@app.task(bind=True, max_retries=3)
def send_alert_notifications(self):
    """Send pending alert notifications"""
    try:
        logger.info("Starting alert notification task")
        
        from api.models import Alert
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Get unread alerts that haven't had email sent
        pending_alerts = Alert.objects.filter(
            is_read=False,
            email_sent=False,
            created_at__gte=datetime.now() - timedelta(hours=24)
        )
        
        notifications_sent = 0
        
        for alert in pending_alerts:
            try:
                # Send email notification
                subject = f"LeakGuard Alert: {alert.title}"
                message = f"""
                Alert: {alert.title}
                
                Message: {alert.message}
                
                Priority: {alert.priority}
                Created: {alert.created_at}
                
                Please log in to your LeakGuard dashboard to investigate this alert.
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [alert.user.email],
                    fail_silently=False,
                )
                
                alert.email_sent = True
                alert.save()
                notifications_sent += 1
                
            except Exception as e:
                logger.error(f"Error sending notification for alert {alert.id}: {e}")
                continue
        
        logger.info(f"Alert notification task completed. Sent {notifications_sent} notifications")
        return f"Sent {notifications_sent} notifications"
        
    except Exception as e:
        logger.error(f"Error in send_alert_notifications: {e}")
        raise self.retry(countdown=60 * (2 ** self.request.retries))

# Celery Beat schedule configuration
app.conf.beat_schedule = {
    'process-telegram-data': {
        'task': 'scripts.tasks.celery_tasks.process_new_telegram_data',
        'schedule': 300.0,  # Every 5 minutes
    },
    'match-credentials': {
        'task': 'scripts.tasks.celery_tasks.match_credentials_for_all_users',
        'schedule': 600.0,  # Every 10 minutes
    },
    'run-telegram-scraper': {
        'task': 'scripts.tasks.celery_tasks.run_telegram_scraper',
        'schedule': 1800.0,  # Every 30 minutes
    },
    'send-alert-notifications': {
        'task': 'scripts.tasks.celery_tasks.send_alert_notifications',
        'schedule': 300.0,  # Every 5 minutes
    },
    'cleanup-old-data': {
        'task': 'scripts.tasks.celery_tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}

app.conf.timezone = 'UTC'

@app.task
def test_task():
    """Test task to verify Celery is working"""
    return "Celery is working correctly!"
