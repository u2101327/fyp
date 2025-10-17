#!/usr/bin/env python3
"""
OpenSearch service for saving crawled Telegram URLs and channel information
"""

import os
import sys
import django
from datetime import datetime, timezone
from typing import List, Dict, Optional

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from opensearchpy import OpenSearch
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class OpenSearchURLService:
    """Service for managing crawled URLs in OpenSearch"""
    
    def __init__(self):
        self.client = self._get_opensearch_client()
        self.crawled_urls_index = "crawled-telegram-urls"
        self.telegram_channels_index = "telegram-channels"
    
    def _get_opensearch_client(self) -> OpenSearch:
        """Initialize OpenSearch client"""
        try:
            # Try to get config from settings first
            opensearch_config = getattr(settings, 'OPENSEARCH_CONFIG', {})
            
            if opensearch_config:
                return OpenSearch(**opensearch_config)
            else:
                # Fallback to default config
                return OpenSearch(
                    hosts=[{'host': 'localhost', 'port': 9200}],
                    http_auth=('admin', 'admin'),
                    use_ssl=False,
                    verify_certs=False,
                    ssl_assert_hostname=False,
                    ssl_show_warn=False,
                    timeout=30,
                    max_retries=3,
                    retry_on_timeout=True
                )
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch client: {e}")
            raise
    
    def create_indices(self):
        """Create required indices with proper mappings"""
        try:
            # Create crawled URLs index
            if not self.client.indices.exists(index=self.crawled_urls_index):
                crawled_urls_mapping = {
                    "mappings": {
                        "properties": {
                            "url": {"type": "keyword"},
                            "username": {"type": "keyword"},
                            "channel_name": {"type": "text", "analyzer": "standard"},
                            "source": {"type": "keyword"},
                            "source_url": {"type": "keyword"},
                            "crawled_at": {"type": "date"},
                            "crawl_session_id": {"type": "keyword"},
                            "is_active": {"type": "boolean"},
                            "description": {"type": "text"},
                            "metadata": {"type": "object"},
                            "investigation_notes": {"type": "text"},
                            "credential_leaks_found": {"type": "boolean", "default": False},
                            "leak_count": {"type": "integer", "default": 0}
                        }
                    }
                }
                self.client.indices.create(index=self.crawled_urls_index, body=crawled_urls_mapping)
                logger.info(f"Created index: {self.crawled_urls_index}")
            
            # Create telegram channels index
            if not self.client.indices.exists(index=self.telegram_channels_index):
                channels_mapping = {
                    "mappings": {
                        "properties": {
                            "channel_id": {"type": "keyword"},
                            "name": {"type": "text", "analyzer": "standard"},
                            "username": {"type": "keyword"},
                            "url": {"type": "keyword"},
                            "description": {"type": "text"},
                            "is_active": {"type": "boolean"},
                            "created_at": {"type": "date"},
                            "updated_at": {"type": "date"},
                            "last_scanned": {"type": "date"},
                            "message_count": {"type": "integer", "default": 0},
                            "leak_count": {"type": "integer", "default": 0},
                            "source": {"type": "keyword"},
                            "metadata": {"type": "object"}
                        }
                    }
                }
                self.client.indices.create(index=self.telegram_channels_index, body=channels_mapping)
                logger.info(f"Created index: {self.telegram_channels_index}")
                
        except Exception as e:
            logger.error(f"Error creating indices: {e}")
            raise
    
    def save_crawled_urls(self, urls: List[Dict[str, str]], crawl_session_id: str = None) -> bool:
        """Save crawled URLs to OpenSearch"""
        try:
            if not crawl_session_id:
                crawl_session_id = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.create_indices()
            
            saved_count = 0
            for url_data in urls:
                doc = {
                    "url": url_data.get('url'),
                    "username": url_data.get('username'),
                    "channel_name": url_data.get('username', ''),  # Use username as channel name if not provided
                    "source": url_data.get('source', 'github'),
                    "source_url": url_data.get('source_url', 'https://raw.githubusercontent.com/fastfire/deepdarkCTI/main/telegram_infostealer.md'),
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "crawl_session_id": crawl_session_id,
                    "is_active": True,
                    "description": url_data.get('description', f'Auto-crawled from {url_data.get("source", "github")}'),
                    "metadata": {
                        "crawl_method": "github_automation",
                        "extracted_from": "deepdarkCTI",
                        "validation_status": "pending"
                    },
                    "investigation_notes": "",
                    "credential_leaks_found": False,
                    "leak_count": 0
                }
                
                # Use username as document ID for uniqueness
                doc_id = f"{url_data.get('username')}_{crawl_session_id}"
                
                self.client.index(
                    index=self.crawled_urls_index,
                    id=doc_id,
                    body=doc
                )
                saved_count += 1
                logger.info(f"Saved crawled URL: {url_data.get('url')}")
            
            logger.info(f"Successfully saved {saved_count} crawled URLs to OpenSearch")
            return True
            
        except Exception as e:
            logger.error(f"Error saving crawled URLs to OpenSearch: {e}")
            return False
    
    def save_telegram_channel(self, channel_data: Dict) -> bool:
        """Save telegram channel information to OpenSearch"""
        try:
            self.create_indices()
            
            doc = {
                "channel_id": channel_data.get('id'),
                "name": channel_data.get('name'),
                "username": channel_data.get('username'),
                "url": channel_data.get('url'),
                "description": channel_data.get('description', ''),
                "is_active": channel_data.get('is_active', True),
                "created_at": channel_data.get('created_at'),
                "updated_at": channel_data.get('updated_at'),
                "last_scanned": channel_data.get('last_scanned'),
                "message_count": 0,
                "leak_count": 0,
                "source": "github_automation",
                "metadata": {
                    "added_via": "auto_collection",
                    "crawl_session": channel_data.get('crawl_session_id', 'unknown')
                }
            }
            
            self.client.index(
                index=self.telegram_channels_index,
                id=channel_data.get('id'),
                body=doc
            )
            
            logger.info(f"Saved telegram channel to OpenSearch: {channel_data.get('username')}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving telegram channel to OpenSearch: {e}")
            return False
    
    def get_crawled_urls(self, limit: int = 100) -> List[Dict]:
        """Retrieve crawled URLs from OpenSearch"""
        try:
            response = self.client.search(
                index=self.crawled_urls_index,
                body={
                    "query": {"match_all": {}},
                    "sort": [{"crawled_at": {"order": "desc"}}],
                    "size": limit
                }
            )
            
            urls = []
            for hit in response['hits']['hits']:
                urls.append(hit['_source'])
            
            return urls
            
        except Exception as e:
            logger.error(f"Error retrieving crawled URLs: {e}")
            return []
    
    def search_urls_by_keyword(self, keyword: str) -> List[Dict]:
        """Search crawled URLs by keyword"""
        try:
            response = self.client.search(
                index=self.crawled_urls_index,
                body={
                    "query": {
                        "multi_match": {
                            "query": keyword,
                            "fields": ["username", "channel_name", "description", "url"]
                        }
                    },
                    "sort": [{"crawled_at": {"order": "desc"}}]
                }
            )
            
            urls = []
            for hit in response['hits']['hits']:
                urls.append(hit['_source'])
            
            return urls
            
        except Exception as e:
            logger.error(f"Error searching URLs: {e}")
            return []
    
    def update_url_investigation_notes(self, username: str, notes: str) -> bool:
        """Update investigation notes for a crawled URL"""
        try:
            # Find the document by username
            response = self.client.search(
                index=self.crawled_urls_index,
                body={
                    "query": {"term": {"username": username}}
                }
            )
            
            if response['hits']['total']['value'] > 0:
                doc_id = response['hits']['hits'][0]['_id']
                self.client.update(
                    index=self.crawled_urls_index,
                    id=doc_id,
                    body={
                        "doc": {
                            "investigation_notes": notes,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating investigation notes: {e}")
            return False
    
    def mark_url_with_leaks(self, username: str, leak_count: int) -> bool:
        """Mark a URL as having credential leaks"""
        try:
            response = self.client.search(
                index=self.crawled_urls_index,
                body={
                    "query": {"term": {"username": username}}
                }
            )
            
            if response['hits']['total']['value'] > 0:
                doc_id = response['hits']['hits'][0]['_id']
                self.client.update(
                    index=self.crawled_urls_index,
                    id=doc_id,
                    body={
                        "doc": {
                            "credential_leaks_found": True,
                            "leak_count": leak_count,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error marking URL with leaks: {e}")
            return False
