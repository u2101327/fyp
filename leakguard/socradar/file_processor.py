"""
File Processor for LeakGuard
Handles parsing and analysis of scraped files from Telegram channels
"""

import os
import re
import zipfile
import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import mimetypes

# Django imports
from django.conf import settings
from scripts.storage.minio_client import LeakGuardMinioClient

logger = logging.getLogger(__name__)

class FileProcessor:
    """Processes files downloaded from Telegram channels"""
    
    def __init__(self):
        self.minio_client = LeakGuardMinioClient()
        self.temp_dir = Path(settings.BASE_DIR) / 'temp' / 'file_processing'
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Regex patterns for data extraction
        self.patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'password': re.compile(r'(?i)(?:password|pass|pwd)\s*[:=]\s*([^\s\n\r]+)'),
            'username': re.compile(r'(?i)(?:username|user|login)\s*[:=]\s*([^\s\n\r]+)'),
            'domain': re.compile(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'phone': re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
            'credit_card': re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'),
            'ssn': re.compile(r'\b(?:[0-9]{3}-[0-9]{2}-[0-9]{4}|[0-9]{9})\b'),
        }
        
        # File type handlers
        self.handlers = {
            'text/plain': self._process_text_file,
            'text/csv': self._process_csv_file,
            'application/json': self._process_json_file,
            'application/zip': self._process_zip_file,
            'application/x-zip-compressed': self._process_zip_file,
        }
    
    def process_file(self, s3_uri: str, channel_username: str, message_id: int) -> Dict[str, Any]:
        """
        Process a file from MinIO and extract structured data
        
        Args:
            s3_uri: S3 URI of the file in MinIO
            channel_username: Telegram channel username
            message_id: Telegram message ID
            
        Returns:
            Dict with processing results
        """
        try:
            logger.info(f"Processing file: {s3_uri}")
            
            # Download file from MinIO
            local_path = self._download_from_minio(s3_uri)
            if not local_path:
                return {'success': False, 'error': 'Failed to download file from MinIO'}
            
            # Get file info
            file_info = self._get_file_info(local_path)
            
            # Process file based on type
            content = self._extract_content(local_path, file_info['mime_type'])
            if not content:
                return {'success': False, 'error': 'Failed to extract content from file'}
            
            # Extract structured data
            extracted_data = self._extract_structured_data(content)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(extracted_data)
            
            # Clean up temp file
            self._cleanup_temp_file(local_path)
            
            result = {
                'success': True,
                'file_info': file_info,
                'extracted_data': extracted_data,
                'risk_score': risk_score,
                'processing_timestamp': datetime.now().isoformat(),
                'channel_username': channel_username,
                'message_id': message_id,
                's3_uri': s3_uri
            }
            
            logger.info(f"Successfully processed file: {s3_uri}, extracted {len(extracted_data.get('credentials', []))} credentials")
            return result
            
        except Exception as e:
            logger.error(f"Error processing file {s3_uri}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _download_from_minio(self, s3_uri: str) -> Optional[str]:
        """Download file from MinIO to local temp directory"""
        try:
            # Parse S3 URI
            if not s3_uri.startswith('s3://'):
                return None
            
            # Extract bucket and object key
            parts = s3_uri[5:].split('/', 1)  # Remove 's3://' and split
            if len(parts) != 2:
                return None
            
            bucket_name, object_key = parts
            
            # Generate local filename
            filename = Path(object_key).name
            local_path = self.temp_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            
            # Download file
            self.minio_client.client.fget_object(bucket_name, object_key, str(local_path))
            
            return str(local_path)
            
        except Exception as e:
            logger.error(f"Error downloading file from MinIO: {e}")
            return None
    
    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information"""
        path = Path(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        return {
            'filename': path.name,
            'size': path.stat().st_size,
            'mime_type': mime_type or 'application/octet-stream',
            'extension': path.suffix.lower(),
            'created_at': datetime.fromtimestamp(path.stat().st_ctime).isoformat()
        }
    
    def _extract_content(self, file_path: str, mime_type: str) -> Optional[str]:
        """Extract text content from file based on type"""
        try:
            # Get handler for file type
            handler = self.handlers.get(mime_type, self._process_text_file)
            return handler(file_path)
        except Exception as e:
            logger.error(f"Error extracting content from {file_path}: {e}")
            return None
    
    def _process_text_file(self, file_path: str) -> str:
        """Process plain text files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                        return f.read()
                except:
                    continue
            return ""
    
    def _process_csv_file(self, file_path: str) -> str:
        """Process CSV files"""
        try:
            content = []
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                for row in reader:
                    content.append(' | '.join(row))
            return '\n'.join(content)
        except Exception as e:
            logger.error(f"Error processing CSV file: {e}")
            return self._process_text_file(file_path)  # Fallback to text processing
    
    def _process_json_file(self, file_path: str) -> str:
        """Process JSON files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
        except Exception as e:
            logger.error(f"Error processing JSON file: {e}")
            return self._process_text_file(file_path)  # Fallback to text processing
    
    def _process_zip_file(self, file_path: str) -> str:
        """Process ZIP files"""
        try:
            content = []
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                for file_info in zip_file.filelist:
                    if not file_info.is_dir():
                        try:
                            # Extract text files from ZIP
                            if file_info.filename.lower().endswith(('.txt', '.csv', '.json', '.log')):
                                file_content = zip_file.read(file_info.filename).decode('utf-8', errors='ignore')
                                content.append(f"=== {file_info.filename} ===\n{file_content}\n")
                        except Exception as e:
                            logger.warning(f"Error processing file {file_info.filename} in ZIP: {e}")
                            continue
            return '\n'.join(content)
        except Exception as e:
            logger.error(f"Error processing ZIP file: {e}")
            return ""
    
    def _extract_structured_data(self, content: str) -> Dict[str, Any]:
        """Extract structured data from content"""
        extracted = {
            'emails': [],
            'passwords': [],
            'usernames': [],
            'domains': [],
            'ip_addresses': [],
            'phones': [],
            'credit_cards': [],
            'ssns': [],
            'credentials': [],  # Combined email:password pairs
            'raw_content': content[:10000]  # First 10KB for preview
        }
        
        # Extract different data types
        for data_type, pattern in self.patterns.items():
            matches = pattern.findall(content)
            if data_type == 'password':
                # Clean up password matches
                cleaned_matches = [match.strip('"\'') for match in matches if len(match.strip('"\'"')) > 3]
                extracted[data_type] = list(set(cleaned_matches))
            else:
                extracted[data_type] = list(set(matches))
        
        # Extract credential pairs (email:password format)
        credential_patterns = [
            r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\s*[:|]\s*([^\s\n\r]+)',
            r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\s*[,;]\s*([^\s\n\r]+)',
        ]
        
        for pattern in credential_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for email, password in matches:
                if len(password.strip()) > 3:  # Basic password length check
                    extracted['credentials'].append({
                        'email': email.strip(),
                        'password': password.strip(),
                        'source': 'regex_extraction'
                    })
        
        # Remove duplicates from credentials
        seen = set()
        unique_credentials = []
        for cred in extracted['credentials']:
            key = (cred['email'], cred['password'])
            if key not in seen:
                seen.add(key)
                unique_credentials.append(cred)
        extracted['credentials'] = unique_credentials
        
        return extracted
    
    def _calculate_risk_score(self, extracted_data: Dict[str, Any]) -> int:
        """Calculate risk score based on extracted data"""
        score = 0
        
        # Base scores for different data types
        scores = {
            'emails': 1,
            'passwords': 3,
            'usernames': 1,
            'domains': 1,
            'ip_addresses': 2,
            'phones': 2,
            'credit_cards': 10,
            'ssns': 10,
            'credentials': 5
        }
        
        for data_type, base_score in scores.items():
            count = len(extracted_data.get(data_type, []))
            score += count * base_score
        
        # Cap at 100
        return min(score, 100)
    
    def _cleanup_temp_file(self, file_path: str):
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"Error cleaning up temp file {file_path}: {e}")

def process_file_sync(s3_uri: str, channel_username: str, message_id: int) -> Dict[str, Any]:
    """Synchronous wrapper for file processing"""
    processor = FileProcessor()
    return processor.process_file(s3_uri, channel_username, message_id)
