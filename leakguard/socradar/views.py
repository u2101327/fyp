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
    
    # Get monitored credentials using the new model structure
    monitored_credentials = MonitoredCredential.objects.filter(owner=request.user, is_active=True).order_by('-created_at')
    
    # Convert to the format expected by the template (for backward compatibility)
    rows = []
    for mc in monitored_credentials:
        rows.append({
            "cred_type": mc.credential_type, 
            "value": mc.display_value,
            "priority": mc.priority,
            "description": mc.description,
            "created_at": mc.created_at,
            "tags": mc.tags
        })

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
    # Get form data
    target_type = (request.POST.get("targetType") or "").strip()
    target_value = (request.POST.get("targetValue") or "").strip()
    priority = (request.POST.get("priority") or "medium").strip()
    description = (request.POST.get("description") or "").strip()
    sources = request.POST.getlist("sources")  # Get list of selected sources
    
    # Validate required fields
    if not target_type or not target_value:
        messages.error(request, "Please choose a type and enter a value.")
        return redirect('dashboard')
    
    # Validate credential type
    valid_types = ['email', 'username', 'domain', 'custom']
    if target_type not in valid_types:
        messages.error(request, "Invalid credential type.")
        return redirect('dashboard')
    
    try:
        # Create the credential object with the new model structure
        credential_data = {
            'owner': request.user,
            'credential_type': target_type,
            'priority': priority,
            'description': description,
            'is_active': True,
            'tags': sources  # Store selected sources as tags
        }
        
        # Set the appropriate field based on credential type
        if target_type == "email":
            credential_data['email'] = target_value.lower()
            # Check for existing email
            existing = MonitoredCredential.objects.filter(owner=request.user, email=target_value.lower()).first()
        elif target_type == "username":
            credential_data['username'] = target_value
            existing = MonitoredCredential.objects.filter(owner=request.user, username=target_value).first()
        elif target_type == "domain":
            credential_data['domain'] = target_value.lower()
            existing = MonitoredCredential.objects.filter(owner=request.user, domain=target_value.lower()).first()        
        elif target_type == "custom":
            credential_data['custom_value'] = target_value
            existing = MonitoredCredential.objects.filter(owner=request.user, custom_value=target_value).first()
        
        # Check if credential already exists
        if existing:
            messages.info(request, f"That {target_type} is already being monitored.")
            return redirect("dashboard")
        
        # Create new credential
        obj = MonitoredCredential.objects.create(**credential_data)
        messages.success(request, f"{target_type.title()} credential added and will be monitored.")
        
    except Exception as e:
        messages.error(request, f"Could not save credential: {str(e)}")
        return redirect("dashboard")

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

@login_required
def telegram_links_dashboard(request):
    """Dashboard for monitoring Telegram links"""
    from .models import TelegramLink, TelegramChannel, TelegramMessage
    from .utils import get_link_statistics
    
    # Get filter parameters
    channel_filter = request.GET.get('channel')
    status_filter = request.GET.get('status')
    suspicious_filter = request.GET.get('suspicious')
    channel_status_filter = request.GET.get('channel_status', 'all')  # New filter for channel status
    
    # Build queryset
    links = TelegramLink.objects.select_related('message', 'channel').all()
    
    if channel_filter:
        links = links.filter(channel__username=channel_filter)
    
    if status_filter:
        links = links.filter(validation_status=status_filter)
    
    if suspicious_filter == 'true':
        links = links.filter(is_suspicious=True)
    
    # Get recent links (last 100)
    recent_links = links.order_by('-created_at')[:100]
    
    # Get statistics
    stats = get_link_statistics()
    
    # Get channel list for filter
    channels = TelegramChannel.objects.filter(is_active=True).order_by('username')
    
    # Get status choices
    status_choices = TelegramLink.VALIDATION_STATUS_CHOICES
    
    # Get all channels and apply status filter
    all_channels = TelegramChannel.objects.all().order_by('-created_at')
    
    # Apply channel status filter
    if channel_status_filter == 'active':
        filtered_channels = all_channels.filter(validation_status='PUBLIC_OK')
    elif channel_status_filter == 'inactive':
        filtered_channels = all_channels.exclude(validation_status='PUBLIC_OK')
    elif channel_status_filter == 'not_found':
        filtered_channels = all_channels.filter(validation_status='NOT_FOUND')
    elif channel_status_filter == 'auth_error':
        filtered_channels = all_channels.filter(validation_status__in=['AUTH_ERROR', 'AUTH_TIMEOUT'])
    elif channel_status_filter == 'api_error':
        filtered_channels = all_channels.filter(validation_status__in=['RPC_ERROR', 'ERROR'])
    elif channel_status_filter == 'no_api':
        filtered_channels = all_channels.filter(validation_status='NO_API_CREDENTIALS')
    elif channel_status_filter == 'pending':
        filtered_channels = all_channels.filter(validation_status='PENDING')
    else:  # 'all'
        filtered_channels = all_channels
    
    # Get recent alerts data (from TelegramLink with high risk scores)
    recent_alerts = TelegramLink.objects.filter(
        is_suspicious=True
    ).select_related('message', 'channel').order_by('-created_at')[:10]
    
    # Get monitored keywords (from your existing system)
    from api.models import MonitoredCredential
    monitored_keywords = MonitoredCredential.objects.filter(
        user=request.user, 
        is_active=True
    ).values_list('value', flat=True)[:10]
    
    # Get processed files for display
    from .models import ProcessedFile
    processed_files = ProcessedFile.objects.select_related('message__channel').order_by('-processed_at')[:20]
    
    context = {
        'recent_links': recent_links,
        'stats': stats,
        'channels': channels,
        'status_choices': status_choices,
        'all_channels': filtered_channels,
        'recent_alerts': recent_alerts,
        'monitored_keywords': list(monitored_keywords),
        'processed_files': processed_files,
        'current_filters': {
            'channel': channel_filter,
            'status': status_filter,
            'suspicious': suspicious_filter,
            'channel_status': channel_status_filter,
        }
    }
    
    return render(request, 'telegram_links_dashboard.html', context)


@login_required
def search_credentials(request):
    """Search credentials using OpenSearch"""
    from .opensearch_client import get_opensearch_client
    from django.http import JsonResponse
    
    try:
        # Get search parameters
        query = request.GET.get('q', '').strip()
        domain = request.GET.get('domain', '').strip()
        risk_level = request.GET.get('risk_level', '').strip()
        channel = request.GET.get('channel', '').strip()
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('size', 20))
        
        # Build filters
        filters = {}
        if domain:
            filters['domain'] = domain
        if risk_level:
            filters['risk_level'] = risk_level
        if channel:
            filters['channel_username'] = channel
        
        # Calculate pagination
        from_ = (page - 1) * size
        
        # Search using OpenSearch
        opensearch_client = get_opensearch_client()
        
        if not opensearch_client.is_available():
            return JsonResponse({
                'error': 'OpenSearch not available',
                'results': [],
                'total': 0,
                'page': page,
                'size': size
            })
        
        # Perform search
        results = opensearch_client.search_credentials(
            query=query,
            filters=filters,
            size=size,
            from_=from_
        )
        
        if 'error' in results:
            return JsonResponse({
                'error': results['error'],
                'results': [],
                'total': 0,
                'page': page,
                'size': size
            })
        
        return JsonResponse({
            'results': results['hits'],
            'total': results['total'],
            'page': page,
            'size': size,
            'query': query,
            'filters': filters
        })
        
    except Exception as e:
        logger.error(f"Error in search_credentials: {e}")
        return JsonResponse({
            'error': str(e),
            'results': [],
            'total': 0,
            'page': page,
            'size': size
        })


@login_required
def get_search_analytics(request):
    """Get search analytics and aggregations"""
    from .opensearch_client import get_opensearch_client
    from django.http import JsonResponse
    
    try:
        opensearch_client = get_opensearch_client()
        
        if not opensearch_client.is_available():
            return JsonResponse({
                'error': 'OpenSearch not available',
                'analytics': {}
            })
        
        # Get aggregations
        analytics = opensearch_client.get_aggregations()
        
        if 'error' in analytics:
            return JsonResponse({
                'error': analytics['error'],
                'analytics': {}
            })
        
        return JsonResponse({
            'analytics': analytics
        })
        
    except Exception as e:
        logger.error(f"Error in get_search_analytics: {e}")
        return JsonResponse({
            'error': str(e),
            'analytics': {}
        })


@login_required
def bulk_index_existing_data(request):
    """Bulk index existing credentials to OpenSearch"""
    from .opensearch_client import get_opensearch_client
    from .models import ExtractedCredential
    from django.http import JsonResponse
    
    try:
        opensearch_client = get_opensearch_client()
        
        if not opensearch_client.is_available():
            return JsonResponse({
                'error': 'OpenSearch not available'
            })
        
        # Get all credential IDs
        credential_ids = list(ExtractedCredential.objects.values_list('id', flat=True))
        
        if not credential_ids:
            return JsonResponse({
                'message': 'No credentials to index',
                'indexed': 0
            })
        
        # Bulk index in batches
        batch_size = 1000
        total_indexed = 0
        
        for i in range(0, len(credential_ids), batch_size):
            batch_ids = credential_ids[i:i + batch_size]
            result = opensearch_client.bulk_index_credentials(batch_ids)
            
            if result.get('success'):
                total_indexed += result.get('indexed', 0)
            else:
                return JsonResponse({
                    'error': f"Failed to index batch: {result.get('error')}",
                    'indexed': total_indexed
                })
        
        return JsonResponse({
            'message': f'Successfully indexed {total_indexed} credentials',
            'indexed': total_indexed,
            'total': len(credential_ids)
        })
        
    except Exception as e:
        logger.error(f"Error in bulk_index_existing_data: {e}")
        return JsonResponse({
            'error': str(e)
        })

@login_required
@require_POST
def add_telegram_channel(request):
    """Add a new Telegram channel for monitoring"""
    from .models import TelegramChannel
    from .utils import validate_telegram_channel
    from django.utils import timezone
    
    channel_link = request.POST.get('channelLink', '').strip()
    keywords = request.POST.get('alertKeywords', '').strip()
    
    if not channel_link:
        messages.error(request, "Please provide a valid Telegram channel link or username.")
        return redirect('telegram_links_dashboard')
    
    # Parse channel link to extract username
    username = None
    if channel_link.startswith('@'):
        username = channel_link[1:]
    elif 't.me/' in channel_link:
        username = channel_link.split('t.me/')[-1].split('?')[0]
    else:
        username = channel_link
    
    # Check if channel already exists
    if TelegramChannel.objects.filter(username=username).exists():
        messages.info(request, f"Channel @{username} is already being monitored.")
        return redirect('telegram_links_dashboard')
    
    try:
        # Validate the channel first
        messages.info(request, f"Validating channel @{username}...")
        validation_result = validate_telegram_channel(username)
        
        # Create new channel with validation results
        channel = TelegramChannel.objects.create(
            name=f"Channel {username}",
            username=username,
            url=f"https://t.me/{username}",
            description=f"Monitored channel with keywords: {keywords}" if keywords else "Manually added channel",
            is_active=True,
            validation_status=validation_result['status'],
            validation_date=timezone.now(),
            validation_error=validation_result.get('error', '')
        )
        
        # Provide appropriate feedback based on validation result
        if validation_result['status'] == 'PUBLIC_OK':
            messages.success(request, f"✅ Successfully added and validated channel @{username} for monitoring.")
        elif validation_result['status'] == 'NOT_FOUND':
            messages.warning(request, f"⚠️ Added channel @{username} but it was not found. Please check the channel name.")
        elif validation_result['status'] == 'NO_API_CREDENTIALS':
            messages.warning(request, f"⚠️ Added channel @{username} but validation skipped (no API credentials).")
        else:
            messages.warning(request, f"⚠️ Added channel @{username} but validation failed: {validation_result.get('error', 'Unknown error')}")
        
    except Exception as e:
        messages.error(request, f"Failed to add channel: {str(e)}")
    
    # Stay on the same page
    return redirect(request.META.get('HTTP_REFERER', 'telegram_links_dashboard'))

@login_required
@require_POST
def toggle_channel_monitoring(request, channel_id):
    """Toggle monitoring status of a channel"""
    from .models import TelegramChannel
    
    try:
        channel = TelegramChannel.objects.get(id=channel_id)
        channel.is_active = not channel.is_active
        channel.save()
        
        status = "activated" if channel.is_active else "paused"
        messages.success(request, f"Channel @{channel.username} monitoring {status}.")
        
    except TelegramChannel.DoesNotExist:
        messages.error(request, "Channel not found.")
    except Exception as e:
        messages.error(request, f"Failed to update channel: {str(e)}")
    
    # Stay on the same page
    return redirect(request.META.get('HTTP_REFERER', 'telegram_links_dashboard'))

@login_required
@require_POST
def remove_telegram_channel(request, channel_id):
    """Remove a Telegram channel from monitoring"""
    from .models import TelegramChannel
    
    try:
        channel = TelegramChannel.objects.get(id=channel_id)
        username = channel.username
        channel.delete()
        
        messages.success(request, f"Channel @{username} has been removed from monitoring.")
        
    except TelegramChannel.DoesNotExist:
        messages.error(request, "Channel not found.")
    except Exception as e:
        messages.error(request, f"Failed to remove channel: {str(e)}")
    
    # Stay on the same page
    return redirect(request.META.get('HTTP_REFERER', 'telegram_links_dashboard'))

@login_required
def process_telegram_links_view(request):
    """Process Telegram links via web interface"""
    from .management.commands.process_telegram_links import Command
    
    try:
        # Run the management command
        command = Command()
        command.handle()
        
        messages.success(request, "Telegram links processed successfully.")
        
    except Exception as e:
        messages.error(request, f"Failed to process links: {str(e)}")
    
    # Stay on the same page
    return redirect(request.META.get('HTTP_REFERER', 'telegram_links_dashboard'))

@login_required
def crawl_telegram_channels(request):
    """Crawl GitHub repository to discover and validate Telegram channels"""
    import requests
    import re
    from django.utils import timezone
    from .models import TelegramChannel
    from .utils import validate_telegram_channel
    
    try:
        # Fetch the GitHub markdown content
        github_url = "https://raw.githubusercontent.com/fastfire/deepdarkCTI/main/telegram_infostealer.md"
        response = requests.get(github_url, timeout=30)
        response.raise_for_status()
        
        # Extract Telegram channel links from markdown
        content = response.text
        telegram_links = re.findall(r'https://t\.me/([a-zA-Z0-9_]+)', content)
        
        # Also extract @username patterns
        at_patterns = re.findall(r'@([a-zA-Z0-9_]+)', content)
        
        # Combine and deduplicate
        all_usernames = list(set(telegram_links + at_patterns))
        
        discovered_channels = []
        skipped_channels = []
        
        for username in all_usernames:
            # Skip if username is too short or contains invalid characters
            if len(username) < 3 or not re.match(r'^[a-zA-Z0-9_]+$', username):
                continue
                
            # Check if channel already exists
            existing_channel = TelegramChannel.objects.filter(username=username).first()
            if existing_channel:
                # Update existing channel with fresh validation status
                validation_result = validate_telegram_channel(username)
                existing_channel.validation_status = validation_result['status']
                existing_channel.validation_date = timezone.now()
                existing_channel.validation_error = validation_result.get('error', '')
                existing_channel.is_active = validation_result['is_active']
                existing_channel.save()
                
                skipped_channels.append({
                    'username': username,
                    'reason': 'Updated existing channel'
                })
                continue
            
            # Use the new validation function
            validation_result = validate_telegram_channel(username)
            
            # Create new channel with detailed validation info
            channel = TelegramChannel.objects.create(
                name=f"Discovered: {username}",
                username=username,
                url=f"https://t.me/{username}",
                description=f"Discovered from deepdarkCTI repository",
                is_active=validation_result['is_active'],
                validation_status=validation_result['status'],
                validation_date=timezone.now(),
                validation_error=validation_result.get('error', '')
            )
            
            discovered_channels.append({
                'username': username,
                'status': validation_result['status'],
                'is_active': validation_result['is_active'],
                'title': validation_result['title'],
                'members_count': validation_result['members_count'],
                'error': validation_result['error'],
                'new': True,
                'channel_id': channel.id
            })
        
        # Prepare detailed success message
        total_found = len(all_usernames)
        new_channels = len(discovered_channels)
        updated_channels = len(skipped_channels)
        active_count = sum(1 for c in discovered_channels if c['is_active'])
        inactive_count = new_channels - active_count
        
        if new_channels > 0 or updated_channels > 0:
            messages.success(
                request, 
                f"Processed {total_found} channels: {new_channels} new, {updated_channels} updated. "
                f"New channels: {active_count} active, {inactive_count} inactive."
            )
        else:
            messages.info(
                request, 
                f"No channels found to process. Total channels checked: {total_found}."
            )
        
    except requests.RequestException as e:
        messages.error(request, f"Failed to fetch GitHub repository: {str(e)}")
    except Exception as e:
        messages.error(request, f"Failed to crawl channels: {str(e)}")
    
    # Stay on the same page by redirecting to the current URL or fallback to telegram links page
    return redirect(request.META.get('HTTP_REFERER', 'telegram_links_dashboard'))

@login_required
@require_POST
def scrape_telegram_channel(request, channel_id):
    """Start scraping a specific Telegram channel"""
    from .models import TelegramChannel
    from .tasks import scrape_channel_task
    
    try:
        # Get the channel
        channel = TelegramChannel.objects.get(id=channel_id)
        
        # Check if channel is active
        if channel.validation_status != 'PUBLIC_OK':
            messages.error(request, f'Cannot scrape channel @{channel.username}: Channel is not active (Status: {channel.validation_status})')
            return redirect(request.META.get('HTTP_REFERER', 'telegram_links_dashboard'))
        
        # Get last scraped message ID (default to 0 for first scrape)
        last_scraped_msg_id = getattr(channel, 'last_scraped_msg_id', 0)
        
        # Create scrape job
        job_data = {
            'channel_id': channel.id,
            'channel_username': channel.username,
            'last_scraped_msg_id': last_scraped_msg_id,
            'requested_by': request.user.id,
            'requested_at': timezone.now().isoformat()
        }
        
        # Queue the scraping task
        try:
            task = scrape_channel_task.delay(
                channel_id=channel.id,
                channel_username=channel.username,
                last_scraped_msg_id=last_scraped_msg_id,
                requested_by=request.user.id
            )
            
            # Update channel with task info
            channel.scraping_task_id = task.id
            channel.scraping_status = 'PENDING'
            channel.save()
            
            messages.success(request, f'Started scraping channel @{channel.username}. Task ID: {task.id}')
            
        except Exception as celery_error:
            # Fallback to synchronous scraping if Celery is not available
            messages.info(request, f'Running scraping synchronously for @{channel.username} (Celery not available)')
            
            try:
                # Import and run scraper directly
                from .scraper import run_sync_scraping
                result = run_sync_scraping(channel.username, last_scraped_msg_id)
                
                if result['success']:
                    messages.success(request, f'Successfully scraped @{channel.username}: {result["messages_count"]} messages, {result["files_count"]} files')
                else:
                    messages.error(request, f'Error scraping @{channel.username}: {result["error"]}')
                    
            except Exception as scraping_error:
                messages.error(request, f'Error during scraping: {str(scraping_error)}')
        
    except TelegramChannel.DoesNotExist:
        messages.error(request, 'Channel not found')
    except Exception as e:
        messages.error(request, f'Error starting scrape job: {str(e)}')
    
    # Stay on the same page
    return redirect(request.META.get('HTTP_REFERER', 'telegram_links_dashboard'))

@login_required
def get_scraping_progress(request, channel_id):
    """Get scraping progress for a specific channel"""
    from .models import TelegramChannel
    from .tasks import scrape_channel_task
    from celery.result import AsyncResult
    from django.http import JsonResponse
    
    try:
        channel = TelegramChannel.objects.get(id=channel_id)
        
        if not channel.scraping_task_id:
            return JsonResponse({
                'status': 'IDLE',
                'progress': 0,
                'message': 'No active scraping task',
                'messages_count': 0,
                'files_count': 0,
                'estimated_time': 'N/A'
            })
        
        # Get task result
        task_result = AsyncResult(channel.scraping_task_id)
        
        if task_result.state == 'PENDING':
            return JsonResponse({
                'status': 'PENDING',
                'progress': 0,
                'message': 'Task is waiting to start...',
                'messages_count': 0,
                'files_count': 0,
                'estimated_time': 'Calculating...'
            })
        elif task_result.state == 'PROGRESS':
            meta = task_result.info
            return JsonResponse({
                'status': 'RUNNING',
                'progress': meta.get('progress', 0),
                'message': meta.get('status', 'Processing...'),
                'messages_count': meta.get('messages_count', 0),
                'files_count': meta.get('files_count', 0),
                'estimated_time': meta.get('estimated_time', 'Calculating...')
            })
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            return JsonResponse({
                'status': 'COMPLETED',
                'progress': 100,
                'message': 'Scraping completed successfully!',
                'messages_count': result.get('messages_count', 0),
                'files_count': result.get('files_count', 0),
                'estimated_time': 'Done!'
            })
        elif task_result.state == 'FAILURE':
            return JsonResponse({
                'status': 'FAILED',
                'progress': 0,
                'message': f'Scraping failed: {str(task_result.info)}',
                'messages_count': 0,
                'files_count': 0,
                'estimated_time': 'Failed'
            })
        else:
            return JsonResponse({
                'status': task_result.state,
                'progress': 0,
                'message': f'Task state: {task_result.state}',
                'messages_count': 0,
                'files_count': 0,
                'estimated_time': 'Unknown'
            })
            
    except TelegramChannel.DoesNotExist:
        return JsonResponse({'error': 'Channel not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
