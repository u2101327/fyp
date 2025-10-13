"""
Management command to set up initial data for LeakGuard API
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import DataSource, MonitoredCredential, CredentialLeak, Alert, UserProfile
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Set up initial data for LeakGuard API testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username for the admin user'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@leakguard.com',
            help='Email for the admin user'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Password for the admin user'
        )

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial data for LeakGuard API...')
        
        # Create admin user
        username = options['username']
        email = options['email']
        password = options['password']
        
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Created admin user: {username}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Admin user already exists: {username}')
            )
        
        # Create user profile
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'email_notifications': True,
                'default_severity_threshold': 'medium',
                'api_rate_limit': 1000
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Created user profile')
            )
        
        # Create sample data sources
        data_sources = [
            {
                'name': 'Telegram Channel - Data Leaks',
                'source_type': 'telegram',
                'url': 'https://t.me/dataleaks',
                'configuration': {
                    'channel_id': '@dataleaks',
                    'api_key': 'bot_token_here'
                }
            },
            {
                'name': 'Pastebin Monitor',
                'source_type': 'paste_site',
                'url': 'https://pastebin.com',
                'configuration': {
                    'keywords': ['password', 'login', 'credential'],
                    'scan_interval': 300
                }
            },
            {
                'name': 'Dark Web Forum Alpha',
                'source_type': 'dark_web',
                'url': 'http://darkforum.onion',
                'configuration': {
                    'forum_id': 'alpha',
                    'access_token': 'token_here'
                }
            },
            {
                'name': 'GitHub Public Repos',
                'source_type': 'github',
                'url': 'https://github.com',
                'configuration': {
                    'search_terms': ['password', 'api_key', 'secret'],
                    'scan_interval': 600
                }
            },
            {
                'name': 'Data Breach Database',
                'source_type': 'data_breach',
                'url': 'https://breachdb.com',
                'configuration': {
                    'api_key': 'breach_api_key',
                    'update_interval': 3600
                }
            }
        ]
        
        created_sources = []
        for source_data in data_sources:
            source, created = DataSource.objects.get_or_create(
                name=source_data['name'],
                defaults=source_data
            )
            if created:
                created_sources.append(source)
                self.stdout.write(
                    self.style.SUCCESS(f'Created data source: {source.name}')
                )
        
        # Create sample monitored credentials
        sample_credentials = [
            {
                'credential_type': 'email',
                'value': 'admin@example.com',
                'tags': ['work', 'critical'],
                'notes': 'Primary admin email'
            },
            {
                'credential_type': 'email',
                'value': 'support@example.com',
                'tags': ['work', 'support'],
                'notes': 'Support team email'
            },
            {
                'credential_type': 'username',
                'value': 'admin_user',
                'tags': ['admin', 'critical'],
                'notes': 'Admin username'
            },
            {
                'credential_type': 'domain',
                'value': 'example.com',
                'tags': ['company', 'critical'],
                'notes': 'Company domain'
            },
            {
                'credential_type': 'api_key',
                'value': 'sk-1234567890abcdef',
                'tags': ['api', 'production'],
                'notes': 'Production API key'
            }
        ]
        
        created_credentials = []
        for cred_data in sample_credentials:
            credential, created = MonitoredCredential.objects.get_or_create(
                user=user,
                credential_type=cred_data['credential_type'],
                value=cred_data['value'],
                defaults=cred_data
            )
            if created:
                created_credentials.append(credential)
                self.stdout.write(
                    self.style.SUCCESS(f'Created credential: {credential.credential_type}: {credential.value}')
                )
        
        # Create sample credential leaks
        if created_sources and created_credentials:
            leak_samples = [
                {
                    'credential_type': 'email',
                    'leaked_value': 'admin@example.com',
                    'leak_content': 'Email: admin@example.com\nPassword: admin123\nSource: Data breach from 2023',
                    'leak_url': 'https://pastebin.com/abc123',
                    'severity': 'critical',
                    'status': 'new',
                    'confidence_score': 0.95,
                    'tags': ['pastebin', 'verified'],
                    'metadata': {'breach_date': '2023-12-01', 'records_count': 1000}
                },
                {
                    'credential_type': 'username',
                    'leaked_value': 'admin_user',
                    'leak_content': 'Username: admin_user\nPassword: password123\nFound in: GitHub repository',
                    'leak_url': 'https://github.com/user/repo/blob/main/config.txt',
                    'severity': 'high',
                    'status': 'investigating',
                    'confidence_score': 0.85,
                    'tags': ['github', 'config'],
                    'metadata': {'repository': 'user/repo', 'file': 'config.txt'}
                },
                {
                    'credential_type': 'api_key',
                    'leaked_value': 'sk-1234567890abcdef',
                    'leak_content': 'API Key: sk-1234567890abcdef\nService: OpenAI\nFound in: Telegram channel',
                    'leak_url': 'https://t.me/dataleaks/123',
                    'severity': 'critical',
                    'status': 'confirmed',
                    'confidence_score': 0.98,
                    'tags': ['telegram', 'openai'],
                    'metadata': {'service': 'OpenAI', 'channel': '@dataleaks'}
                }
            ]
            
            for leak_data in leak_samples:
                # Find matching credential
                matching_cred = None
                for cred in created_credentials:
                    if cred.value == leak_data['leaked_value']:
                        matching_cred = cred
                        break
                
                if matching_cred:
                    leak_data['monitored_credential'] = matching_cred
                    leak_data['source'] = random.choice(created_sources)
                    leak_data['leak_date'] = datetime.now() - timedelta(days=random.randint(1, 30))
                    
                    leak = CredentialLeak.objects.create(user=user, **leak_data)
                    self.stdout.write(
                        self.style.SUCCESS(f'Created leak: {leak.credential_type}: {leak.leaked_value}')
                    )
        
        # Create sample alerts
        alert_samples = [
            {
                'alert_type': 'leak_detected',
                'title': 'Critical Email Leak Detected',
                'message': 'Your email admin@example.com was found in a data breach. Immediate action required.',
                'priority': 'critical'
            },
            {
                'alert_type': 'leak_detected',
                'title': 'API Key Exposed on GitHub',
                'message': 'Your API key was found in a public GitHub repository. Please rotate immediately.',
                'priority': 'high'
            },
            {
                'alert_type': 'source_offline',
                'title': 'Monitoring Source Offline',
                'message': 'Telegram Channel - Data Leaks is currently offline. Monitoring paused.',
                'priority': 'medium'
            }
        ]
        
        for alert_data in alert_samples:
            alert = Alert.objects.create(user=user, **alert_data)
            self.stdout.write(
                self.style.SUCCESS(f'Created alert: {alert.title}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\nInitial data setup completed successfully!')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Admin user: {username} / {password}')
        )
        self.stdout.write(
            self.style.SUCCESS('You can now test the API endpoints.')
        )
