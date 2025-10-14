from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
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

    context = {
        "monitored_credentials": rows,
        "alerts": alerts,
        "new_alerts_count": new_alerts_count
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
    from data_processor import CredentialProcessor
    from api.models import Alert
    
    if request.method == 'POST':
        # Get recent messages from all channels
        recent_messages = TelegramMessage.objects.filter(
            channel__is_active=True,
            created_at__gte=datetime.now() - timedelta(hours=24)
        ).order_by('-created_at')[:100]
        
        processor = CredentialProcessor()
        alerts_created = 0
        
        for message in recent_messages:
            # Process the message text line by line
            credentials = []
            for line in message.text.split('\n'):
                cred = processor.process_line(line)
                if cred:
                    credentials.append(cred)
            
            for cred in credentials:
                # Check if this credential matches any monitored credentials
                monitored_creds = MonitoredCredential.objects.filter(owner=request.user)
                
                for monitored in monitored_creds:
                    is_match = False
                    matched_value = ""
                    
                    if monitored.email and cred.get('email') == monitored.email:
                        is_match = True
                        matched_value = monitored.email
                    elif monitored.username and cred.get('username') == monitored.username:
                        is_match = True
                        matched_value = monitored.username
                    elif monitored.domain and cred.get('domain') == monitored.domain:
                        is_match = True
                        matched_value = monitored.domain
                    
                    if is_match:
                        # Create data leak record
                        data_leak = DataLeak.objects.create(
                            email=cred.get('email', ''),
                            username=cred.get('username', ''),
                            password=cred.get('password', ''),
                            domain=cred.get('domain', ''),
                            source=f'Telegram: {message.channel.username}',
                            source_url=message.channel.url,
                            severity=cred.get('severity', 'medium'),
                            telegram_message=message,
                            raw_data=cred.get('raw_data', message.text),
                            is_processed=True
                        )
                        
                        # Create alert
                        title = f"Credential Found in Telegram Channel"
                        message_text = f"Your credential '{matched_value}' was found in Telegram channel @{message.channel.username}. "
                        if cred.get('password'):
                            message_text += "Password was also exposed!"
                            priority = 'critical'
                        else:
                            priority = 'high'
                        
                        create_alert(
                            user=request.user,
                            title=title,
                            message=message_text,
                            priority=priority
                        )
                        
                        alerts_created += 1
        
        if alerts_created > 0:
            messages.success(request, f'Processed Telegram data and created {alerts_created} alerts!')
        else:
            messages.info(request, 'No matching credentials found in recent Telegram messages.')
    
    return redirect('telegram_monitor')

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
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            from telegram_automation import GitHubLinkExtractor, TelegramCollector, TelegramConfig
            
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
            
            # Step 2: Add channels to database
            channels_added = 0
            for link in telegram_links:
                channel, created = TelegramChannel.objects.get_or_create(
                    username=link['username'],
                    defaults={
                        'name': link['username'],
                        'url': link['url'],
                        'description': f'Auto-added from {link["source"]}',
                        'is_active': True
                    }
                )
                if created:
                    channels_added += 1
            
            messages.success(request, f'Successfully added {channels_added} Telegram channels from GitHub!')
            
            # Step 3: Start Telegram collection (this would run in background)
            # For demo purposes, we'll just show the channels were added
            # In production, you'd want to run this as a background task
            
        except Exception as e:
            messages.error(request, f'Error during automated collection: {str(e)}')
    
    return redirect('telegram_monitor')

@login_required
def start_telegram_scraping(request):
    """Start the Telegram scraping process"""
    if request.method == 'POST':
        try:
            # This would typically run as a background task
            # For now, we'll create a simple version that processes existing channels
            
            # Get active channels
            active_channels = TelegramChannel.objects.filter(is_active=True)
            
            if not active_channels.exists():
                messages.warning(request, 'No active channels to scrape. Add some channels first.')
                return redirect('telegram_monitor')
            
            # Create some demo messages for active channels
            messages_created = 0
            for channel in active_channels:
                # Create demo messages with various credential formats
                demo_messages = [
                    f'user@example.com:password123\nadmin@test.com:admin123\n{request.user.email}:demo_password',
                    f'john.doe@company.com:secret123\n{request.user.email}:leaked_password\nuser@domain.com:password456',
                    f'test@university.edu:student123\n{request.user.email}:academic_password\nprof@school.edu:teacher123'
                ]
                
                for i, msg_text in enumerate(demo_messages):
                    # Use get_or_create to avoid duplicate constraint errors
                    message, created = TelegramMessage.objects.get_or_create(
                        channel=channel,
                        message_id=1000 + i,
                        defaults={
                            'text': msg_text,
                            'date': datetime.now(),
                            'sender_username': 'scraper_bot'
                        }
                    )
                    if created:
                        messages_created += 1
            
            messages.success(request, f'Successfully scraped {messages_created} messages from {active_channels.count()} channels!')
            
        except Exception as e:
            messages.error(request, f'Error during scraping: {str(e)}')
    
    return redirect('telegram_monitor')   
