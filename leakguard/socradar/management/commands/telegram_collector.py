"""
Django management command for Telegram data collection
Usage: python manage.py telegram_collector [--limit 100] [--channels-only] [--messages-only]
"""

import asyncio
import os
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from datetime import datetime, timezone

from socradar.models import TelegramChannel, TelegramMessage, DataLeak

# Import our automation components
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from telegram_automation import (
    GitHubLinkExtractor, 
    TelegramCollector, 
    TelegramConfig,
    DataParser
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Collect data from Telegram channels automatically'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Number of messages to collect per channel (default: 100)'
        )
        parser.add_argument(
            '--channels-only',
            action='store_true',
            help='Only join channels, do not collect messages'
        )
        parser.add_argument(
            '--messages-only',
            action='store_true',
            help='Only collect messages from existing channels'
        )
        parser.add_argument(
            '--api-id',
            type=int,
            help='Telegram API ID (can also be set via TELEGRAM_API_ID env var)'
        )
        parser.add_argument(
            '--api-hash',
            type=str,
            help='Telegram API Hash (can also be set via TELEGRAM_API_HASH env var)'
        )
        parser.add_argument(
            '--phone',
            type=str,
            help='Phone number (can also be set via TELEGRAM_PHONE env var)'
        )

    def handle(self, *args, **options):
        # Get configuration
        api_id = options.get('api_id') or os.getenv('TELEGRAM_API_ID')
        api_hash = options.get('api_hash') or os.getenv('TELEGRAM_API_HASH')
        phone = options.get('phone') or os.getenv('TELEGRAM_PHONE')

        if not all([api_id, api_hash, phone]):
            raise CommandError(
                'Missing required configuration. Please provide:\n'
                '--api-id, --api-hash, --phone\n'
                'OR set environment variables: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE'
            )

        try:
            api_id = int(api_id)
        except ValueError:
            raise CommandError('API ID must be a valid integer')

        # Run the async automation
        asyncio.run(self.run_automation(api_id, api_hash, phone, options))

    async def run_automation(self, api_id, api_hash, phone, options):
        """Run the Telegram automation"""
        config = TelegramConfig(
            api_id=api_id,
            api_hash=api_hash,
            phone_number=phone
        )

        collector = TelegramCollector(config)
        link_extractor = GitHubLinkExtractor()

        try:
            self.stdout.write(
                self.style.SUCCESS('Starting Telegram data collection...')
            )

            # Start Telegram client
            await collector.start()
            self.stdout.write('✓ Telegram client connected')

            if not options['messages_only']:
                # Fetch and join channels
                self.stdout.write('Fetching Telegram links from GitHub...')
                links = link_extractor.fetch_telegram_links()
                
                if not links:
                    self.stdout.write(
                        self.style.WARNING('No Telegram links found')
                    )
                    return

                self.stdout.write(f'Found {len(links)} Telegram channels')
                
                # Join channels
                self.stdout.write('Joining channels...')
                channels = await collector.join_channels(links)
                
                if not channels:
                    self.stdout.write(
                        self.style.WARNING('No channels joined successfully')
                    )
                    return

                self.stdout.write(
                    self.style.SUCCESS(f'Successfully joined {len(channels)} channels')
                )

                if options['channels_only']:
                    self.stdout.write('Channels-only mode: skipping message collection')
                    return

            else:
                # Use existing channels
                channels = list(TelegramChannel.objects.filter(is_active=True))
                if not channels:
                    self.stdout.write(
                        self.style.WARNING('No active channels found in database')
                    )
                    return
                
                self.stdout.write(f'Using {len(channels)} existing channels')

            # Collect messages
            self.stdout.write('Collecting messages...')
            await collector.collect_messages(channels, limit=options['limit'])

            # Show statistics
            total_messages = TelegramMessage.objects.count()
            total_leaks = DataLeak.objects.count()
            recent_leaks = DataLeak.objects.filter(
                created_at__gte=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
            ).count()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Collection completed!\n'
                    f'Total messages in database: {total_messages}\n'
                    f'Total data leaks found: {total_leaks}\n'
                    f'Leaks found today: {recent_leaks}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Automation failed: {str(e)}')
            )
            logger.error(f'Automation error: {e}', exc_info=True)

        finally:
            await collector.stop()
            self.stdout.write('Telegram client disconnected')

