from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.db import models
from datetime import datetime, timedelta
# from .documents import CredentialLeakDocument, MonitoredCredentialDocument  # Disabled - requires OpenSearch

from .models import *
from .forms import CreateUserForm, MonitoredCredentialForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def registerPage(request):
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Account was created for {user.username}! You can now log in.")
            return redirect('login')
    else:
        form = CreateUserForm()

    return render(request, 'register.html', {"form": form})


def loginPage(request):

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')

    context = {}
    return render(request, 'login.html', context)

@login_required
def dashboard(request):
    from api.models import Alert
    
    # Get monitored credentials
    rows = []
    for mc in MonitoredCredential.objects.filter(owner=request.user):
        if mc.email:
            rows.append({"cred_type": "email", "value": mc.email})
        if mc.username:
            rows.append({"cred_type": "username", "value": mc.username})
        if mc.domain:
            rows.append({"cred_type": "domain", "value": mc.domain})

    # Get recent alerts
    alerts = Alert.objects.filter(user=request.user).order_by('-created_at')[:10]
    new_alerts_count = Alert.objects.filter(user=request.user, is_read=False).count()
    
    # Get monitored channels (active Telegram channels)
    monitored_channels = TelegramChannel.objects.filter(is_active=True).order_by('-created_at')
    monitored_sources_count = monitored_channels.count()
    
    # Get recent data leaks
    recent_leaks = DataLeak.objects.order_by('-created_at')[:5]
    total_leaks = DataLeak.objects.count()
    
    # Get recent messages
    recent_messages = TelegramMessage.objects.order_by('-created_at')[:5]
    total_messages = TelegramMessage.objects.count()

    context = {
        "monitored_credentials": rows,
        "alerts": alerts,
        "new_alerts_count": new_alerts_count,
        "monitored_channels": monitored_channels,
        "monitored_sources_count": monitored_sources_count,
        "recent_leaks": recent_leaks,
        "total_leaks": total_leaks,
        "recent_messages": recent_messages,
        "total_messages": total_messages,
    }
    return render(request, 'dashboard.html', context)


@login_required
@require_POST
def add_monitored_credential(request):

    cred_type = (request.POST.get("cred_type") or "").strip()
    value = (request.POST.get("value") or "").strip()

    if not cred_type or not value:
        messages.error(request, "Please choose a type and enter a value.")
        return redirect('dashboard')
    
    try:
        if cred_type == "email":
            obj, created = MonitoredCredential.objects.get_or_create(
                owner=request.user, email=value
            )
        elif cred_type == "username":
            obj, created = MonitoredCredential.objects.get_or_create(
                owner=request.user, username=value
            )
        elif cred_type == "domain":
            obj, created = MonitoredCredential.objects.get_or_create(
                owner=request.user, domain=value.lower()
            )
        else:
            messages.error(request, "Unknown credential type.")
            return redirect("dashboard")
    except Exception:
        messages.error(request, "Could not save credential.")
        return redirect("dashboard")

    if created:
        messages.success(request, "Credential added and will be monitored.")
    else:
        messages.info(request, "That credential is already being monitored.")
    return redirect("dashboard")

@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')

# Alert Service Functions
def send_alert_email(user_email, alert_data):
    """Send email notification for alerts"""
    try:
        subject = f"Data Leak Alert: {alert_data['title']}"
        
        # Create HTML message
        html_message = f"""
        <html>
        <body>
            <h2>Data Leak Alert</h2>
            <div style="border: 1px solid #ddd; padding: 20px; border-radius: 5px;">
                <h3>{alert_data['title']}</h3>
                <p>{alert_data['message']}</p>
                <p><strong>Severity:</strong> {alert_data['severity']}</p>
                <p><strong>Date:</strong> {alert_data['created_at']}</p>
            </div>
            <p>Please take necessary actions to secure your account and change your credentials if needed.</p>
            <p>If you have any questions or concerns, please contact our support team.</p>
        </body>
        </html>
        """
        
        # Create plain text message
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send email notification: {str(e)}")
        return False

def create_alert(user, title, message, alert_type='leak_detected', priority='medium', credential_leak=None):
    """Create an alert and send email notification"""
    from api.models import Alert
    
    # Create alert
    alert = Alert.objects.create(
        user=user,
        alert_type=alert_type,
        title=title,
        message=message,
        priority=priority,
        credential_leak=credential_leak
    )
    
    # Send email notification
    alert_data = {
        'title': title,
        'message': message,
        'severity': priority,
        'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }
    send_alert_email(user.email, alert_data)
    
    return alert

@login_required
def demo_leak_detection(request):
    """Demo view to simulate data leak detection"""
    if request.method == 'POST':
        leak_type = request.POST.get('leak_type', 'email')
        
        # Create a demo data leak
        if leak_type == 'email':
            data_leak = DataLeak.objects.create(
                email=request.user.email,
                source='Demo Email Leak',
                severity='high',
                raw_data=f'Demo email leak for {request.user.email}',
                is_processed=True
            )
            title = "Email Leak Detected"
            message = f"Your email address ({request.user.email}) was found in a recent data breach from 'Demo Email Leak'."
            priority = 'high'
            
        elif leak_type == 'password':
            data_leak = DataLeak.objects.create(
                email=request.user.email,
                password='demo_password_123',
                source='Demo Password Leak',
                severity='critical',
                raw_data=f'Demo password leak for {request.user.email}',
                is_processed=True
            )
            title = "Password Leak Detected"
            message = f"Your password was found in a recent data breach from 'Demo Password Leak'. Please change your password immediately."
            priority = 'critical'
            
        else:  # general
            data_leak = DataLeak.objects.create(
                email=request.user.email,
                source='Demo General Leak',
                severity='medium',
                raw_data=f'Demo general leak for {request.user.email}',
                is_processed=True
            )
            title = "General Data Leak Detected"
            message = f"Your information was found in a recent data breach from 'Demo General Leak'."
            priority = 'medium'
        
        # Create alert
        create_alert(
            user=request.user,
            title=title,
            message=message,
            priority=priority
        )
        
        messages.success(request, f'Demo {leak_type} leak created successfully! Check your email for notification.')
        return redirect('dashboard')
    
    return render(request, 'demo.html')

@login_required
def get_alerts(request):
    """API endpoint to get user's alerts"""
    from api.models import Alert
    
    alerts = Alert.objects.filter(user=request.user).order_by('-created_at')
    alerts_data = [{
        'id': alert.id,
        'title': alert.title,
        'message': alert.message,
        'alert_type': alert.alert_type,
        'priority': alert.priority,
        'is_read': alert.is_read,
        'is_resolved': alert.is_resolved,
        'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    } for alert in alerts]
    
    return JsonResponse({'alerts': alerts_data})

@login_required
def update_alert_status(request, alert_id):
    """API endpoint to update alert status"""
    from api.models import Alert
    
    try:
        alert = Alert.objects.get(id=alert_id, user=request.user)
        new_status = request.POST.get('status')
        
        if new_status == 'read':
            alert.is_read = True
        elif new_status == 'resolved':
            alert.is_resolved = True
        
        alert.save()
        return JsonResponse({'status': 'success'})
        
    except Alert.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Alert not found'}, status=404)

@login_required
def telegram_monitor(request):
    """View for managing Telegram channel monitoring"""
    if request.method == 'POST':
        telegram_url = request.POST.get('telegram_url', '').strip()
        
        if telegram_url:
            # Extract channel username from URL
            import re
            username_match = re.search(r't\.me/([a-zA-Z0-9_]+)', telegram_url)
            if username_match:
                username = username_match.group(1)
                
                # Create or get Telegram channel
                channel, created = TelegramChannel.objects.get_or_create(
                    username=username,
                    defaults={
                        'name': username,
                        'url': telegram_url,
                        'description': f'Channel added by {request.user.username}',
                        'is_active': True
                    }
                )
                
                if created:
                    messages.success(request, f'Successfully added Telegram channel: @{username}')
                else:
                    messages.info(request, f'Channel @{username} is already being monitored')
            else:
                messages.error(request, 'Invalid Telegram URL format. Please use format: https://t.me/username')
        else:
            messages.error(request, 'Please enter a Telegram URL')
    
    # Get all monitored channels
    channels = TelegramChannel.objects.filter(is_active=True).order_by('-created_at')
    
    context = {
        'channels': channels
    }
    return render(request, 'telegram_monitor.html', context)

@login_required
def process_telegram_data(request):
    """Process Telegram data and create alerts for found credentials"""
    from scripts.matching.credential_matcher import CredentialMatcher
    
    if request.method == 'POST':
        # Use the enhanced credential matcher
        matcher = CredentialMatcher()
        alerts_created = matcher.process_matches_for_user(request.user.id, hours_back=24)
        
        if alerts_created > 0:
            messages.success(request, f'Processed Telegram data and created {alerts_created} alerts!')
        else:
            messages.info(request, 'No matching credentials found in recent Telegram messages.')
    
    return redirect('telegram_monitor')

@login_required
def investigate_alert(request, alert_id):
    """Allow users to investigate alerts by fetching raw files from MinIO"""
    from api.models import Alert
    from scripts.storage.minio_client import LeakGuardMinioClient
    
    alert = get_object_or_404(Alert, id=alert_id, user=request.user)
    
    raw_file_url = None
    source_document = None
    
    if alert.credential_leak and alert.credential_leak.metadata:
        try:
            minio_client = LeakGuardMinioClient()
            metadata = alert.credential_leak.metadata
            
            channel_id = metadata.get('channel_id')
            message_id = metadata.get('message_id')
            
            if channel_id and message_id:
                # Get presigned URL for raw message file
                raw_file_url = minio_client.get_telegram_message_url(
                    channel_id=channel_id,
                    message_id=message_id,
                    expires_in_seconds=3600
                )
                
                # Get source document from OpenSearch
                from config.opensearch_config import OPENSEARCH_CONFIG
                from opensearchpy import OpenSearch
                
                opensearch_client = OpenSearch(**OPENSEARCH_CONFIG)
                query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"channel_id": channel_id}},
                                {"term": {"message_id": message_id}}
                            ]
                        }
                    }
                }
                
                results = opensearch_client.search(
                    index="telegram-extracted-data",
                    body=query,
                    size=1
                )
                
                if results['hits']['hits']:
                    source_document = results['hits']['hits'][0]['_source']
                    
        except Exception as e:
            messages.error(request, f'Error accessing raw data: {str(e)}')
    
    context = {
        'alert': alert,
        'raw_file_url': raw_file_url,
        'source_document': source_document
    }
    return render(request, 'investigate_alert.html', context)

@login_required
@require_POST
def mark_alert_read(request, alert_id):
    """Mark an alert as read"""
    from api.models import Alert
    
    alert = get_object_or_404(Alert, id=alert_id, user=request.user)
    alert.is_read = True
    alert.read_at = timezone.now()
    alert.save()
    
    messages.success(request, 'Alert marked as read.')
    return redirect('investigate_alert', alert_id=alert_id)

@login_required
@require_POST
def resolve_alert(request, alert_id):
    """Resolve an alert"""
    from api.models import Alert
    
    alert = get_object_or_404(Alert, id=alert_id, user=request.user)
    resolution = request.POST.get('resolution', 'resolved')
    
    alert.is_resolved = True
    alert.resolved_at = timezone.now()
    
    if alert.credential_leak:
        alert.credential_leak.status = resolution
        alert.credential_leak.save()
    
    alert.save()
    
    messages.success(request, f'Alert marked as {resolution}.')
    return redirect('investigate_alert', alert_id=alert_id)

@login_required
def demo_telegram_collection(request):
    """Demo view to simulate Telegram data collection"""
    if request.method == 'POST':
        # Create some demo Telegram messages with credentials
        demo_channels = [
            {'username': 'demo_leaks', 'name': 'Demo Leaks Channel', 'url': 'https://t.me/demo_leaks'},
            {'username': 'test_breach', 'name': 'Test Breach Channel', 'url': 'https://t.me/test_breach'},
        ]
        
        demo_messages = [
            {
                'text': f'user@example.com:password123\nadmin@test.com:admin123\n{request.user.email}:demo_password',
                'channel_username': 'demo_leaks'
            },
            {
                'text': f'john.doe@company.com:secret123\n{request.user.email}:leaked_password\nuser@domain.com:password456',
                'channel_username': 'test_breach'
            }
        ]
        
        # Create demo channels
        for channel_data in demo_channels:
            channel, created = TelegramChannel.objects.get_or_create(
                username=channel_data['username'],
                defaults={
                    'name': channel_data['name'],
                    'url': channel_data['url'],
                    'description': 'Demo channel for testing',
                    'is_active': True
                }
            )
        
        # Create demo messages
        for i, msg_data in enumerate(demo_messages):
            channel = TelegramChannel.objects.get(username=msg_data['channel_username'])
            # Use get_or_create to avoid duplicate constraint errors
            TelegramMessage.objects.get_or_create(
                channel=channel,
                message_id=12345 + i,  # Use different message IDs
                defaults={
                    'text': msg_data['text'],
                    'date': datetime.now(),
                    'sender_username': 'demo_user'
                }
            )
        
        messages.success(request, 'Demo Telegram data created! Now process the data to see alerts.')
        return redirect('telegram_monitor')
    
    return render(request, 'demo_telegram.html')

@login_required
def auto_telegram_collection(request):
    """Automated Telegram collection from GitHub"""
    if request.method == 'POST':
        try:
            # Import the automation components
            import sys
            import os
            from datetime import datetime
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            from scripts.telegram.telegram_automation import GitHubLinkExtractor, TelegramCollector, TelegramConfig
            from scripts.storage.opensearch_url_service import OpenSearchURLService
            from socradar.models import CrawledURL
            
            # Get Telegram credentials from settings or environment
            api_id = getattr(settings, 'TELEGRAM_API_ID', None) or os.getenv('TELEGRAM_API_ID')
            api_hash = getattr(settings, 'TELEGRAM_API_HASH', None) or os.getenv('TELEGRAM_API_HASH')
            phone_number = getattr(settings, 'TELEGRAM_PHONE', None) or os.getenv('TELEGRAM_PHONE')
            
            if not all([api_id, api_hash, phone_number]):
                messages.error(request, 'Telegram API credentials not configured. Please set TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_PHONE in settings.')
                return redirect('telegram_monitor')
            
            # Step 1: Extract Telegram links from GitHub
            extractor = GitHubLinkExtractor()
            telegram_links = extractor.fetch_telegram_links()
            
            if not telegram_links:
                messages.warning(request, 'No Telegram links found on GitHub page.')
                return redirect('telegram_monitor')
            
            # Step 2: Validate links to check if they are active
            from scripts.telegram.telegram_link_validator import validate_telegram_links
            import asyncio
            
            # Run validation in async context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                validated_links = loop.run_until_complete(
                    validate_telegram_links(telegram_links, int(api_id), api_hash, phone_number)
                )
            finally:
                loop.close()
            
            if not validated_links:
                messages.warning(request, 'No active Telegram links found after validation.')
                return redirect('telegram_monitor')
            
            # Generate unique crawl session ID
            crawl_session_id = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Step 3: Save validated URLs to OpenSearch
            opensearch_service = OpenSearchURLService()
            opensearch_success = opensearch_service.save_crawled_urls(validated_links, crawl_session_id)
            
            # Step 4: Save validated URLs to Django database
            django_urls_saved = 0
            for link in validated_links:
                crawled_url, created = CrawledURL.objects.get_or_create(
                    username=link['username'],
                    crawl_session_id=crawl_session_id,
                    defaults={
                        'url': link['url'],
                        'channel_name': link.get('channel_name', link['username']),
                        'source': link.get('source', 'github'),
                        'source_url': link.get('source_url', ''),
                        'description': link.get('description', f'Auto-crawled from {link.get("source", "github")}'),
                        'metadata': link.get('metadata', {}),
                        'is_active': True
                    }
                )
                if created:
                    django_urls_saved += 1
            
            # Step 5: Add channels to TelegramChannel database
            channels_added = 0
            for link in validated_links:
                channel, created = TelegramChannel.objects.get_or_create(
                    username=link['username'],
                    defaults={
                        'name': link.get('title', link['username']),
                        'url': link['url'],
                        'description': link.get('description', f'Auto-added from {link["source"]}'),
                        'is_active': True
                    }
                )
                if created:
                    channels_added += 1
                    
                    # Save channel to OpenSearch as well
                    channel_data = {
                        'id': channel.id,
                        'name': channel.name,
                        'username': channel.username,
                        'url': channel.url,
                        'description': channel.description,
                        'is_active': channel.is_active,
                        'created_at': channel.created_at.isoformat() if channel.created_at else None,
                        'updated_at': channel.updated_at.isoformat() if channel.updated_at else None,
                        'last_scanned': channel.last_scanned.isoformat() if channel.last_scanned else None,
                        'crawl_session_id': crawl_session_id
                    }
                    opensearch_service.save_telegram_channel(channel_data)
            
            # Prepare success message with validation info
            total_found = len(telegram_links)
            active_found = len(validated_links)
            inactive_count = total_found - active_found
            
            success_parts = []
            if opensearch_success:
                success_parts.append(f"Saved {active_found} active URLs to OpenSearch")
            if django_urls_saved > 0:
                success_parts.append(f"Saved {django_urls_saved} URLs to Django database")
            if channels_added > 0:
                success_parts.append(f"Added {channels_added} new Telegram channels")
            
            if success_parts:
                message = f'Successfully completed auto-collection! {". ".join(success_parts)}.'
                if inactive_count > 0:
                    message += f" ({inactive_count} inactive/expired links were filtered out.)"
                messages.success(request, message)
            else:
                messages.info(request, 'Auto-collection completed. All URLs were already in the database.')
            
            # Step 5: Start Telegram collection (this would run in background)
            # For demo purposes, we'll just show the channels were added
            # In production, you'd want to run this as a background task
            
        except Exception as e:
            messages.error(request, f'Error during automated collection: {str(e)}')
            import traceback
            print(f"Auto collection error: {traceback.format_exc()}")
    
    return redirect('telegram_monitor')

@login_required
def crawled_urls_investigation(request):
    """Display crawled URLs for investigation purposes"""
    from socradar.models import CrawledURL
    from scripts.storage.opensearch_url_service import OpenSearchURLService
    
    # Get crawled URLs from Django database
    crawled_urls = CrawledURL.objects.all().order_by('-crawled_at')
    
    # Get additional data from OpenSearch if available
    opensearch_urls = []
    try:
        opensearch_service = OpenSearchURLService()
        opensearch_urls = opensearch_service.get_crawled_urls(limit=100)
    except Exception as e:
        print(f"Could not fetch OpenSearch data: {e}")
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        crawled_urls = crawled_urls.filter(
            models.Q(username__icontains=search_query) |
            models.Q(channel_name__icontains=search_query) |
            models.Q(description__icontains=search_query)
        )
    
    # Filter by leak status
    leak_filter = request.GET.get('leak_filter', '')
    if leak_filter == 'with_leaks':
        crawled_urls = crawled_urls.filter(credential_leaks_found=True)
    elif leak_filter == 'without_leaks':
        crawled_urls = crawled_urls.filter(credential_leaks_found=False)
    
    context = {
        'crawled_urls': crawled_urls,
        'opensearch_urls': opensearch_urls,
        'search_query': search_query,
        'leak_filter': leak_filter,
        'total_urls': crawled_urls.count(),
        'urls_with_leaks': crawled_urls.filter(credential_leaks_found=True).count(),
    }
    
    return render(request, 'crawled_urls_investigation.html', context)

@login_required
def start_telegram_scraping(request):
    """Start the Telegram scraping process"""
    if request.method == 'POST':
        try:
            # Import the automated scraper
            from scripts.telegram.automated_telegram_scraper import run_automated_scraping_sync
            from scripts.tasks.celery_tasks import run_telegram_scraper
            
            # Get active channels
            active_channels = TelegramChannel.objects.filter(is_active=True)
            
            if not active_channels.exists():
                messages.warning(request, 'No active channels to scrape. Add some channels first.')
                return redirect('telegram_monitor')
            
            # Get channel usernames for scraping
            channel_usernames = list(active_channels.values_list('username', flat=True))
            
            # Start scraping as a background task
            try:
                # Try to run as Celery task first
                task = run_telegram_scraper.delay(channel_usernames)
                messages.success(request, f'Started scraping {len(channel_usernames)} channels as background task. Task ID: {task.id}')
            except Exception as celery_error:
                # Fallback to synchronous scraping if Celery is not available
                messages.info(request, 'Running scraping synchronously (Celery not available)')
                
                try:
                    # Use the automated scraper (limit to 5 channels for synchronous operation)
                    limited_channels = channel_usernames[:5]
                    run_automated_scraping_sync(limited_channels)
                    messages.success(request, f'Successfully scraped {len(limited_channels)} channels!')
                except Exception as scraping_error:
                    messages.error(request, f'Error during scraping: {str(scraping_error)}')
            
        except Exception as e:
            messages.error(request, f'Error during scraping: {str(e)}')
    
    return redirect('telegram_monitor')

@login_required
def database_status(request):
    """View to show database status and scraped data"""
    from api.models import Alert
    
    # Get statistics
    total_channels = TelegramChannel.objects.count()
    active_channels = TelegramChannel.objects.filter(is_active=True).count()
    total_messages = TelegramMessage.objects.count()
    total_data_leaks = DataLeak.objects.count()
    total_alerts = Alert.objects.filter(user=request.user).count()
    
    # Get recent data
    recent_channels = TelegramChannel.objects.order_by('-created_at')[:10]
    recent_messages = TelegramMessage.objects.order_by('-created_at')[:10]
    recent_leaks = DataLeak.objects.order_by('-created_at')[:10]
    
    context = {
        'total_channels': total_channels,
        'active_channels': active_channels,
        'total_messages': total_messages,
        'total_data_leaks': total_data_leaks,
        'total_alerts': total_alerts,
        'recent_channels': recent_channels,
        'recent_messages': recent_messages,
        'recent_leaks': recent_leaks,
    }
    
    return render(request, 'database_status.html', context)   
