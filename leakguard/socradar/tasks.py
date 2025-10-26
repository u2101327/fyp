"""
Celery tasks for LeakGuard Telegram scraping
"""

import os
import sys
import asyncio
import logging
from celery import shared_task
from django.utils import timezone
from django.conf import settings

# Setup logging
logger = logging.getLogger(__name__)

@shared_task(bind=True)
def scrape_channel_task(self, channel_id, channel_username, last_scraped_msg_id=0, requested_by=None):
    """
    Celery task to scrape a Telegram channel with progress tracking
    
    Args:
        channel_id: Database ID of the channel
        channel_username: Telegram channel username
        last_scraped_msg_id: Last scraped message ID for incremental scraping
        requested_by: User ID who requested the scraping
    """
    try:
        # Import here to avoid circular imports
        from .models import TelegramChannel, TelegramMessage
        from .scraper import TelegramScraper
        
        # Get channel from database
        try:
            channel = TelegramChannel.objects.get(id=channel_id)
        except TelegramChannel.DoesNotExist:
            return {'status': 'FAILED', 'error': 'Channel not found'}
        
        # Update channel status
        channel.scraping_status = 'RUNNING'
        channel.scraping_error = None
        channel.save()
        
        # Progress tracking variables
        total_messages = 0
        processed_messages = 0
        processed_files = 0
        start_time = timezone.now()
        
        # Update task status - Connecting
        if self.request.id:
            self.update_state(
                state='PROGRESS', 
                meta={
                    'status': 'Connecting to Telegram...',
                    'progress': 5,
                    'messages_count': 0,
                    'files_count': 0,
                    'estimated_time': 'Calculating...'
                }
            )
        
        # Initialize scraper
        scraper = TelegramScraper()
        
        # Update task status - Getting channel info
        if self.request.id:
            self.update_state(
                state='PROGRESS', 
                meta={
                    'status': 'Getting channel information...',
                    'progress': 10,
                    'messages_count': 0,
                    'files_count': 0,
                    'estimated_time': 'Calculating...'
                }
            )
        
        # Run scraping with progress callback
        def progress_callback(current, total, files, status):
            if total > 0:
                progress = min(90, 10 + (current / total) * 80)  # 10-90% for message processing
                elapsed = (timezone.now() - start_time).total_seconds()
                if current > 0:
                    estimated_total = (elapsed / current) * total
                    remaining = max(0, estimated_total - elapsed)
                    estimated_time = f"{int(remaining)}s remaining"
                else:
                    estimated_time = "Calculating..."
            else:
                progress = 10
                estimated_time = "Starting..."
            
            if self.request.id:
                self.update_state(
                    state='PROGRESS', 
                    meta={
                        'status': status,
                        'progress': int(progress),
                        'messages_count': current,
                        'files_count': files,
                        'estimated_time': estimated_time
                    }
                )
        
        # Use asyncio.run in a separate thread to avoid async context issues
        import threading
        result_container = {}
        
        def run_scraper():
            result_container['result'] = asyncio.run(scraper.scrape_channel_async(
                channel_username=channel_username,
                offset_id=last_scraped_msg_id,
                channel_id=channel_id,
                progress_callback=progress_callback
            ))
        
        scraper_thread = threading.Thread(target=run_scraper)
        scraper_thread.start()
        scraper_thread.join()
        
        result = result_container['result']
        
        # Final progress update
        if self.request.id:
            self.update_state(
                state='PROGRESS', 
                meta={
                    'status': 'Finalizing...',
                    'progress': 95,
                    'messages_count': result.get('messages_count', 0),
                    'files_count': result.get('files_count', 0),
                    'estimated_time': 'Almost done...'
                }
            )
        
        if result['success']:
            # Update channel with results
            channel.scraping_status = 'COMPLETED'
            channel.last_scraped_msg_id = result.get('last_message_id', last_scraped_msg_id)
            channel.last_scanned = timezone.now()
            channel.scraping_error = None
            channel.save()
            
            # Final success update
            if self.request.id:
                self.update_state(
                    state='SUCCESS', 
                    meta={
                        'status': 'Completed successfully!',
                        'progress': 100,
                        'messages_count': result.get('messages_count', 0),
                        'files_count': result.get('files_count', 0),
                        'estimated_time': 'Done!'
                    }
                )
            
            return {
                'status': 'SUCCESS',
                'messages_count': result.get('messages_count', 0),
                'files_count': result.get('files_count', 0),
                'last_message_id': result.get('last_message_id', last_scraped_msg_id)
            }
        else:
            # Update channel with error
            channel.scraping_status = 'FAILED'
            channel.scraping_error = result.get('error', 'Unknown error')
            channel.save()
            
            # Don't use FAILURE state, return error in result
            pass
            
            return {
                'status': 'FAILED',
                'error': result.get('error', 'Unknown error')
            }
            
    except Exception as e:
        logger.error(f"Error in scrape_channel_task: {str(e)}")
        
        # Update channel with error
        try:
            channel = TelegramChannel.objects.get(id=channel_id)
            channel.scraping_status = 'FAILED'
            channel.scraping_error = str(e)
            channel.save()
        except:
            pass
        
        # Don't use FAILURE state with custom meta, use SUCCESS with error info
        return {
            'status': 'FAILED',
            'error': str(e),
            'progress': 0,
            'messages_count': 0,
            'files_count': 0
        }

@shared_task
def cleanup_old_scraping_tasks():
    """Clean up old completed/failed scraping tasks"""
    try:
        from .models import TelegramChannel
        
        # Reset old completed/failed tasks
        old_tasks = TelegramChannel.objects.filter(
            scraping_status__in=['COMPLETED', 'FAILED'],
            updated_at__lt=timezone.now() - timezone.timedelta(hours=24)
        )
        
        count = old_tasks.count()
        old_tasks.update(
            scraping_status='IDLE',
            scraping_task_id=None,
            scraping_error=None
        )
        
        logger.info(f"Cleaned up {count} old scraping tasks")
        return f"Cleaned up {count} old scraping tasks"
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_scraping_tasks: {str(e)}")
        return f"Error: {str(e)}"

@shared_task(bind=True)
def process_file_task(self, message_id: int, s3_uri: str, channel_username: str):
    """
    Celery task to process a file and extract structured data
    
    Args:
        message_id: Telegram message ID
        s3_uri: S3 URI of the file in MinIO
        channel_username: Telegram channel username
    """
    try:
        # Import here to avoid circular imports
        from .models import TelegramMessage, ProcessedFile, ExtractedCredential
        from .file_processor import FileProcessor
        from django.utils import timezone
        
        # Get message from database
        try:
            message = TelegramMessage.objects.get(id=message_id)
        except TelegramMessage.DoesNotExist:
            return {'status': 'FAILED', 'error': 'Message not found'}
        
        # Create or get ProcessedFile record
        processed_file, created = ProcessedFile.objects.get_or_create(
            message=message,
            s3_uri=s3_uri,
            defaults={
                'filename': s3_uri.split('/')[-1],
                'file_size': 0,
                'mime_type': 'unknown',
                'file_extension': '',
                'processing_status': 'PENDING'
            }
        )
        
        if not created:
            # File already processed
            return {'status': 'SUCCESS', 'message': 'File already processed', 'processed_file_id': processed_file.id}
        
        # Update status to processing
        processed_file.processing_status = 'PROCESSING'
        processed_file.save()
        
        # Update task status
        if self.request.id:
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': 'Processing file...',
                    'progress': 10,
                    'filename': processed_file.filename
                }
            )
        
        # Process the file
        processor = FileProcessor()
        result = processor.process_file(s3_uri, channel_username, message_id)
        
        if not result['success']:
            # Update status to failed
            processed_file.processing_status = 'FAILED'
            processed_file.processing_error = result['error']
            processed_file.save()
            return {'status': 'FAILED', 'error': result['error']}
        
        # Update task status
        if self.request.id:
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': 'Saving extracted data...',
                    'progress': 80,
                    'filename': processed_file.filename
                }
            )
        
        # Update ProcessedFile with results
        file_info = result['file_info']
        extracted_data = result['extracted_data']
        
        processed_file.filename = file_info['filename']
        processed_file.file_size = file_info['size']
        processed_file.mime_type = file_info['mime_type']
        processed_file.file_extension = file_info['extension']
        processed_file.processing_status = 'COMPLETED'
        processed_file.processed_at = timezone.now()
        
        # Update counts
        processed_file.emails_count = len(extracted_data.get('emails', []))
        processed_file.passwords_count = len(extracted_data.get('passwords', []))
        processed_file.usernames_count = len(extracted_data.get('usernames', []))
        processed_file.domains_count = len(extracted_data.get('domains', []))
        processed_file.ip_addresses_count = len(extracted_data.get('ip_addresses', []))
        processed_file.phones_count = len(extracted_data.get('phones', []))
        processed_file.credit_cards_count = len(extracted_data.get('credit_cards', []))
        processed_file.ssns_count = len(extracted_data.get('ssns', []))
        processed_file.credentials_count = len(extracted_data.get('credentials', []))
        
        # Update risk assessment
        processed_file.risk_score = result['risk_score']
        processed_file.is_sensitive = result['risk_score'] > 50
        
        processed_file.save()
        
        # Create ExtractedCredential records
        credentials_created = 0
        credential_ids = []
        for cred_data in extracted_data.get('credentials', []):
            try:
                credential = ExtractedCredential.objects.create(
                    processed_file=processed_file,
                    message=message,
                    email=cred_data.get('email'),
                    password=cred_data.get('password'),
                    extraction_method='regex',
                    confidence_score=0.8,  # Default confidence
                    risk_level='MEDIUM'  # Will be calculated by the model
                )
                # Calculate and update risk level
                credential.risk_level = credential.calculate_risk_level()
                credential.save()
                credentials_created += 1
                credential_ids.append(credential.id)
            except Exception as e:
                logger.warning(f"Error creating credential record: {e}")
                continue
        
        # Index credentials to OpenSearch
        if credential_ids:
            try:
                from .opensearch_client import get_opensearch_client
                opensearch_client = get_opensearch_client()
                
                if opensearch_client.is_available():
                    # Bulk index all credentials
                    index_result = opensearch_client.bulk_index_credentials(credential_ids)
                    if index_result.get('success'):
                        logger.info(f"Indexed {index_result.get('indexed', 0)} credentials to OpenSearch")
                    else:
                        logger.warning(f"Failed to index credentials: {index_result.get('error')}")
                else:
                    logger.warning("OpenSearch not available for indexing")
            except Exception as e:
                logger.warning(f"Error indexing credentials to OpenSearch: {e}")
        
        # Index processed file to OpenSearch
        try:
            from .opensearch_client import get_opensearch_client
            opensearch_client = get_opensearch_client()
            
            if opensearch_client.is_available():
                file_indexed = opensearch_client.index_processed_file(processed_file.id)
                if file_indexed:
                    logger.info(f"Indexed processed file {processed_file.id} to OpenSearch")
                else:
                    logger.warning(f"Failed to index processed file {processed_file.id}")
            else:
                logger.warning("OpenSearch not available for file indexing")
        except Exception as e:
            logger.warning(f"Error indexing processed file to OpenSearch: {e}")
        
        # Update task status
        if self.request.id:
            self.update_state(
                state='SUCCESS',
                meta={
                    'status': 'File processing completed!',
                    'progress': 100,
                    'filename': processed_file.filename,
                    'credentials_created': credentials_created
                }
            )
        
        logger.info(f"Successfully processed file {s3_uri}: {credentials_created} credentials extracted")
        
        return {
            'status': 'SUCCESS',
            'processed_file_id': processed_file.id,
            'credentials_created': credentials_created,
            'risk_score': result['risk_score'],
            'extracted_counts': {
                'emails': processed_file.emails_count,
                'passwords': processed_file.passwords_count,
                'credentials': processed_file.credentials_count
            }
        }
        
    except Exception as e:
        logger.error(f"Error in process_file_task: {str(e)}")
        
        # Update ProcessedFile with error
        try:
            processed_file = ProcessedFile.objects.get(message_id=message_id, s3_uri=s3_uri)
            processed_file.processing_status = 'FAILED'
            processed_file.processing_error = str(e)
            processed_file.save()
        except:
            pass
        
        return {'status': 'FAILED', 'error': str(e)}


@shared_task
def process_scraped_files():
    """Process newly scraped files for parsing and indexing"""
    try:
        from .models import TelegramMessage
        
        # Get messages with media that haven't been processed
        unprocessed_messages = TelegramMessage.objects.filter(
            has_media=True,
            processed=False
        )[:100]  # Process in batches
        
        processed_count = 0
        for message in unprocessed_messages:
            try:
                # Here you would add file processing logic
                # For now, just mark as processed
                message.processed = True
                message.save()
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing message {message.id}: {str(e)}")
        
        logger.info(f"Processed {processed_count} scraped files")
        return f"Processed {processed_count} scraped files"
        
    except Exception as e:
        logger.error(f"Error in process_scraped_files: {str(e)}")
        return f"Error: {str(e)}"
