"""
MinIO client for LeakGuard system
Handles file storage and retrieval for investigation purposes
"""

import os
import json
import io
from datetime import datetime
from typing import Optional, Dict, Any, List
from minio import Minio
from minio.error import S3Error
import logging

from config.minio_config import MINIO_CONFIG, BUCKET_CONFIGS, FILE_PATHS

logger = logging.getLogger(__name__)

class LeakGuardMinioClient:
    """MinIO client for LeakGuard file operations"""
    
    def __init__(self):
        self.client = Minio(**MINIO_CONFIG)
        self._ensure_buckets_exist()
    
    def _ensure_buckets_exist(self):
        """Ensure all required buckets exist"""
        for bucket_config in BUCKET_CONFIGS.values():
            bucket_name = bucket_config['name']
            try:
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    logger.info(f"Created bucket: {bucket_name}")
            except S3Error as e:
                logger.error(f"Error creating bucket {bucket_name}: {e}")
    
    def save_telegram_message(self, message_data: Dict[str, Any], channel_id: str, message_id: int) -> str:
        """Save Telegram message data to MinIO"""
        try:
            bucket_name = BUCKET_CONFIGS['telegram_raw']['name']
            file_path = FILE_PATHS['telegram_message'].format(
                channel_id=channel_id,
                message_id=message_id
            )
            
            # Convert message data to JSON
            message_json = json.dumps(message_data, default=str, indent=2)
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name,
                file_path,
                io.BytesIO(message_json.encode('utf-8')),
                len(message_json),
                content_type='application/json'
            )
            
            logger.info(f"Saved message {message_id} to MinIO: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving message to MinIO: {e}")
            raise
    
    def save_telegram_media(self, media_file_path: str, channel_id: str, message_id: int, original_filename: str) -> str:
        """Save Telegram media file to MinIO"""
        try:
            bucket_name = BUCKET_CONFIGS['telegram_media']['name']
            file_path = FILE_PATHS['telegram_media'].format(
                channel_id=channel_id,
                message_id=message_id,
                filename=original_filename
            )
            
            # Upload file to MinIO
            self.client.fput_object(
                bucket_name,
                file_path,
                media_file_path
            )
            
            logger.info(f"Saved media file to MinIO: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving media to MinIO: {e}")
            raise
    
    def get_file_url(self, bucket_name: str, file_path: str, expires_in_seconds: int = 3600) -> str:
        """Generate presigned URL for file access"""
        try:
            url = self.client.presigned_get_object(
                bucket_name,
                file_path,
                expires=expires_in_seconds
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def get_telegram_message_url(self, channel_id: str, message_id: int, expires_in_seconds: int = 3600) -> str:
        """Get presigned URL for Telegram message file"""
        bucket_name = BUCKET_CONFIGS['telegram_raw']['name']
        file_path = FILE_PATHS['telegram_message'].format(
            channel_id=channel_id,
            message_id=message_id
        )
        return self.get_file_url(bucket_name, file_path, expires_in_seconds)
    
    def get_telegram_media_url(self, channel_id: str, message_id: int, filename: str, expires_in_seconds: int = 3600) -> str:
        """Get presigned URL for Telegram media file"""
        bucket_name = BUCKET_CONFIGS['telegram_media']['name']
        file_path = FILE_PATHS['telegram_media'].format(
            channel_id=channel_id,
            message_id=message_id,
            filename=filename
        )
        return self.get_file_url(bucket_name, file_path, expires_in_seconds)
    
    def list_channel_files(self, channel_id: str) -> List[Dict[str, Any]]:
        """List all files for a specific channel"""
        try:
            bucket_name = BUCKET_CONFIGS['telegram_raw']['name']
            prefix = f"telegram/{channel_id}/"
            
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)
            
            files = []
            for obj in objects:
                files.append({
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified,
                    'etag': obj.etag
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing channel files: {e}")
            return []
    
    def delete_file(self, bucket_name: str, file_path: str) -> bool:
        """Delete a file from MinIO"""
        try:
            self.client.remove_object(bucket_name, file_path)
            logger.info(f"Deleted file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def get_file_metadata(self, bucket_name: str, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata from MinIO"""
        try:
            stat = self.client.stat_object(bucket_name, file_path)
            return {
                'size': stat.size,
                'last_modified': stat.last_modified,
                'etag': stat.etag,
                'content_type': stat.content_type
            }
        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
            return None
