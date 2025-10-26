"""
Django management command to process Telegram messages and extract/validate links
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from socradar.models import TelegramMessage, TelegramChannel
from socradar.utils import process_telegram_message_links, retry_failed_links, get_link_statistics
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process Telegram messages to extract and validate links'

    def add_arguments(self, parser):
        parser.add_argument(
            '--channel',
            type=str,
            help='Process only messages from a specific channel username'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of messages to process (default: 100)'
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Retry validation for previously failed links'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show link statistics after processing'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Telegram link processing...')
        )
        
        # Handle retry failed links
        if options['retry_failed']:
            self.stdout.write('Retrying failed links...')
            retry_counts = retry_failed_links()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Retry completed: {retry_counts['total']} links processed - "
                    f"Valid: {retry_counts['valid']}, "
                    f"Invalid: {retry_counts['invalid']}, "
                    f"Error: {retry_counts['error']}"
                )
            )
            return
        
        # Get messages to process
        queryset = TelegramMessage.objects.filter(has_links=False)
        
        if options['channel']:
            try:
                channel = TelegramChannel.objects.get(username=options['channel'])
                queryset = queryset.filter(channel=channel)
                self.stdout.write(f"Processing messages from channel: @{channel.username}")
            except TelegramChannel.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Channel @{options['channel']} not found")
                )
                return
        
        # Limit the number of messages
        messages = queryset[:options['limit']]
        total_messages = messages.count()
        
        if total_messages == 0:
            self.stdout.write(
                self.style.WARNING('No messages found to process')
            )
            return
        
        self.stdout.write(f"Processing {total_messages} messages...")
        
        # Process messages
        processed_count = 0
        total_links = 0
        valid_links = 0
        invalid_links = 0
        error_links = 0
        
        for message in messages:
            try:
                counts = process_telegram_message_links(message)
                
                total_links += counts['total']
                valid_links += counts['valid']
                invalid_links += counts['invalid']
                error_links += counts['error']
                processed_count += 1
                
                if processed_count % 10 == 0:
                    self.stdout.write(f"Processed {processed_count}/{total_messages} messages...")
                    
            except Exception as e:
                logger.error(f"Error processing message {message.id}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"Error processing message {message.id}: {str(e)}")
                )
                continue
        
        # Show results
        self.stdout.write(
            self.style.SUCCESS(
                f"Processing completed!\n"
                f"Messages processed: {processed_count}/{total_messages}\n"
                f"Total links found: {total_links}\n"
                f"Valid links: {valid_links}\n"
                f"Invalid links: {invalid_links}\n"
                f"Error links: {error_links}"
            )
        )
        
        # Show statistics if requested
        if options['stats']:
            self.show_statistics(options.get('channel'))

    def show_statistics(self, channel_username=None):
        """Show link statistics"""
        if channel_username:
            try:
                channel = TelegramChannel.objects.get(username=channel_username)
                stats = get_link_statistics(channel)
                self.stdout.write(f"\nStatistics for @{channel.username}:")
            except TelegramChannel.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Channel @{channel_username} not found")
                )
                return
        else:
            stats = get_link_statistics()
            self.stdout.write("\nOverall statistics:")
        
        self.stdout.write(
            f"  Total links: {stats['total_links']}\n"
            f"  Valid links: {stats['valid_links']}\n"
            f"  Invalid links: {stats['invalid_links']}\n"
            f"  Error links: {stats['error_links']}\n"
            f"  Pending links: {stats['pending_links']}\n"
            f"  Suspicious links: {stats['suspicious_links']}\n"
            f"  Telegram links: {stats['telegram_links']}"
        )
