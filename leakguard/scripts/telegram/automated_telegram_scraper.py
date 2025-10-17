"""
Automated Telegram Scraper for LeakGuard
Modified version of telegram-scraper.py that works without user input
"""

import os
import sys
import asyncio
import json
import time
import uuid
import warnings
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage, User, PeerChannel
from telethon.errors import FloodWaitError, SessionPasswordNeededError

# Django imports
from socradar.models import TelegramChannel, TelegramMessage
from django.utils import timezone
from django.conf import settings

# MinIO imports
from scripts.storage.minio_client import LeakGuardMinioClient

warnings.filterwarnings("ignore", message="Using async sessions support is an experimental feature")

@dataclass
class MessageData:
    message_id: int
    date: str
    sender_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    username: Optional[str]
    message: str
    media_type: Optional[str]
    media_path: Optional[str]
    reply_to: Optional[int]
    channel_id: str
    channel_name: str

class AutomatedTelegramScraper:
    """Automated Telegram scraper that works without user input"""
    
    def __init__(self):
        self.client = None
        self.max_concurrent_downloads = 5
        self.batch_size = 100
        self.state_save_interval = 50
        
        # MinIO client for file storage
        self.minio_client = LeakGuardMinioClient()
        
        # Media storage directory
        self.media_base_dir = Path(settings.BASE_DIR) / 'media' / 'telegram'
        self.media_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Get API credentials from Django settings
        self.api_id = getattr(settings, 'TELEGRAM_API_ID', None)
        self.api_hash = getattr(settings, 'TELEGRAM_API_HASH', None)
        
        if not self.api_id or not self.api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in Django settings")

    async def download_media(self, channel_name: str, message) -> Optional[str]:
        """Download media file and save to MinIO"""
        if not message.media or isinstance(message.media, MessageMediaWebPage):
            return None

        try:
            # Create media directory for this channel
            channel_media_dir = self.media_base_dir / channel_name
            channel_media_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine file extension and name
            if isinstance(message.media, MessageMediaPhoto):
                original_name = "photo.jpg"
                ext = "jpg"
            elif isinstance(message.media, MessageMediaDocument):
                ext = getattr(message.file, 'ext', 'bin') if message.file else 'bin'
                original_name = getattr(message.file, 'name', None) or f"document.{ext}"
            else:
                return None
            
            # Create unique filename
            base_name = Path(original_name).stem
            extension = Path(original_name).suffix or f".{ext}"
            unique_filename = f"{message.id}-{base_name}{extension}"
            media_path = channel_media_dir / unique_filename
            
            # Download the media file
            for attempt in range(3):
                try:
                    downloaded_path = await message.download_media(file=str(media_path))
                    if downloaded_path and Path(downloaded_path).exists():
                        # Upload to MinIO
                        s3_uri = await self.upload_to_minio(downloaded_path, channel_name, message.id, original_name)
                        
                        # Clean up local file
                        try:
                            os.remove(downloaded_path)
                        except:
                            pass
                        
                        return s3_uri
                    else:
                        return None
                        
                except FloodWaitError as e:
                    if attempt < 2:
                        await asyncio.sleep(e.seconds)
                    else:
                        return None
                except Exception:
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        return None
            
            return None
            
        except Exception:
            return None

    async def upload_to_minio(self, local_path: str, channel_name: str, message_id: int, original_filename: str) -> Optional[str]:
        """Upload file to MinIO and return the MinIO path"""
        try:
            # Save to MinIO using our client
            minio_path = self.minio_client.save_telegram_media(
                local_path,
                channel_name,
                message_id,
                original_filename
            )
            return minio_path
            
        except Exception as e:
            print(f"Error uploading to MinIO: {e}")
            return None

    async def scrape_channel(self, channel_username: str, offset_id: int = 0):
        """Scrape messages from a specific channel"""
        try:
            # Get channel entity
            entity = await self.client.get_entity(channel_username)
            
            # Get total message count
            result = await self.client.get_messages(entity, offset_id=offset_id, reverse=True, limit=0)
            total_messages = result.total

            if total_messages == 0:
                print(f"No messages found in channel {channel_username}")
                return

            print(f"Found {total_messages} messages in channel {channel_username}")

            message_batch = []
            media_tasks = []
            processed_messages = 0
            last_message_id = offset_id
            semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

            # Get or create channel in database
            channel, created = TelegramChannel.objects.get_or_create(
                username=channel_username,
                defaults={
                    'name': getattr(entity, 'title', channel_username),
                    'url': f'https://t.me/{channel_username}',
                    'is_active': True
                }
            )

            async for message in self.client.iter_messages(entity, offset_id=offset_id, reverse=True):
                try:
                    sender = await message.get_sender()
                    
                    msg_data = MessageData(
                        message_id=message.id,
                        date=message.date.strftime('%Y-%m-%d %H:%M:%S'),
                        sender_id=message.sender_id,
                        first_name=getattr(sender, 'first_name', None) if isinstance(sender, User) else None,
                        last_name=getattr(sender, 'last_name', None) if isinstance(sender, User) else None,
                        username=getattr(sender, 'username', None) if isinstance(sender, User) else None,
                        message=message.message or '',
                        media_type=message.media.__class__.__name__ if message.media else None,
                        media_path=None,
                        reply_to=message.reply_to_msg_id if message.reply_to else None,
                        channel_id=channel_username,
                        channel_name=channel.name
                    )
                    
                    message_batch.append(msg_data)

                    # Add media download task if media exists
                    if message.media and not isinstance(message.media, MessageMediaWebPage):
                        media_tasks.append(message)

                    last_message_id = message.id
                    processed_messages += 1

                    # Process batch when it reaches batch_size
                    if len(message_batch) >= self.batch_size:
                        await self.process_message_batch(message_batch, channel)
                        message_batch.clear()

                    # Progress update
                    if processed_messages % self.state_save_interval == 0:
                        progress = (processed_messages / total_messages) * 100
                        print(f"Progress: {progress:.1f}% ({processed_messages}/{total_messages})")

                except Exception as e:
                    print(f"Error processing message {message.id}: {e}")

            # Process remaining messages
            if message_batch:
                await self.process_message_batch(message_batch, channel)

            # Download media files
            if media_tasks:
                await self.download_media_files(channel_username, media_tasks)

            # Update channel last scanned time
            channel.last_scanned = timezone.now()
            channel.save()

            print(f"Completed scraping channel {channel_username}")

        except Exception as e:
            print(f"Error scraping channel {channel_username}: {e}")

    async def process_message_batch(self, message_batch: List[MessageData], channel: TelegramChannel):
        """Process a batch of messages and save to database"""
        for msg_data in message_batch:
            try:
                # Create or get TelegramMessage
                telegram_message, created = TelegramMessage.objects.get_or_create(
                    channel=channel,
                    message_id=msg_data.message_id,
                    defaults={
                        'text': msg_data.message,
                        'date': datetime.fromisoformat(msg_data.date.replace(' ', 'T')),
                        'sender_id': msg_data.sender_id,
                        'sender_username': msg_data.username or '',
                        'is_forwarded': False,
                        'forwarded_from': '',
                        'media_type': msg_data.media_type or '',
                        'file_path': msg_data.media_path or ''
                    }
                )

                # Save raw message data to MinIO
                if self.minio_client:
                    try:
                        message_dict = {
                            'message_id': msg_data.message_id,
                            'date': msg_data.date,
                            'sender_id': msg_data.sender_id,
                            'first_name': msg_data.first_name,
                            'last_name': msg_data.last_name,
                            'username': msg_data.username,
                            'message': msg_data.message,
                            'media_type': msg_data.media_type,
                            'media_path': msg_data.media_path,
                            'reply_to': msg_data.reply_to,
                            'channel_id': msg_data.channel_id,
                            'channel_name': msg_data.channel_name,
                            'scraped_at': timezone.now().isoformat()
                        }
                        
                        self.minio_client.save_telegram_message(
                            message_dict,
                            msg_data.channel_id,
                            msg_data.message_id
                        )
                        
                    except Exception as e:
                        print(f"Error saving to MinIO: {e}")

            except Exception as e:
                print(f"Error processing message {msg_data.message_id}: {e}")

    async def download_media_files(self, channel_name: str, media_tasks: List):
        """Download media files concurrently"""
        if not media_tasks:
            return

        total_media = len(media_tasks)
        completed_media = 0
        successful_downloads = 0
        
        print(f"Downloading {total_media} media files...")
        
        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        
        async def download_single_media(message):
            async with semaphore:
                return await self.download_media(channel_name, message)
        
        # Process media in batches
        batch_size = 10
        for i in range(0, len(media_tasks), batch_size):
            batch = media_tasks[i:i + batch_size]
            tasks = [asyncio.create_task(download_single_media(msg)) for msg in batch]
            
            for j, task in enumerate(tasks):
                try:
                    media_path = await task
                    if media_path:
                        # Update message with media path
                        message = batch[j]
                        try:
                            telegram_message = TelegramMessage.objects.get(
                                channel__username=channel_name,
                                message_id=message.id
                            )
                            telegram_message.file_path = media_path
                            telegram_message.save()
                            successful_downloads += 1
                        except TelegramMessage.DoesNotExist:
                            pass
                except Exception:
                    pass
                
                completed_media += 1
                progress = (completed_media / total_media) * 100
                print(f"Media progress: {progress:.1f}% ({completed_media}/{total_media})")
        
        print(f"Media download complete! ({successful_downloads}/{total_media} successful)")

    async def initialize_client(self):
        """Initialize Telegram client with stored session"""
        try:
            # Create session file path
            session_file = Path(settings.BASE_DIR) / 'temp' / 'telegram_session'
            session_file.parent.mkdir(exist_ok=True)
            
            self.client = TelegramClient(str(session_file), self.api_id, self.api_hash)
            
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                print("Telegram client not authorized. Please run the interactive scraper first to authenticate.")
                return False
            
            print("Telegram client initialized successfully")
            return True
            
        except Exception as e:
            print(f"Failed to initialize Telegram client: {e}")
            return False

    async def scrape_channels(self, channel_usernames: List[str]):
        """Scrape multiple channels"""
        if not await self.initialize_client():
            raise Exception("Failed to initialize Telegram client")
        
        try:
            for i, channel_username in enumerate(channel_usernames, 1):
                print(f"[{i}/{len(channel_usernames)}] Scraping channel: {channel_username}")
                await self.scrape_channel(channel_username)
            
            print(f"Completed scraping {len(channel_usernames)} channels")
            
        finally:
            if self.client:
                await self.client.disconnect()

    async def run_scraping(self, channel_usernames: List[str] = None):
        """Main method to run scraping"""
        if channel_usernames is None:
            # Get all active channels from database
            active_channels = TelegramChannel.objects.filter(is_active=True)
            channel_usernames = list(active_channels.values_list('username', flat=True))
        
        if not channel_usernames:
            print("No channels to scrape")
            return
        
        print(f"Starting automated scraping for {len(channel_usernames)} channels")
        await self.scrape_channels(channel_usernames)

# Convenience function for use in views
async def run_automated_scraping(channel_usernames: List[str] = None):
    """Run automated scraping for specified channels"""
    scraper = AutomatedTelegramScraper()
    await scraper.run_scraping(channel_usernames)

# Synchronous wrapper for use in Django views
def run_automated_scraping_sync(channel_usernames: List[str] = None):
    """Synchronous wrapper for automated scraping"""
    asyncio.run(run_automated_scraping(channel_usernames))

