from django.core.management.base import BaseCommand
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from scripts.data_processing.telegram_data_extractor import TelegramDataExtractor

class Command(BaseCommand):
    help = 'Extract structured data from Telegram messages'

    def add_arguments(self, parser):
        parser.add_argument(
            'command',
            choices=['extract', 'leaks', 'export', 'stats'],
            help='Command to run',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of messages to process (for extract command)',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output filename (for export command)',
        )

    def handle(self, *args, **options):
        extractor = TelegramDataExtractor()
        
        command = options['command']
        
        if command == 'extract':
            limit = options.get('limit')
            extractor.process_telegram_messages(limit)
            self.stdout.write(
                self.style.SUCCESS('Data extraction completed')
            )
        elif command == 'leaks':
            extractor.process_data_leaks()
            self.stdout.write(
                self.style.SUCCESS('Data leak detection completed')
            )
        elif command == 'export':
            output_file = options.get('output')
            extractor.export_extracted_data(output_file)
            self.stdout.write(
                self.style.SUCCESS('Data export completed')
            )
        elif command == 'stats':
            extractor.get_statistics()
