"""
OpenSearch client for LeakGuard
Handles indexing and searching of extracted credentials
"""

import logging
from typing import Dict, List, Any, Optional
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class LeakGuardOpenSearchClient:
    """Client for interacting with OpenSearch"""
    
    def __init__(self):
        self.client = None
        self.index_name = 'leakguard-credentials'
        self.file_index_name = 'leakguard-processed-files'
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize OpenSearch client"""
        try:
            from opensearchpy import OpenSearch
            
            # Get OpenSearch configuration from Django settings
            opensearch_hosts = getattr(settings, 'OPENSEARCH_DSL', {}).get('default', {}).get('hosts', ['localhost:9200'])
            
            self.client = OpenSearch(
                hosts=opensearch_hosts,
                http_auth=('admin', 'admin'),  # Default credentials
                use_ssl=False,
                verify_certs=False,
                ssl_assert_hostname=False,
                ssl_show_warn=False,
            )
            
            # Test connection
            if self.client.ping():
                logger.info("OpenSearch client initialized successfully")
            else:
                logger.error("Failed to connect to OpenSearch")
                self.client = None
                
        except Exception as e:
            logger.error(f"Error initializing OpenSearch client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if OpenSearch is available"""
        if not self.client:
            return False
        try:
            return self.client.ping()
        except:
            return False
    
    def create_indices(self):
        """Create OpenSearch indices"""
        if not self.is_available():
            logger.error("OpenSearch not available")
            return False
        
        try:
            from .documents import CredentialDocument, ProcessedFileDocument
            
            # Create credential index
            CredentialDocument._index.create()
            logger.info(f"Created index: {self.index_name}")
            
            # Create processed file index
            ProcessedFileDocument._index.create()
            logger.info(f"Created index: {self.file_index_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating indices: {e}")
            return False
    
    def index_credential(self, credential_id: int) -> bool:
        """Index a single credential"""
        if not self.is_available():
            return False
        
        try:
            from .models import ExtractedCredential
            from .documents import CredentialDocument
            
            credential = ExtractedCredential.objects.get(id=credential_id)
            doc = CredentialDocument()
            doc.meta.id = credential.id
            doc.meta.index = self.index_name
            
            # Prepare document data
            doc_data = {
                'email': doc.prepare_email(credential),
                'username': doc.prepare_username(credential),
                'password': doc.prepare_password(credential),
                'domain': doc.prepare_domain(credential),
                'ip_address': doc.prepare_ip_address(credential),
                'phone': doc.prepare_phone(credential),
                'credit_card': doc.prepare_credit_card(credential),
                'ssn': doc.prepare_ssn(credential),
                'extraction_method': doc.prepare_extraction_method(credential),
                'confidence_score': doc.prepare_confidence_score(credential),
                'is_verified': doc.prepare_is_verified(credential),
                'risk_level': doc.prepare_risk_level(credential),
                'channel_username': doc.prepare_channel_username(credential),
                'channel_name': doc.prepare_channel_name(credential),
                'message_id': doc.prepare_message_id(credential),
                'file_name': doc.prepare_file_name(credential),
                'file_size': doc.prepare_file_size(credential),
                'file_mime_type': doc.prepare_file_mime_type(credential),
                'risk_score': doc.prepare_risk_score(credential),
                'is_sensitive': doc.prepare_is_sensitive(credential),
                'extracted_at': doc.prepare_extracted_at(credential),
                'message_date': doc.prepare_message_date(credential),
                'file_processed_at': doc.prepare_file_processed_at(credential),
                'content': doc.prepare_content(credential),
                'id': credential.id,
                'created_at': credential.created_at,
                'updated_at': credential.updated_at,
            }
            
            # Index the document
            response = self.client.index(
                index=self.index_name,
                id=credential.id,
                body=doc_data
            )
            
            logger.info(f"Indexed credential {credential.id}: {response['result']}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing credential {credential_id}: {e}")
            return False
    
    def index_processed_file(self, processed_file_id: int) -> bool:
        """Index a processed file"""
        if not self.is_available():
            return False
        
        try:
            from .models import ProcessedFile
            from .documents import ProcessedFileDocument
            
            processed_file = ProcessedFile.objects.get(id=processed_file_id)
            doc = ProcessedFileDocument()
            doc.meta.id = processed_file.id
            doc.meta.index = self.file_index_name
            
            # Prepare document data
            doc_data = {
                'filename': doc.prepare_filename(processed_file),
                'file_size': doc.prepare_file_size(processed_file),
                'mime_type': doc.prepare_mime_type(processed_file),
                'file_extension': doc.prepare_file_extension(processed_file),
                'processing_status': doc.prepare_processing_status(processed_file),
                'processing_error': doc.prepare_processing_error(processed_file),
                'emails_count': doc.prepare_emails_count(processed_file),
                'passwords_count': doc.prepare_passwords_count(processed_file),
                'usernames_count': doc.prepare_usernames_count(processed_file),
                'domains_count': doc.prepare_domains_count(processed_file),
                'ip_addresses_count': doc.prepare_ip_addresses_count(processed_file),
                'phones_count': doc.prepare_phones_count(processed_file),
                'credit_cards_count': doc.prepare_credit_cards_count(processed_file),
                'ssns_count': doc.prepare_ssns_count(processed_file),
                'credentials_count': doc.prepare_credentials_count(processed_file),
                'risk_score': doc.prepare_risk_score(processed_file),
                'is_sensitive': doc.prepare_is_sensitive(processed_file),
                'channel_username': doc.prepare_channel_username(processed_file),
                'channel_name': doc.prepare_channel_name(processed_file),
                'message_id': doc.prepare_message_id(processed_file),
                's3_uri': doc.prepare_s3_uri(processed_file),
                'processed_at': doc.prepare_processed_at(processed_file),
                'message_date': doc.prepare_message_date(processed_file),
                'created_at': doc.prepare_created_at(processed_file),
                'id': processed_file.id,
                'updated_at': processed_file.updated_at,
            }
            
            # Index the document
            response = self.client.index(
                index=self.file_index_name,
                id=processed_file.id,
                body=doc_data
            )
            
            logger.info(f"Indexed processed file {processed_file.id}: {response['result']}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing processed file {processed_file_id}: {e}")
            return False
    
    def search_credentials(self, query: str, filters: Dict[str, Any] = None, size: int = 20, from_: int = 0) -> Dict[str, Any]:
        """Search credentials in OpenSearch"""
        if not self.is_available():
            return {'error': 'OpenSearch not available'}
        
        try:
            # Build search query
            search_body = {
                'query': {
                    'bool': {
                        'must': [],
                        'filter': []
                    }
                },
                'sort': [
                    {'extracted_at': {'order': 'desc'}},
                    {'_score': {'order': 'desc'}}
                ],
                'size': size,
                'from': from_
            }
            
            # Add text search
            if query:
                # Check if query looks like a domain
                if '.' in query and not '@' in query:
                    # Domain search - use wildcard match for partial domain matching
                    search_body['query']['bool']['must'].append({
                        'wildcard': {
                            'domain.keyword': f'*{query}*'
                        }
                    })
                elif '@' in query:
                    # Email search - use exact match for email field
                    search_body['query']['bool']['must'].append({
                        'term': {
                            'email.keyword': query
                        }
                    })
                else:
                    # General text search - use wildcard matching for better results
                    search_body['query']['bool']['must'].append({
                        'multi_match': {
                            'query': query,
                            'fields': [
                                'email^3',
                                'username^2',
                                'domain^2',
                                'channel_username^2',
                                'file_name^2'
                            ],
                            'type': 'phrase_prefix',  # More precise than best_fields
                            'fuzziness': '0'  # No fuzziness for exact matches
                        }
                    })
            else:
                # If no query, match all
                search_body['query']['bool']['must'].append({'match_all': {}})
            
            # Add filters
            if filters:
                for field, value in filters.items():
                    if value is not None and value != '':
                        if field == 'risk_level':
                            search_body['query']['bool']['filter'].append({
                                'term': {field: value}
                            })
                        elif field == 'domain':
                            search_body['query']['bool']['filter'].append({
                                'wildcard': {f'{field}.keyword': f'*{value}*'}
                            })
                        elif field == 'channel_username':
                            search_body['query']['bool']['filter'].append({
                                'term': {f'{field}.keyword': value}
                            })
                        elif field == 'date_range':
                            if 'from' in value or 'to' in value:
                                date_filter = {'range': {'extracted_at': {}}}
                                if 'from' in value:
                                    date_filter['range']['extracted_at']['gte'] = value['from']
                                if 'to' in value:
                                    date_filter['range']['extracted_at']['lte'] = value['to']
                                search_body['query']['bool']['filter'].append(date_filter)
            
            # Execute search
            response = self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            # Process results
            results = {
                'total': response['hits']['total']['value'],
                'hits': [],
                'aggregations': {}
            }
            
            for hit in response['hits']['hits']:
                source = hit['_source']
                results['hits'].append({
                    'id': hit['_id'],
                    'score': hit['_score'],
                    'email': source.get('email', ''),
                    'username': source.get('username', ''),
                    'password': source.get('password', ''),
                    'domain': source.get('domain', ''),
                    'risk_level': source.get('risk_level', 'LOW'),
                    'risk_score': source.get('risk_score', 0),
                    'channel_username': source.get('channel_username', ''),
                    'file_name': source.get('file_name', ''),
                    'extracted_at': source.get('extracted_at', ''),
                    'message_date': source.get('message_date', ''),
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching credentials: {e}")
            return {'error': str(e)}
    
    def get_aggregations(self) -> Dict[str, Any]:
        """Get aggregations for dashboard statistics"""
        if not self.is_available():
            return {'error': 'OpenSearch not available'}
        
        try:
            search_body = {
                'size': 0,
                'aggs': {
                    'total_credentials': {
                        'value_count': {
                            'field': 'id'
                        }
                    },
                    'risk_levels': {
                        'terms': {
                            'field': 'risk_level.keyword',
                            'size': 10
                        }
                    },
                    'domains': {
                        'terms': {
                            'field': 'domain.keyword',
                            'size': 20
                        }
                    },
                    'channels': {
                        'terms': {
                            'field': 'channel_username.keyword',
                            'size': 20
                        }
                    },
                    'daily_stats': {
                        'date_histogram': {
                            'field': 'extracted_at',
                            'calendar_interval': 'day',
                            'min_doc_count': 1
                        }
                    }
                }
            }
            
            response = self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            return {
                'total_credentials': response['aggregations']['total_credentials']['value'],
                'risk_levels': response['aggregations']['risk_levels']['buckets'],
                'domains': response['aggregations']['domains']['buckets'],
                'channels': response['aggregations']['channels']['buckets'],
                'daily_stats': response['aggregations']['daily_stats']['buckets']
            }
            
        except Exception as e:
            logger.error(f"Error getting aggregations: {e}")
            return {'error': str(e)}
    
    def bulk_index_credentials(self, credential_ids: List[int]) -> Dict[str, Any]:
        """Bulk index multiple credentials"""
        if not self.is_available():
            return {'error': 'OpenSearch not available'}
        
        try:
            from .models import ExtractedCredential
            from .documents import CredentialDocument
            
            credentials = ExtractedCredential.objects.filter(id__in=credential_ids)
            
            bulk_data = []
            for credential in credentials:
                doc = CredentialDocument()
                
                # Prepare document data
                doc_data = {
                    'email': doc.prepare_email(credential),
                    'username': doc.prepare_username(credential),
                    'password': doc.prepare_password(credential),
                    'domain': doc.prepare_domain(credential),
                    'ip_address': doc.prepare_ip_address(credential),
                    'phone': doc.prepare_phone(credential),
                    'credit_card': doc.prepare_credit_card(credential),
                    'ssn': doc.prepare_ssn(credential),
                    'extraction_method': doc.prepare_extraction_method(credential),
                    'confidence_score': doc.prepare_confidence_score(credential),
                    'is_verified': doc.prepare_is_verified(credential),
                    'risk_level': doc.prepare_risk_level(credential),
                    'channel_username': doc.prepare_channel_username(credential),
                    'channel_name': doc.prepare_channel_name(credential),
                    'message_id': doc.prepare_message_id(credential),
                    'file_name': doc.prepare_file_name(credential),
                    'file_size': doc.prepare_file_size(credential),
                    'file_mime_type': doc.prepare_file_mime_type(credential),
                    'risk_score': doc.prepare_risk_score(credential),
                    'is_sensitive': doc.prepare_is_sensitive(credential),
                    'extracted_at': doc.prepare_extracted_at(credential),
                    'message_date': doc.prepare_message_date(credential),
                    'file_processed_at': doc.prepare_file_processed_at(credential),
                    'content': doc.prepare_content(credential),
                    'id': credential.id,
                    'created_at': credential.created_at,
                    'updated_at': credential.updated_at,
                }
                
                # Add to bulk data
                bulk_data.append({
                    'index': {
                        '_index': self.index_name,
                        '_id': credential.id
                    }
                })
                bulk_data.append(doc_data)
            
            # Execute bulk index
            if bulk_data:
                response = self.client.bulk(body=bulk_data)
                
                # Check for errors
                errors = [item for item in response['items'] if 'error' in item.get('index', {})]
                
                return {
                    'success': True,
                    'indexed': len(credentials),
                    'errors': len(errors),
                    'error_details': errors if errors else None
                }
            else:
                return {'success': True, 'indexed': 0, 'errors': 0}
                
        except Exception as e:
            logger.error(f"Error bulk indexing credentials: {e}")
            return {'error': str(e)}

def get_opensearch_client() -> LeakGuardOpenSearchClient:
    """Get OpenSearch client instance"""
    return LeakGuardOpenSearchClient()
