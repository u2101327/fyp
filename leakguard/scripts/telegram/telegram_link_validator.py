#!/usr/bin/env python3
"""
Telegram Link Validator - Validates if Telegram links are active before saving
"""

import asyncio
import logging
from typing import List, Dict, Optional
from telethon import TelegramClient
from telethon.errors import (
    UsernameNotOccupiedError, 
    UsernameInvalidError,
    FloodWaitError,
    ChannelPrivateError,
    ChatAdminRequiredError
)

logger = logging.getLogger(__name__)

class TelegramLinkValidator:
    """Validates Telegram links to check if they are active and accessible"""
    
    def __init__(self, api_id: int, api_hash: str, phone_number: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = None
    
    async def start(self):
        """Initialize Telegram client"""
        try:
            self.client = TelegramClient('validation_session', self.api_id, self.api_hash)
            await self.client.start(phone=self.phone_number)
            logger.info("Telegram validation client started")
            return True
        except Exception as e:
            logger.error(f"Failed to start Telegram client: {e}")
            return False
    
    async def stop(self):
        """Stop Telegram client"""
        if self.client:
            await self.client.disconnect()
    
    async def validate_single_link(self, username: str) -> Dict[str, any]:
        """Validate a single Telegram link"""
        if not self.client:
            return {
                'username': username,
                'is_active': False,
                'status': 'client_not_initialized',
                'error': 'Telegram client not started'
            }
        
        try:
            # Remove @ if present
            clean_username = username.strip('@')
            
            # Try to get entity information
            entity = await self.client.get_entity(clean_username)
            
            # Extract channel information
            channel_info = {
                'username': clean_username,
                'is_active': True,
                'status': 'active',
                'channel_id': getattr(entity, 'id', None),
                'title': getattr(entity, 'title', clean_username),
                'description': getattr(entity, 'about', ''),
                'participants_count': getattr(entity, 'participants_count', 0),
                'is_private': getattr(entity, 'megagroup', False) or getattr(entity, 'broadcast', False),
                'is_verified': getattr(entity, 'verified', False),
                'is_scam': getattr(entity, 'scam', False),
                'is_fake': getattr(entity, 'fake', False),
                'access_hash': getattr(entity, 'access_hash', None)
            }
            
            logger.info(f"✅ Channel @{clean_username} is active: {channel_info['title']}")
            return channel_info
            
        except UsernameNotOccupiedError:
            logger.warning(f"❌ Channel @{username} does not exist")
            return {
                'username': username,
                'is_active': False,
                'status': 'not_found',
                'error': 'Channel does not exist'
            }
            
        except UsernameInvalidError:
            logger.warning(f"❌ Invalid username format: @{username}")
            return {
                'username': username,
                'is_active': False,
                'status': 'invalid_format',
                'error': 'Invalid username format'
            }
            
        except ChannelPrivateError:
            logger.warning(f"❌ Channel @{username} is private")
            return {
                'username': username,
                'is_active': False,
                'status': 'private',
                'error': 'Channel is private and cannot be accessed'
            }
            
        except ChatAdminRequiredError:
            logger.warning(f"❌ Admin required for @{username}")
            return {
                'username': username,
                'is_active': False,
                'status': 'admin_required',
                'error': 'Admin privileges required'
            }
            
        except FloodWaitError as e:
            logger.warning(f"⏳ Rate limited for @{username}, waiting {e.seconds} seconds")
            return {
                'username': username,
                'is_active': False,
                'status': 'rate_limited',
                'error': f'Rate limited, wait {e.seconds} seconds'
            }
            
        except Exception as e:
            logger.error(f"❌ Unexpected error validating @{username}: {e}")
            return {
                'username': username,
                'is_active': False,
                'status': 'error',
                'error': str(e)
            }
    
    async def validate_links_batch(self, links: List[Dict[str, str]], max_concurrent: int = 5) -> List[Dict[str, any]]:
        """Validate multiple links with concurrency control"""
        if not self.client:
            logger.error("Telegram client not initialized")
            return []
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_with_semaphore(link_data):
            async with semaphore:
                username = link_data.get('username', '')
                result = await self.validate_single_link(username)
                
                # Merge original link data with validation result
                result.update({
                    'url': link_data.get('url', f'https://t.me/{username}'),
                    'source': link_data.get('source', 'github'),
                    'source_url': link_data.get('source_url', ''),
                    'description': link_data.get('description', ''),
                    'channel_name': result.get('title', username),
                    'metadata': link_data.get('metadata', {})
                })
                
                return result
        
        # Validate all links concurrently
        tasks = [validate_with_semaphore(link) for link in links]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Validation task failed: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
    
    def filter_active_links(self, validation_results: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Filter and return only active links"""
        active_links = [result for result in validation_results if result.get('is_active', False)]
        inactive_links = [result for result in validation_results if not result.get('is_active', False)]
        
        logger.info(f"Validation complete: {len(active_links)} active, {len(inactive_links)} inactive")
        
        # Log inactive links for debugging
        for link in inactive_links:
            logger.info(f"Inactive: @{link['username']} - {link.get('status', 'unknown')}")
        
        return active_links
    
    def get_validation_summary(self, validation_results: List[Dict[str, any]]) -> Dict[str, int]:
        """Get summary statistics of validation results"""
        summary = {
            'total': len(validation_results),
            'active': 0,
            'inactive': 0,
            'not_found': 0,
            'private': 0,
            'invalid_format': 0,
            'rate_limited': 0,
            'error': 0
        }
        
        for result in validation_results:
            if result.get('is_active', False):
                summary['active'] += 1
            else:
                summary['inactive'] += 1
                status = result.get('status', 'error')
                if status in summary:
                    summary[status] += 1
        
        return summary

# Convenience function for use in views
async def validate_telegram_links(links: List[Dict[str, str]], api_id: int, api_hash: str, phone_number: str) -> List[Dict[str, any]]:
    """Validate a list of Telegram links"""
    validator = TelegramLinkValidator(api_id, api_hash, phone_number)
    
    try:
        if not await validator.start():
            logger.error("Failed to start Telegram client for validation")
            return []
        
        # Validate all links
        results = await validator.validate_links_batch(links)
        
        # Return only active links
        active_links = validator.filter_active_links(results)
        
        # Log summary
        summary = validator.get_validation_summary(results)
        logger.info(f"Validation summary: {summary}")
        
        return active_links
        
    except Exception as e:
        logger.error(f"Error during link validation: {e}")
        return []
    
    finally:
        await validator.stop()
