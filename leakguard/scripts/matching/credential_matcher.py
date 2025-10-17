"""
Enhanced credential matching service for LeakGuard
Compares indexed indicators against user-monitored items
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from opensearchpy import OpenSearch
from opensearchpy.exceptions import OpenSearchException

from django.contrib.auth.models import User
from api.models import MonitoredCredential, CredentialLeak, Alert, DataSource
from config.opensearch_config import OPENSEARCH_CONFIG

logger = logging.getLogger(__name__)

class CredentialMatcher:
    """Enhanced credential matching service"""
    
    def __init__(self):
        self.opensearch_client = self._setup_opensearch()
        self.telegram_source = self._get_or_create_telegram_source()
    
    def _setup_opensearch(self) -> OpenSearch:
        """Setup OpenSearch client"""
        try:
            client = OpenSearch(**OPENSEARCH_CONFIG)
            client.info()  # Test connection
            logger.info("✅ OpenSearch connection established for matching")
            return client
        except Exception as e:
            logger.error(f"❌ Failed to connect to OpenSearch: {e}")
            raise
    
    def _get_or_create_telegram_source(self) -> DataSource:
        """Get or create Telegram data source"""
        source, created = DataSource.objects.get_or_create(
            name='Telegram Channels',
            source_type='telegram',
            defaults={
                'url': 'https://telegram.org',
                'is_active': True,
                'check_interval': 300
            }
        )
        return source
    
    def find_matches_for_user(self, user_id: int, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Find matches between indexed data and user's monitored credentials"""
        try:
            # Get user's monitored credentials
            monitored_creds = MonitoredCredential.objects.filter(
                user_id=user_id, 
                is_active=True
            )
            
            if not monitored_creds.exists():
                logger.info(f"No active monitored credentials for user {user_id}")
                return []
            
            matches = []
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for cred in monitored_creds:
                cred_matches = self._search_for_credential(cred, cutoff_time)
                matches.extend(cred_matches)
            
            # Sort by confidence score and timestamp
            matches.sort(key=lambda x: (x['confidence'], x['timestamp']), reverse=True)
            
            logger.info(f"Found {len(matches)} matches for user {user_id}")
            return matches
            
        except Exception as e:
            logger.error(f"Error finding matches for user {user_id}: {e}")
            return []
    
    def _search_for_credential(self, credential: MonitoredCredential, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Search for a specific credential in indexed data"""
        matches = []
        
        # Build search query based on credential type
        if credential.credential_type == 'email':
            matches.extend(self._search_email_patterns(credential, cutoff_time))
        elif credential.credential_type == 'username':
            matches.extend(self._search_username_patterns(credential, cutoff_time))
        elif credential.credential_type == 'domain':
            matches.extend(self._search_domain_patterns(credential, cutoff_time))
        elif credential.credential_type == 'phone':
            matches.extend(self._search_phone_patterns(credential, cutoff_time))
        elif credential.credential_type == 'api_key':
            matches.extend(self._search_api_key_patterns(credential, cutoff_time))
        elif credential.credential_type == 'password':
            matches.extend(self._search_password_patterns(credential, cutoff_time))
        
        return matches
    
    def _search_email_patterns(self, credential: MonitoredCredential, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Search for email patterns"""
        email_value = credential.value.lower()
        domain = email_value.split('@')[1] if '@' in email_value else None
        
        queries = [
            # Exact email match
            {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"message_text": email_value}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            }
        ]
        
        # Also search for domain if it's a full email
        if domain:
            queries.append({
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"message_text": domain}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            })
        
        return self._execute_queries(queries, credential, 'email')
    
    def _search_username_patterns(self, credential: MonitoredCredential, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Search for username patterns"""
        username = credential.value.lower()
        
        # Search for username in various contexts
        queries = [
            # Direct username match
            {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"message_text": username}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            },
            # Username with common separators
            {
                "query": {
                    "bool": {
                        "must": [
                            {"wildcard": {"message_text": f"*{username}*"}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            }
        ]
        
        return self._execute_queries(queries, credential, 'username')
    
    def _search_domain_patterns(self, credential: MonitoredCredential, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Search for domain patterns"""
        domain = credential.value.lower()
        
        queries = [
            # Exact domain match
            {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"message_text": domain}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            },
            # Domain with subdomains
            {
                "query": {
                    "bool": {
                        "must": [
                            {"wildcard": {"message_text": f"*.{domain}"}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            }
        ]
        
        return self._execute_queries(queries, credential, 'domain')
    
    def _search_phone_patterns(self, credential: MonitoredCredential, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Search for phone number patterns"""
        phone = credential.value
        
        # Normalize phone number for searching
        normalized_phone = re.sub(r'[^\d+]', '', phone)
        
        queries = [
            # Exact phone match
            {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"message_text": phone}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            },
            # Normalized phone match
            {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"message_text": normalized_phone}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            }
        ]
        
        return self._execute_queries(queries, credential, 'phone')
    
    def _search_api_key_patterns(self, credential: MonitoredCredential, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Search for API key patterns"""
        api_key = credential.value
        
        queries = [
            # Exact API key match
            {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"message_text": api_key}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            },
            # Partial API key match (for truncated keys)
            {
                "query": {
                    "bool": {
                        "must": [
                            {"wildcard": {"message_text": f"{api_key[:8]}*"}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            }
        ]
        
        return self._execute_queries(queries, credential, 'api_key')
    
    def _search_password_patterns(self, credential: MonitoredCredential, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Search for password patterns"""
        password = credential.value
        
        queries = [
            # Exact password match
            {
                "query": {
                    "bool": {
                        "must": [
                            {"match": {"message_text": password}},
                            {"range": {"message_date": {"gte": cutoff_time.isoformat()}}}
                        ]
                    }
                }
            }
        ]
        
        return self._execute_queries(queries, credential, 'password')
    
    def _execute_queries(self, queries: List[Dict], credential: MonitoredCredential, search_type: str) -> List[Dict[str, Any]]:
        """Execute search queries and return formatted results"""
        matches = []
        
        for query in queries:
            try:
                # Search in telegram-extracted-data index
                results = self.opensearch_client.search(
                    index="telegram-extracted-data",
                    body=query,
                    size=100
                )
                
                for hit in results['hits']['hits']:
                    source = hit['_source']
                    confidence = self._calculate_confidence(hit['_score'], search_type, source)
                    
                    match = {
                        'credential': credential,
                        'source_document': source,
                        'confidence': confidence,
                        'timestamp': source.get('message_date'),
                        'channel_name': source.get('channel_name'),
                        'message_id': source.get('message_id'),
                        'channel_id': source.get('channel_id'),
                        'search_type': search_type,
                        'opensearch_score': hit['_score']
                    }
                    matches.append(match)
                    
            except Exception as e:
                logger.error(f"Error executing query for {credential.value}: {e}")
                continue
        
        return matches
    
    def _calculate_confidence(self, opensearch_score: float, search_type: str, source: Dict) -> float:
        """Calculate confidence score for a match"""
        base_confidence = min(opensearch_score / 10.0, 1.0)  # Normalize OpenSearch score
        
        # Boost confidence based on context
        message_text = source.get('message_text', '').lower()
        extracted_data = source.get('extracted_data', {})
        
        # Check if credential appears in extracted structured data
        if search_type in extracted_data:
            base_confidence += 0.2
        
        # Check for credential-like patterns in context
        if search_type == 'email' and '@' in message_text:
            base_confidence += 0.1
        elif search_type == 'domain' and ('.com' in message_text or '.org' in message_text):
            base_confidence += 0.1
        elif search_type == 'phone' and re.search(r'\d{3,}', message_text):
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def create_alert_from_match(self, match: Dict[str, Any], user: User) -> Optional[Alert]:
        """Create alert from a credential match"""
        try:
            credential = match['credential']
            source = match['source_document']
            confidence = match['confidence']
            
            # Determine severity based on confidence and credential type
            if confidence > 0.8:
                severity = 'critical' if credential.credential_type in ['password', 'api_key'] else 'high'
            elif confidence > 0.6:
                severity = 'high' if credential.credential_type in ['password', 'api_key'] else 'medium'
            else:
                severity = 'medium'
            
            # Create credential leak record
            credential_leak = CredentialLeak.objects.create(
                user=user,
                monitored_credential=credential,
                source=self.telegram_source,
                credential_type=credential.credential_type,
                leaked_value=credential.value,
                leak_content=source.get('message_text', ''),
                leak_url=f"https://t.me/{source.get('channel_name', 'unknown')}",
                severity=severity,
                confidence_score=confidence,
                leak_date=source.get('message_date'),
                metadata={
                    'channel_id': source.get('channel_id'),
                    'message_id': source.get('message_id'),
                    'sender_username': source.get('sender_username'),
                    'search_type': match['search_type']
                }
            )
            
            # Create alert
            title = f"Credential Found: {credential.credential_type.title()}"
            message = f"Your {credential.credential_type} '{credential.value}' was found in Telegram channel @{source.get('channel_name', 'unknown')}."
            
            alert = Alert.objects.create(
                user=user,
                alert_type='leak_detected',
                title=title,
                message=message,
                priority=severity,
                credential_leak=credential_leak,
                source=self.telegram_source
            )
            
            logger.info(f"Created alert {alert.id} for credential {credential.value}")
            return alert
            
        except Exception as e:
            logger.error(f"Error creating alert from match: {e}")
            return None
    
    def process_matches_for_user(self, user_id: int, hours_back: int = 24) -> int:
        """Process all matches for a user and create alerts"""
        try:
            user = User.objects.get(id=user_id)
            matches = self.find_matches_for_user(user_id, hours_back)
            
            alerts_created = 0
            for match in matches:
                # Check if alert already exists for this match
                existing_alert = Alert.objects.filter(
                    user=user,
                    credential_leak__monitored_credential=match['credential'],
                    credential_leak__leaked_value=match['credential'].value,
                    created_at__gte=datetime.now() - timedelta(hours=1)
                ).exists()
                
                if not existing_alert:
                    alert = self.create_alert_from_match(match, user)
                    if alert:
                        alerts_created += 1
            
            logger.info(f"Created {alerts_created} new alerts for user {user_id}")
            return alerts_created
            
        except Exception as e:
            logger.error(f"Error processing matches for user {user_id}: {e}")
            return 0
