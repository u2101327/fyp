import os
import sys
import asyncio
import json
import time
import uuid
import warnings
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import django
from django.conf import settings

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage, User, PeerChannel
from telethon.errors import FloodWaitError, SessionPasswordNeededError
import qrcode
from io import StringIO

# OpenSearch imports
from opensearchpy import OpenSearch
from opensearchpy.exceptions import OpenSearchException

# Django imports
from socradar.models import TelegramChannel, TelegramMessage, DataLeak
from django.utils import timezone

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

class IntegratedTelegramScraper:
    def __init__(self):
        self.STATE_FILE = 'telegram_scraper_state.json'
        self.state = self.load_state()
        self.client = None
        self.continuous_scraping_active = False
        self.max_concurrent_downloads = 5
        self.batch_size = 100
        self.state_save_interval = 50
        
        # OpenSearch client
        self.opensearch_client = self.setup_opensearch()
        
        # MinIO client for raw file storage
        self.minio_client = self.setup_minio()
        
        # Media storage directory
        self.media_base_dir = Path(settings.BASE_DIR) / 'media' / 'telegram'
        self.media_base_dir.mkdir(parents=True, exist_ok=True)
        
    def setup_opensearch(self):
        """Setup OpenSearch client"""
        try:
            client = OpenSearch(
                hosts=[{'host': 'localhost', 'port': 9200}],
                http_auth=('admin', 'admin'),  # Update with your credentials
                use_ssl=False,
                verify_certs=False,
                ssl_assert_hostname=False,
                ssl_show_warn=False,
            )
            
            # Test connection
            client.info()
            print("OpenSearch connection established")
            return client
        except Exception as e:
            print(f"Failed to connect to OpenSearch: {e}")
            return None
    
    def setup_minio(self):
        """Setup MinIO client for raw file storage"""
        try:
            from scripts.storage.minio_client import LeakGuardMinioClient
            client = LeakGuardMinioClient()
            print("MinIO connection established")
            return client
        except Exception as e:
            print(f"Failed to connect to MinIO: {e}")
            return None

    def load_state(self) -> Dict[str, Any]:
        """Load scraper state from file"""
        if os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'api_id': settings.TELEGRAM_API_ID,
            'api_hash': settings.TELEGRAM_API_HASH,
            'channels': {},
            'scrape_media': True,
        }

    def save_state(self):
        """Save scraper state to file"""
        try:
            with open(self.STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"Failed to save state: {e}")

    async def download_media(self, channel_name: str, message) -> Optional[str]:
        """Download media file and return path"""
        if not message.media or not self.state['scrape_media']:
            return None

        if isinstance(message.media, MessageMediaWebPage):
            return None

        try:
            channel_media_dir = self.media_base_dir / channel_name
            channel_media_dir.mkdir(exist_ok=True)
            
            if isinstance(message.media, MessageMediaPhoto):
                original_name = getattr(message.file, 'name', None) or "photo.jpg"
                ext = "jpg"
            elif isinstance(message.media, MessageMediaDocument):
                ext = getattr(message.file, 'ext', 'bin') if message.file else 'bin'
                original_name = getattr(message.file, 'name', None) or f"document.{ext}"
            else:
                return None
            
            base_name = Path(original_name).stem
            extension = Path(original_name).suffix or f".{ext}"
            unique_filename = f"{message.id}-{base_name}{extension}"
            media_path = channel_media_dir / unique_filename
            
            # Check if file already exists
            if media_path.exists():
                return str(media_path)

            # Download with retry logic
            for attempt in range(3):
                try:
                    downloaded_path = await message.download_media(file=str(media_path))
                    if downloaded_path and Path(downloaded_path).exists():
                        return downloaded_path
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

    def save_to_opensearch(self, message_data: MessageData):
        """Save message data to OpenSearch"""
        if not self.opensearch_client:
            return False

        try:
            # Create document for OpenSearch
            doc = {
                'message_id': message_data.message_id,
                'date': message_data.date,
                'timestamp': datetime.fromisoformat(message_data.date.replace(' ', 'T')).isoformat(),
                'sender_id': message_data.sender_id,
                'sender_first_name': message_data.first_name,
                'sender_last_name': message_data.last_name,
                'sender_username': message_data.username,
                'message_text': message_data.message,
                'media_type': message_data.media_type,
                'media_path': message_data.media_path,
                'reply_to': message_data.reply_to,
                'channel_id': message_data.channel_id,
                'channel_name': message_data.channel_name,
                'scraped_at': timezone.now().isoformat(),
                'source': 'telegram_scraper'
            }

            # Index name based on channel
            index_name = f"telegram-{message_data.channel_name.lower().replace(' ', '-')}"
            
            # Create index if it doesn't exist
            if not self.opensearch_client.indices.exists(index=index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "message_id": {"type": "long"},
                            "date": {"type": "date"},
                            "timestamp": {"type": "date"},
                            "sender_id": {"type": "long"},
                            "sender_first_name": {"type": "text"},
                            "sender_last_name": {"type": "text"},
                            "sender_username": {"type": "keyword"},
                            "message_text": {"type": "text", "analyzer": "standard"},
                            "media_type": {"type": "keyword"},
                            "media_path": {"type": "keyword"},
                            "reply_to": {"type": "long"},
                            "channel_id": {"type": "keyword"},
                            "channel_name": {"type": "keyword"},
                            "scraped_at": {"type": "date"},
                            "source": {"type": "keyword"}
                        }
                    }
                }
                self.opensearch_client.indices.create(index=index_name, body=mapping)

            # Index the document
            self.opensearch_client.index(
                index=index_name,
                id=f"{message_data.channel_id}_{message_data.message_id}",
                body=doc
            )
            return True

        except Exception as e:
            print(f"Error saving to OpenSearch: {e}")
            return False

    def save_to_django_db(self, message_data: MessageData):
        """Save message data to Django database"""
        try:
            # Get or create TelegramChannel
            channel, created = TelegramChannel.objects.get_or_create(
                channel_id=message_data.channel_id,
                defaults={
                    'name': message_data.channel_name,
                    'is_active': True,
                    'created_at': timezone.now()
                }
            )

            # Create TelegramMessage
            telegram_message = TelegramMessage.objects.create(
                channel=channel,
                message_id=message_data.message_id,
                sender_id=message_data.sender_id,
                sender_first_name=message_data.first_name,
                sender_last_name=message_data.last_name,
                sender_username=message_data.username,
                message_text=message_data.message,
                media_type=message_data.media_type,
                media_path=message_data.media_path,
                reply_to=message_data.reply_to,
                message_date=datetime.fromisoformat(message_data.date.replace(' ', 'T')),
                scraped_at=timezone.now()
            )

            # Save raw message data to MinIO
            if self.minio_client:
                try:
                    message_dict = {
                        'message_id': message_data.message_id,
                        'date': message_data.date,
                        'sender_id': message_data.sender_id,
                        'first_name': message_data.first_name,
                        'last_name': message_data.last_name,
                        'username': message_data.username,
                        'message': message_data.message,
                        'media_type': message_data.media_type,
                        'media_path': message_data.media_path,
                        'reply_to': message_data.reply_to,
                        'channel_id': message_data.channel_id,
                        'channel_name': message_data.channel_name,
                        'scraped_at': timezone.now().isoformat()
                    }
                    
                    self.minio_client.save_telegram_message(
                        message_dict,
                        message_data.channel_id,
                        message_data.message_id
                    )
                    
                    # Save media file to MinIO if present
                    if message_data.media_path and os.path.exists(message_data.media_path):
                        original_filename = os.path.basename(message_data.media_path)
                        self.minio_client.save_telegram_media(
                            message_data.media_path,
                            message_data.channel_id,
                            message_data.message_id,
                            original_filename
                        )
                        
                except Exception as e:
                    print(f"Error saving to MinIO: {e}")

            # Check for potential data leaks in message content
            self.check_for_data_leaks(message_data, telegram_message)

            return telegram_message

        except Exception as e:
            print(f"Error saving to Django DB: {e}")
            return None

    def check_for_data_leaks(self, message_data: MessageData, telegram_message):
        """Check message content for potential data leaks"""
        try:
            message_text = message_data.message.lower()
            
            # Common patterns that might indicate data leaks
            leak_patterns = [
                'password', 'passwd', 'pwd',
                'api_key', 'apikey', 'api-key',
                'secret', 'token', 'key',
                'email', 'username', 'login',
                'credit card', 'card number',
                'ssn', 'social security',
                'phone number', 'mobile'
            ]
            
            # Check if message contains potential leak patterns
            for pattern in leak_patterns:
                if pattern in message_text:
                    # Create DataLeak record
                    DataLeak.objects.create(
                        source='telegram',
                        source_id=f"{message_data.channel_id}_{message_data.message_id}",
                        leak_type='potential_credential',
                        content=message_data.message,
                        detected_at=timezone.now(),
                        severity='medium',
                        status='detected',
                        telegram_message=telegram_message
                    )
                    break

        except Exception as e:
            print(f"Error checking for data leaks: {e}")

    async def scrape_channel(self, channel_id: str, channel_name: str, offset_id: int = 0):
        """Scrape messages from a Telegram channel"""
        try:
            entity = await self.client.get_entity(PeerChannel(int(channel_id)) if channel_id.startswith('-') else channel_id)
            result = await self.client.get_messages(entity, offset_id=offset_id, reverse=True, limit=0)
            total_messages = result.total

            if total_messages == 0:
                print(f"No messages found in channel {channel_name}")
                return

            print(f"Found {total_messages} messages in channel {channel_name}")

            message_batch = []
            media_tasks = []
            processed_messages = 0
            last_message_id = offset_id
            semaphore = asyncio.Semaphore(self.max_concurrent_downloads)

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
                        channel_id=channel_id,
                        channel_name=channel_name
                    )
                    
                    message_batch.append(msg_data)

                    if self.state['scrape_media'] and message.media and not isinstance(message.media, MessageMediaWebPage):
                        media_tasks.append(message)

                    last_message_id = message.id
                    processed_messages += 1

                    # Process batch
                    if len(message_batch) >= self.batch_size:
                        await self.process_message_batch(message_batch)
                        message_batch.clear()

                    # Save state periodically
                    if processed_messages % self.state_save_interval == 0:
                        self.state['channels'][channel_id] = last_message_id
                        self.save_state()

                    # Progress bar
                    progress = (processed_messages / total_messages) * 100
                    bar_length = 30
                    filled_length = int(bar_length * processed_messages // total_messages)
                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                    
                    sys.stdout.write(f"\r📄 Messages: [{bar}] {progress:.1f}% ({processed_messages}/{total_messages})")
                    sys.stdout.flush()

                except Exception as e:
                    print(f"\nError processing message {message.id}: {e}")

            # Process remaining messages
            if message_batch:
                await self.process_message_batch(message_batch)

            # Download media files
            if media_tasks:
                await self.download_media_files(channel_name, media_tasks)

            self.state['channels'][channel_id] = last_message_id
            self.save_state()
            print(f"\n✅ Completed scraping channel {channel_name}")

        except Exception as e:
            print(f"Error scraping channel {channel_name}: {e}")

    async def process_message_batch(self, message_batch: List[MessageData]):
        """Process a batch of messages"""
        for msg_data in message_batch:
            # Save to Django database
            telegram_message = self.save_to_django_db(msg_data)
            
            # Save to OpenSearch
            self.save_to_opensearch(msg_data)

    async def download_media_files(self, channel_name: str, media_tasks: List):
        """Download media files with progress tracking"""
        total_media = len(media_tasks)
        completed_media = 0
        successful_downloads = 0
        
        print(f"\n📥 Downloading {total_media} media files...")
        
        semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        
        async def download_single_media(message):
            async with semaphore:
                return await self.download_media(channel_name, message)
        
        batch_size = 10
        for i in range(0, len(media_tasks), batch_size):
            batch = media_tasks[i:i + batch_size]
            tasks = [asyncio.create_task(download_single_media(msg)) for msg in batch]
            
            for j, task in enumerate(tasks):
                try:
                    media_path = await task
                    if media_path:
                        successful_downloads += 1
                except Exception:
                    pass
                
                completed_media += 1
                progress = (completed_media / total_media) * 100
                bar_length = 30
                filled_length = int(bar_length * completed_media // total_media)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                
                sys.stdout.write(f"\r📥 Media: [{bar}] {progress:.1f}% ({completed_media}/{total_media})")
                sys.stdout.flush()
        
        print(f"\n✅ Media download complete! ({successful_downloads}/{total_media} successful)")

    def display_qr_code_ascii(self, qr_login):
        """Display QR code in ASCII format"""
        qr = qrcode.QRCode(box_size=1, border=1)
        qr.add_data(qr_login.url)
        qr.make()
        
        f = StringIO()
        qr.print_ascii(out=f)
        f.seek(0)
        print(f.read())

    async def qr_code_auth(self):
        """Authenticate using QR code"""
        print("\nChoosing QR Code authentication...")
        print("Please scan the QR code with your Telegram app:")
        print("1. Open Telegram on your phone")
        print("2. Go to Settings > Devices > Scan QR")
        print("3. Scan the code below\n")
        
        qr_login = await self.client.qr_login()
        self.display_qr_code_ascii(qr_login)
        
        try:
            await qr_login.wait()
            print("\n✅ Successfully logged in via QR code!")
            return True
        except SessionPasswordNeededError:
            password = input("Two-factor authentication enabled. Enter your password: ")
            await self.client.sign_in(password=password)
            print("\n✅ Successfully logged in with 2FA!")
            return True
        except Exception as e:
            print(f"\n❌ QR code authentication failed: {e}")
            return False

    async def phone_auth(self):
        """Authenticate using phone number"""
        phone = input("Enter your phone number: ")
        await self.client.send_code_request(phone)
        code = input("Enter the code you received: ")
        
        try:
            await self.client.sign_in(phone, code)
            print("\n✅ Successfully logged in via phone!")
            return True
        except SessionPasswordNeededError:
            password = input("Two-factor authentication enabled. Enter your password: ")
            await self.client.sign_in(password=password)
            print("\n✅ Successfully logged in with 2FA!")
            return True
        except Exception as e:
            print(f"\n❌ Phone authentication failed: {e}")
            return False

    async def initialize_client(self):
        """Initialize Telegram client"""
        if not all([self.state.get('api_id'), self.state.get('api_hash')]):
            print("\n=== API Configuration Required ===")
            print("Using API credentials from Django settings...")
            self.state['api_id'] = settings.TELEGRAM_API_ID
            self.state['api_hash'] = settings.TELEGRAM_API_HASH
            self.save_state()

        self.client = TelegramClient('telegram_session', self.state['api_id'], self.state['api_hash'])
        
        try:
            await self.client.connect()
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
        
        if not await self.client.is_user_authorized():
            print("\n=== Choose Authentication Method ===")
            print("[1] QR Code (Recommended - No phone number needed)")
            print("[2] Phone Number (Traditional method)")
            
            while True:
                choice = input("Enter your choice (1 or 2): ").strip()
                if choice in ['1', '2']:
                    break
                print("Please enter 1 or 2")
            
            success = await self.qr_code_auth() if choice == '1' else await self.phone_auth()
                
            if not success:
                print("Authentication failed. Please try again.")
                await self.client.disconnect()
                return False
        else:
            print("✅ Already authenticated!")
            
        return True

    async def add_channel(self, channel_id: str, channel_name: str):
        """Add a channel to scrape"""
        try:
            # Test if we can access the channel
            entity = await self.client.get_entity(PeerChannel(int(channel_id)) if channel_id.startswith('-') else channel_id)
            channel_title = getattr(entity, 'title', channel_name)
            
            self.state['channels'][channel_id] = 0
            self.save_state()
            
            print(f"✅ Added channel: {channel_title} (ID: {channel_id})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to add channel {channel_id}: {e}")
            return False

    async def list_available_channels(self):
        """List channels available to the account"""
        try:
            print("\n📋 Available channels:")
            count = 1
            channels = []
            
            async for dialog in self.client.iter_dialogs():
                if dialog.id != 777000:  # Skip Telegram's own channel
                    title = getattr(dialog.entity, 'title', f'Channel {dialog.id}')
                    print(f"[{count}] {title} (ID: {dialog.id})")
                    channels.append((str(dialog.id), title))
                    count += 1
            
            return channels
            
        except Exception as e:
            print(f"Error listing channels: {e}")
            return []

    async def run_scraper(self, channel_ids: List[str] = None):
        """Run the scraper for specified channels or all channels"""
        if not await self.initialize_client():
            print("Failed to initialize client. Exiting.")
            return

        try:
            if not channel_ids:
                # Scrape all channels in state
                if not self.state['channels']:
                    print("No channels configured. Please add channels first.")
                    return
                
                for channel_id in self.state['channels']:
                    # Get channel name from Django DB or use ID
                    try:
                        channel = TelegramChannel.objects.get(channel_id=channel_id)
                        channel_name = channel.name
                    except TelegramChannel.DoesNotExist:
                        channel_name = f"Channel_{channel_id}"
                    
                    print(f"\n🚀 Scraping channel: {channel_name}")
                    await self.scrape_channel(channel_id, channel_name, self.state['channels'][channel_id])
            else:
                # Scrape specified channels
                for channel_id in channel_ids:
                    try:
                        channel = TelegramChannel.objects.get(channel_id=channel_id)
                        channel_name = channel.name
                    except TelegramChannel.DoesNotExist:
                        channel_name = f"Channel_{channel_id}"
                    
                    print(f"\n🚀 Scraping channel: {channel_name}")
                    await self.scrape_channel(channel_id, channel_name, self.state['channels'].get(channel_id, 0))

        finally:
            if self.client:
                await self.client.disconnect()

    async def interactive_mode(self):
        """Run scraper in interactive mode"""
        if not await self.initialize_client():
            print("Failed to initialize client. Exiting.")
            return

        try:
            while True:
                print("\n" + "="*50)
                print("           INTEGRATED TELEGRAM SCRAPER")
                print("="*50)
                print("[S] Scrape all channels")
                print("[A] Add new channel")
                print("[L] List available channels")
                print("[V] View configured channels")
                print("[R] Remove channel")
                print("[M] Toggle media scraping")
                print("[Q] Quit")
                print("="*50)

                choice = input("Enter your choice: ").lower().strip()
                
                if choice == 's':
                    await self.run_scraper()
                    
                elif choice == 'a':
                    channel_id = input("Enter channel ID (e.g., -1001234567890): ").strip()
                    channel_name = input("Enter channel name: ").strip()
                    await self.add_channel(channel_id, channel_name)
                    
                elif choice == 'l':
                    await self.list_available_channels()
                    
                elif choice == 'v':
                    if not self.state['channels']:
                        print("No channels configured")
                    else:
                        print("\nConfigured channels:")
                        for i, (channel_id, last_id) in enumerate(self.state['channels'].items(), 1):
                            try:
                                channel = TelegramChannel.objects.get(channel_id=channel_id)
                                print(f"[{i}] {channel.name} (ID: {channel_id}, Last: {last_id})")
                            except TelegramChannel.DoesNotExist:
                                print(f"[{i}] Channel_{channel_id} (ID: {channel_id}, Last: {last_id})")
                    
                elif choice == 'r':
                    if not self.state['channels']:
                        print("No channels to remove")
                        continue
                    
                    print("\nConfigured channels:")
                    channels_list = list(self.state['channels'].keys())
                    for i, channel_id in enumerate(channels_list, 1):
                        try:
                            channel = TelegramChannel.objects.get(channel_id=channel_id)
                            print(f"[{i}] {channel.name} (ID: {channel_id})")
                        except TelegramChannel.DoesNotExist:
                            print(f"[{i}] Channel_{channel_id} (ID: {channel_id})")
                    
                    try:
                        choice_num = int(input("Enter channel number to remove: "))
                        if 1 <= choice_num <= len(channels_list):
                            channel_id = channels_list[choice_num - 1]
                            del self.state['channels'][channel_id]
                            self.save_state()
                            print(f"✅ Removed channel {channel_id}")
                        else:
                            print("Invalid channel number")
                    except ValueError:
                        print("Invalid input")
                    
                elif choice == 'm':
                    self.state['scrape_media'] = not self.state['scrape_media']
                    self.save_state()
                    print(f"\n✅ Media scraping {'enabled' if self.state['scrape_media'] else 'disabled'}")
                    
                elif choice == 'q':
                    print("\n👋 Goodbye!")
                    break
                    
                else:
                    print("Invalid option")

        finally:
            if self.client:
                await self.client.disconnect()

async def main():
    """Main function"""
    scraper = IntegratedTelegramScraper()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--interactive':
            await scraper.interactive_mode()
        else:
            # Scrape specific channels
            channel_ids = sys.argv[1:]
            await scraper.run_scraper(channel_ids)
    else:
        # Default: scrape all configured channels
        await scraper.run_scraper()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")
        sys.exit()
