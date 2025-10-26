"""
LeakGuard MinIO Client for file storage
Handles uploading and managing files in MinIO object storage
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional
from minio import Minio
from minio.error import S3Error
import logging

logger = logging.getLogger(__name__)

class LeakGuardMinioClient:
    """MinIO client for LeakGuard file storage operations"""
    
    def __init__(self):
        """Initialize MinIO client with environment variables"""
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'admin123')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'admin123456')
        self.secure = False  # Set to True for HTTPS
        
        # Initialize MinIO client
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # Default bucket for leaks
        self.bucket_name = 'leaks'
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the leaks bucket exists"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error creating bucket {self.bucket_name}: {e}")
            raise
    
    def _generate_file_hash(self, file_path: str) -> str:
        """Generate SHA256 hash of file content"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _generate_object_path(self, channel_id: str, message_id: int, filename: str, file_hash: str) -> str:
        """Generate MinIO object path for telegram media"""
        date_str = datetime.now().strftime("%Y%m%d")
        # Path format: leaks/{channel_id}/{date}/{hash}/{filename}
        return f"leaks/{channel_id}/{date_str}/{file_hash}/{filename}"
    
    def save_telegram_media(self, local_path: str, channel_id: str, message_id: int, original_filename: str) -> Optional[str]:
        """
        Save telegram media file to MinIO
        
        Args:
            local_path: Local file path to upload
            channel_id: Telegram channel ID (e.g., "-1002515757968")
            message_id: Telegram message ID
            original_filename: Original filename from telegram
            
        Returns:
            MinIO object path (s3://bucket/path) or None if failed
        """
        try:
            if not os.path.exists(local_path):
                logger.error(f"Local file does not exist: {local_path}")
                return None
            
            # Generate file hash for deduplication
            file_hash = self._generate_file_hash(local_path)
            
            # Generate object path
            object_path = self._generate_object_path(channel_id, message_id, original_filename, file_hash)
            
            # Upload file to MinIO
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_path,
                file_path=local_path,
                content_type=self._get_content_type(original_filename)
            )
            
            # Return s3:// URI
            s3_uri = f"s3://{self.bucket_name}/{object_path}"
            logger.info(f"Successfully uploaded {original_filename} to {s3_uri}")
            return s3_uri
            
        except S3Error as e:
            logger.error(f"MinIO S3Error uploading {local_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error uploading {local_path} to MinIO: {e}")
            return None
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension"""
        ext = Path(filename).suffix.lower()
        content_types = {
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.csv': 'text/csv',
            '.sql': 'application/sql',
            '.zip': 'application/zip',
            '.rar': 'application/x-rar-compressed',
            '.7z': 'application/x-7z-compressed',
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def download_file(self, s3_uri: str, local_path: str) -> bool:
        """
        Download file from MinIO to local path
        
        Args:
            s3_uri: S3 URI (s3://bucket/path)
            local_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse s3:// URI
            if not s3_uri.startswith('s3://'):
                logger.error(f"Invalid S3 URI: {s3_uri}")
                return False
            
            # Remove s3:// prefix and split bucket/path
            path_part = s3_uri[5:]  # Remove 's3://'
            if '/' not in path_part:
                logger.error(f"Invalid S3 URI format: {s3_uri}")
                return False
            
            bucket, object_path = path_part.split('/', 1)
            
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            self.client.fget_object(bucket, object_path, local_path)
            logger.info(f"Successfully downloaded {s3_uri} to {local_path}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO S3Error downloading {s3_uri}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error downloading {s3_uri}: {e}")
            return False
    
    def list_files(self, channel_id: str = None, date: str = None) -> list:
        """
        List files in MinIO bucket
        
        Args:
            channel_id: Filter by channel ID
            date: Filter by date (YYYYMMDD format)
            
        Returns:
            List of file objects
        """
        try:
            prefix = "leaks/"
            if channel_id:
                prefix += f"{channel_id}/"
                if date:
                    prefix += f"{date}/"
            
            objects = self.client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
            
        except S3Error as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def delete_file(self, s3_uri: str) -> bool:
        """
        Delete file from MinIO
        
        Args:
            s3_uri: S3 URI to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse s3:// URI
            if not s3_uri.startswith('s3://'):
                logger.error(f"Invalid S3 URI: {s3_uri}")
                return False
            
            path_part = s3_uri[5:]  # Remove 's3://'
            if '/' not in path_part:
                logger.error(f"Invalid S3 URI format: {s3_uri}")
                return False
            
            bucket, object_path = path_part.split('/', 1)
            
            # Delete object
            self.client.remove_object(bucket, object_path)
            logger.info(f"Successfully deleted {s3_uri}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO S3Error deleting {s3_uri}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deleting {s3_uri}: {e}")
            return False
