from django.core.management.base import BaseCommand
from django.conf import settings
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from scripts.telegram.telegram_integrated_scraper import IntegratedTelegramScraper

class Command(BaseCommand):
    help = 'Run the integrated Telegram scraper'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='Run in interactive mode',
        )
        parser.add_argument(
            '--channels',
            nargs='+',
            help='Specific channel IDs to scrape',
        )
        parser.add_argument(
            '--add-channel',
            nargs=2,
            metavar=('CHANNEL_ID', 'CHANNEL_NAME'),
            help='Add a new channel to scrape',
        )

    def handle(self, *args, **options):
        async def run_scraper():
            scraper = IntegratedTelegramScraper()
            
            if options['add_channel']:
                channel_id, channel_name = options['add_channel']
                if await scraper.initialize_client():
                    success = await scraper.add_channel(channel_id, channel_name)
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(f'Successfully added channel: {channel_name}')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'Failed to add channel: {channel_name}')
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR('Failed to initialize Telegram client')
                    )
                return
            
            if options['interactive']:
                await scraper.interactive_mode()
            elif options['channels']:
                await scraper.run_scraper(options['channels'])
            else:
                await scraper.run_scraper()

        try:
            asyncio.run(run_scraper())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nScraper interrupted by user'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error running scraper: {e}'))
