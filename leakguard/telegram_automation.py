#!/usr/bin/env python3
"""
Telegram Data Collection Automation System
Automatically fetches Telegram links from GitHub, joins channels, and collects data
"""

import os
import re
import asyncio
import requests
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass

# Telegram API
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Channel, Chat, User
from telethon.errors import FloodWaitError, ChannelPrivateError, ChatAdminRequiredError

# Django setup
import django
from django.conf import settings
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from socradar.models import TelegramChannel, TelegramMessage, DataLeak

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TelegramConfig:
    """Configuration for Telegram API"""
    api_id: int
    api_hash: str
    phone_number: str
    session_name: str = 'leakguard_session'

class GitHubLinkExtractor:
    """Extract Telegram links from GitHub repository"""
    
    def __init__(self):
        self.github_url = "https://raw.githubusercontent.com/fastfire/deepdarkCTI/main/telegram_infostealer.md"
    
    def fetch_telegram_links(self) -> List[Dict[str, str]]:
        """Fetch and parse Telegram links from GitHub"""
        try:
            logger.info("Fetching Telegram links from GitHub...")
            response = requests.get(self.github_url, timeout=30)
            response.raise_for_status()
            
            content = response.text
            links = self._parse_telegram_links(content)
            logger.info(f"Found {len(links)} Telegram links")
            return links
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch GitHub content: {e}")
            return []
    
    def _parse_telegram_links(self, content: str) -> List[Dict[str, str]]:
        """Parse Telegram links from markdown content"""
        links = []
        
        # Regex patterns for different Telegram link formats
        patterns = [
            r'https://t\.me/([a-zA-Z0-9_]+)',
            r'@([a-zA-Z0-9_]+)',
            r't\.me/([a-zA-Z0-9_]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                username = match.strip('@')
                if username and len(username) > 3:  # Basic validation
                    links.append({
                        'username': username,
                        'url': f'https://t.me/{username}',
                        'source': 'deepdarkCTI'
                    })
        
        # Remove duplicates
        unique_links = []
        seen = set()
        for link in links:
            if link['username'] not in seen:
                unique_links.append(link)
                seen.add(link['username'])
        
        return unique_links

class DataParser:
    """Parse leaked data from Telegram messages"""
    
    def __init__(self):
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.password_pattern = re.compile(r':([^:\s\n]+)')
        self.domain_pattern = re.compile(r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
    
    def parse_message(self, text: str) -> List[Dict[str, str]]:
        """Parse leaked credentials from message text"""
        if not text:
            return []
        
        leaks = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Check if line contains email:password format
            if ':' in line and '@' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    email = parts[0].strip()
                    password = parts[1].strip()
                    
                    # Validate email format
                    if self.email_pattern.match(email):
                        leaks.append({
                            'email': email,
                            'password': password,
                            'domain': self._extract_domain(email),
                            'raw_data': line,
                            'type': 'email_password'
                        })
        
        return leaks
    
    def _extract_domain(self, email: str) -> str:
        """Extract domain from email"""
        if '@' in email:
            return email.split('@')[1]
        return ''

class TelegramCollector:
    """Main class for collecting data from Telegram channels"""
    
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.client = TelegramClient(
            config.session_name,
            config.api_id,
            config.api_hash
        )
        self.data_parser = DataParser()
        self.processed_messages = set()
    
    async def start(self):
        """Start the Telegram client"""
        await self.client.start(phone=self.config.phone_number)
        logger.info("Telegram client started successfully")
    
    async def stop(self):
        """Stop the Telegram client"""
        await self.client.disconnect()
        logger.info("Telegram client stopped")
    
    async def join_channels(self, links: List[Dict[str, str]]) -> List[TelegramChannel]:
        """Join Telegram channels and create database records"""
        joined_channels = []
        
        for link_data in links:
            try:
                username = link_data['username']
                url = link_data['url']
                
                logger.info(f"Attempting to join channel: @{username}")
                
                # Try to join the channel
                try:
                    await self.client(JoinChannelRequest(username))
                    logger.info(f"Successfully joined @{username}")
                except (ChannelPrivateError, ChatAdminRequiredError) as e:
                    logger.warning(f"Cannot join @{username}: {e}")
                    continue
                except FloodWaitError as e:
                    logger.warning(f"Rate limited for @{username}, waiting {e.seconds} seconds")
                    await asyncio.sleep(e.seconds)
                    continue
                
                # Get channel info
                try:
                    entity = await self.client.get_entity(username)
                    channel_name = getattr(entity, 'title', username)
                    description = getattr(entity, 'about', '')
                    
                    # Create or update channel in database
                    channel, created = TelegramChannel.objects.get_or_create(
                        username=username,
                        defaults={
                            'name': channel_name,
                            'url': url,
                            'description': description,
                            'is_active': True
                        }
                    )
                    
                    if created:
                        logger.info(f"Created new channel record: @{username}")
                    else:
                        logger.info(f"Channel already exists: @{username}")
                    
                    joined_channels.append(channel)
                    
                except Exception as e:
                    logger.error(f"Failed to get entity info for @{username}: {e}")
                    continue
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing channel {link_data}: {e}")
                continue
        
        return joined_channels
    
    async def collect_messages(self, channels: List[TelegramChannel], limit: int = 100):
        """Collect messages from joined channels"""
        for channel in channels:
            try:
                logger.info(f"Collecting messages from @{channel.username}")
                
                # Get channel entity
                entity = await self.client.get_entity(channel.username)
                
                # Get recent messages
                messages = await self.client.get_messages(
                    entity,
                    limit=limit,
                    reverse=False
                )
                
                new_messages_count = 0
                for message in messages:
                    if not message.text:
                        continue
                    
                    # Check if message already processed
                    message_key = f"{channel.id}_{message.id}"
                    if message_key in self.processed_messages:
                        continue
                    
                    # Save message to database
                    try:
                        telegram_msg, created = TelegramMessage.objects.get_or_create(
                            channel=channel,
                            message_id=message.id,
                            defaults={
                                'text': message.text,
                                'date': message.date,
                                'sender_id': message.sender_id,
                                'sender_username': getattr(message.sender, 'username', '') if message.sender else '',
                                'is_forwarded': message.forward is not None,
                                'forwarded_from': getattr(message.forward, 'from_name', '') if message.forward else '',
                                'media_type': message.media.__class__.__name__ if message.media else '',
                            }
                        )
                        
                        if created:
                            new_messages_count += 1
                            self.processed_messages.add(message_key)
                            
                            # Parse leaked data from message
                            await self._process_message_data(telegram_msg)
                    
                    except Exception as e:
                        logger.error(f"Error saving message {message.id}: {e}")
                        continue
                
                # Update channel last scanned time
                channel.last_scanned = datetime.now(timezone.utc)
                channel.save()
                
                logger.info(f"Collected {new_messages_count} new messages from @{channel.username}")
                
            except Exception as e:
                logger.error(f"Error collecting messages from @{channel.username}: {e}")
                continue
    
    async def _process_message_data(self, telegram_msg: TelegramMessage):
        """Process message data and extract leaked credentials"""
        try:
            leaks = self.data_parser.parse_message(telegram_msg.text)
            
            for leak_data in leaks:
                # Determine severity based on data type
                severity = 'medium'
                if leak_data['type'] == 'email_password':
                    if any(domain in leak_data['domain'].lower() for domain in ['edu', 'gov', 'org']):
                        severity = 'high'
                    if len(leak_data['password']) > 12:
                        severity = 'critical'
                
                # Create data leak record
                DataLeak.objects.create(
                    email=leak_data.get('email', ''),
                    username=leak_data.get('username', ''),
                    password=leak_data.get('password', ''),
                    domain=leak_data.get('domain', ''),
                    source=f"Telegram @{telegram_msg.channel.username}",
                    source_url=telegram_msg.channel.url,
                    leak_date=telegram_msg.date,
                    severity=severity,
                    telegram_message=telegram_msg,
                    raw_data=leak_data['raw_data'],
                    is_processed=True
                )
            
            if leaks:
                logger.info(f"Extracted {len(leaks)} credential leaks from message {telegram_msg.message_id}")
        
        except Exception as e:
            logger.error(f"Error processing message data: {e}")

async def main():
    """Main automation function"""
    # Configuration - Replace with your actual values
    config = TelegramConfig(
        api_id=int(os.getenv('TELEGRAM_API_ID', 'YOUR_API_ID')),
        api_hash=os.getenv('TELEGRAM_API_HASH', 'YOUR_API_HASH'),
        phone_number=os.getenv('TELEGRAM_PHONE', 'YOUR_PHONE_NUMBER')
    )
    
    # Initialize components
    link_extractor = GitHubLinkExtractor()
    collector = TelegramCollector(config)
    
    try:
        # Start Telegram client
        await collector.start()
        
        # Fetch Telegram links from GitHub
        links = link_extractor.fetch_telegram_links()
        if not links:
            logger.error("No Telegram links found")
            return
        
        # Join channels
        channels = await collector.join_channels(links)
        if not channels:
            logger.error("No channels joined successfully")
            return
        
        # Collect messages from channels
        await collector.collect_messages(channels, limit=50)
        
        logger.info("Automation completed successfully")
    
    except Exception as e:
        logger.error(f"Automation failed: {e}")
    
    finally:
        await collector.stop()

if __name__ == "__main__":
    asyncio.run(main())
