"""
Telegram Scraper for LeakGuard
Handles scraping messages and media from Telegram channels
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')

import django
django.setup()

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from django.utils import timezone
from django.conf import settings
from asgiref.sync import sync_to_async

# Import our models and MinIO client
from .models import TelegramChannel, TelegramMessage
from scripts.storage.minio_client import LeakGuardMinioClient

logger = logging.getLogger(__name__)

class TelegramScraper:
    """Telegram scraper for downloading messages and media"""
    
    def __init__(self):
        """Initialize the scraper"""
        self.client = None
        self.minio_client = LeakGuardMinioClient()
        
        # Get API credentials
        self.api_id = getattr(settings, 'TELEGRAM_API_ID', None) or os.getenv('TELEGRAM_API_ID')
        self.api_hash = getattr(settings, 'TELEGRAM_API_HASH', None) or os.getenv('TELEGRAM_API_HASH')
        
        if not self.api_id or not self.api_hash:
            raise ValueError("Telegram API credentials not configured")
        
        # Media storage directory
        self.media_base_dir = Path(settings.BASE_DIR) / 'media' / 'telegram'
        self.media_base_dir.mkdir(parents=True, exist_ok=True)
    
    async def connect(self):
        """Connect to Telegram"""
        try:
            self.client = TelegramClient("leakguard_session", int(self.api_id), self.api_hash)
            await self.client.start()
            logger.info("Connected to Telegram")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Telegram: {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client:
            await self.client.disconnect()
            logger.info("Disconnected from Telegram")
    
    async def scrape_channel_async(self, channel_username: str, offset_id: int = 0, channel_id: int = None, progress_callback=None) -> Dict[str, Any]:
        """
        Scrape messages from a Telegram channel
        
        Args:
            channel_username: Telegram channel username
            offset_id: Last scraped message ID for incremental scraping
            channel_id: Database channel ID
            
        Returns:
            Dict with scraping results
        """
        try:
            # Connect to Telegram
            if not await self.connect():
                return {'success': False, 'error': 'Failed to connect to Telegram'}
            
            # Get channel entity
            try:
                entity = await self.client.get_entity(channel_username)
            except Exception as e:
                return {'success': False, 'error': f'Channel not found: {str(e)}'}
            
            # Get or create channel in database
            if channel_id:
                try:
                    channel = await sync_to_async(TelegramChannel.objects.get)(id=channel_id)
                except TelegramChannel.DoesNotExist:
                    return {'success': False, 'error': 'Channel not found in database'}
            else:
                channel, created = await sync_to_async(TelegramChannel.objects.get_or_create)(
                    username=channel_username,
                    defaults={
                        'name': getattr(entity, 'title', channel_username),
                        'url': f'https://t.me/{channel_username}',
                        'is_active': True
                    }
                )
            
            messages_count = 0
            files_count = 0
            last_message_id = offset_id
            
            # Get total message count for progress tracking
            try:
                total_messages = await self.client.get_messages(entity, limit=0)
                total_count = total_messages.total if hasattr(total_messages, 'total') else 0
            except:
                total_count = 0
            
            # Call progress callback with initial info
            if progress_callback:
                progress_callback(0, total_count, 0, f"Found {total_count} messages to process")
            
            # Scrape messages
            async for message in self.client.iter_messages(entity, offset_id=offset_id, reverse=True):
                try:
                    # Create message record
                    message_obj = await sync_to_async(TelegramMessage.objects.create)(
                        channel=channel,
                        message_id=message.id,
                        date=message.date,
                        sender_id=getattr(message.sender, 'id', None) if message.sender else None,
                        sender_username=getattr(message.sender, 'username', '') if message.sender else '',
                        text=message.text or '',
                        is_forwarded=bool(message.fwd_from),
                        forwarded_from=getattr(message.fwd_from, 'from_name', '') if message.fwd_from else '',
                        media_type='photo' if isinstance(message.media, MessageMediaPhoto) else 'document' if isinstance(message.media, MessageMediaDocument) else 'other' if message.media else '',
                        has_links=bool(message.text and ('http' in message.text or 't.me' in message.text))
                    )
                    
                    messages_count += 1
                    last_message_id = message.id
                    
                    # Handle media files
                    if message.media:
                        media_path = await self.download_media(channel_username, message)
                        if media_path:
                            message_obj.file_path = media_path
                            await sync_to_async(message_obj.save)()
                            files_count += 1
                            
                            # Trigger file processing task
                            try:
                                from .tasks import process_file_task
                                process_file_task.delay(
                                    message_id=message_obj.id,
                                    s3_uri=media_path,
                                    channel_username=channel_username
                                )
                                logger.info(f"Queued file processing for {media_path}")
                            except Exception as e:
                                logger.warning(f"Failed to queue file processing: {e}")
                    
                    # Update progress every 5 messages
                    if progress_callback and messages_count % 5 == 0:
                        status = f"Processing message {messages_count}/{total_count if total_count > 0 else '?'}"
                        progress_callback(messages_count, total_count, files_count, status)
                    
                    # Log progress every 10 messages
                    if messages_count % 10 == 0:
                        logger.info(f"Scraped {messages_count} messages from @{channel_username}")
                
                except Exception as e:
                    logger.error(f"Error processing message {message.id}: {str(e)}")
                    continue
            
            # Final progress update
            if progress_callback:
                progress_callback(messages_count, total_count, files_count, f"Completed processing {messages_count} messages")
            
            # Update channel statistics
            link_count = await sync_to_async(TelegramMessage.objects.filter(channel=channel).count)()
            channel.link_count = link_count
            await sync_to_async(channel.save)()
            
            logger.info(f"Completed scraping @{channel_username}: {messages_count} messages, {files_count} files")
            
            return {
                'success': True,
                'messages_count': messages_count,
                'files_count': files_count,
                'last_message_id': last_message_id
            }
            
        except Exception as e:
            logger.error(f"Error scraping channel @{channel_username}: {str(e)}")
            return {'success': False, 'error': str(e)}
        
        finally:
            await self.disconnect()
    
    async def download_media(self, channel_username: str, message) -> Optional[str]:
        """
        Download media from a message and upload to MinIO
        
        Args:
            channel_username: Channel username
            message: Telegram message object
            
        Returns:
            MinIO path if successful, None otherwise
        """
        try:
            if not message.media:
                return None
            
            # Get media info
            if isinstance(message.media, MessageMediaPhoto):
                media_type = 'photo'
                original_name = f"photo_{message.id}.jpg"
            elif isinstance(message.media, MessageMediaDocument):
                media_type = 'document'
                # Get filename from document attributes
                original_name = f"document_{message.id}"
                if hasattr(message.media.document, 'attributes') and message.media.document.attributes:
                    for attr in message.media.document.attributes:
                        if hasattr(attr, 'file_name') and attr.file_name:
                            original_name = attr.file_name
                            break
            else:
                return None
            
            # Create local directory
            channel_dir = self.media_base_dir / channel_username
            channel_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{message.id}_{original_name}"
            local_path = channel_dir / unique_filename
            
            # Download media
            downloaded_path = await message.download_media(file=str(local_path))
            if not downloaded_path or not Path(downloaded_path).exists():
                return None
            
            # Upload to MinIO
            minio_path = self.minio_client.save_telegram_media(
                downloaded_path,
                channel_username,
                message.id,
                original_name
            )
            
            # Clean up local file
            try:
                os.remove(downloaded_path)
            except:
                pass
            
            return minio_path
            
        except Exception as e:
            logger.error(f"Error downloading media from message {message.id}: {str(e)}")
            return None

def run_sync_scraping(channel_username: str, offset_id: int = 0) -> Dict[str, Any]:
    """
    Synchronous wrapper for scraping
    
    Args:
        channel_username: Telegram channel username
        offset_id: Last scraped message ID
        
    Returns:
        Dict with scraping results
    """
    scraper = TelegramScraper()
    return asyncio.run(scraper.scrape_channel_async(channel_username, offset_id))
