#!/usr/bin/env python3
"""
Data Processing Utility for LeakGuard
Processes leaked credential data from various sources including Telegram
"""

import os
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
import hashlib

# Django setup
import django
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from socradar.models import DataLeak, TelegramMessage, TelegramChannel

logger = logging.getLogger(__name__)

class CredentialProcessor:
    """Process and validate leaked credentials"""
    
    def __init__(self):
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.password_pattern = re.compile(r':([^:\s\n\r]+)')
        self.domain_pattern = re.compile(r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
        self.phone_pattern = re.compile(r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})')
        
        # Common educational domains
        self.edu_domains = {
            'edu', 'edu.au', 'edu.br', 'edu.cn', 'edu.co', 'edu.eg', 'edu.in',
            'edu.mx', 'edu.pe', 'edu.ph', 'edu.pk', 'edu.tr', 'edu.vn',
            'ac.uk', 'ac.za', 'university', 'college', 'school'
        }
        
        # Government domains
        self.gov_domains = {
            'gov', 'gov.au', 'gov.br', 'gov.cn', 'gov.co', 'gov.eg', 'gov.in',
            'gov.mx', 'gov.pe', 'gov.ph', 'gov.pk', 'gov.tr', 'gov.vn',
            'gob', 'mil'
        }
    
    def process_line(self, line: str) -> Optional[Dict[str, str]]:
        """Process a single line of leaked data"""
        if not line or len(line.strip()) < 5:
            return None
        
        line = line.strip()
        
        # Skip lines that don't look like credentials
        if not (':' in line and ('@' in line or line.count(':') >= 1)):
            return None
        
        # Parse email:password format
        if '@' in line and ':' in line:
            return self._parse_email_password(line)
        
        # Parse username:password format
        if ':' in line and not '@' in line:
            return self._parse_username_password(line)
        
        return None
    
    def _parse_email_password(self, line: str) -> Optional[Dict[str, str]]:
        """Parse email:password format"""
        try:
            # Split on first colon
            parts = line.split(':', 1)
            if len(parts) != 2:
                return None
            
            email = parts[0].strip()
            password = parts[1].strip()
            
            # Validate email format
            if not self.email_pattern.match(email):
                return None
            
            # Extract domain
            domain = self._extract_domain(email)
            
            # Determine severity
            severity = self._determine_severity(email, domain, password)
            
            return {
                'email': email,
                'username': email.split('@')[0],
                'password': password,
                'domain': domain,
                'raw_data': line,
                'type': 'email_password',
                'severity': severity,
                'is_educational': self._is_educational_domain(domain),
                'is_government': self._is_government_domain(domain)
            }
            
        except Exception as e:
            logger.error(f"Error parsing email:password line: {e}")
            return None
    
    def _parse_username_password(self, line: str) -> Optional[Dict[str, str]]:
        """Parse username:password format"""
        try:
            parts = line.split(':', 1)
            if len(parts) != 2:
                return None
            
            username = parts[0].strip()
            password = parts[1].strip()
            
            # Basic validation
            if len(username) < 2 or len(password) < 1:
                return None
            
            # Determine severity
            severity = self._determine_severity(username, '', password)
            
            return {
                'username': username,
                'password': password,
                'raw_data': line,
                'type': 'username_password',
                'severity': severity,
                'is_educational': False,
                'is_government': False
            }
            
        except Exception as e:
            logger.error(f"Error parsing username:password line: {e}")
            return None
    
    def _extract_domain(self, email: str) -> str:
        """Extract domain from email"""
        if '@' in email:
            return email.split('@')[1].lower()
        return ''
    
    def _is_educational_domain(self, domain: str) -> bool:
        """Check if domain is educational"""
        domain_lower = domain.lower()
        return any(edu_domain in domain_lower for edu_domain in self.edu_domains)
    
    def _is_government_domain(self, domain: str) -> bool:
        """Check if domain is government"""
        domain_lower = domain.lower()
        return any(gov_domain in domain_lower for gov_domain in self.gov_domains)
    
    def _determine_severity(self, identifier: str, domain: str, password: str) -> str:
        """Determine severity level based on various factors"""
        severity_score = 0
        
        # Educational domain bonus
        if self._is_educational_domain(domain):
            severity_score += 2
        
        # Government domain bonus
        if self._is_government_domain(domain):
            severity_score += 3
        
        # Password strength factors
        if len(password) >= 12:
            severity_score += 1
        elif len(password) >= 8:
            severity_score += 0
        else:
            severity_score -= 1
        
        # Special characters in password
        if any(char in password for char in '!@#$%^&*()_+-=[]{}|;:,.<>?'):
            severity_score += 1
        
        # Numbers in password
        if any(char.isdigit() for char in password):
            severity_score += 1
        
        # Determine final severity
        if severity_score >= 4:
            return 'critical'
        elif severity_score >= 2:
            return 'high'
        elif severity_score >= 0:
            return 'medium'
        else:
            return 'low'
    
    def process_file(self, file_path: str, source: str = 'file') -> List[Dict[str, str]]:
        """Process a file containing leaked credentials"""
        leaks = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        leak_data = self.process_line(line)
                        if leak_data:
                            leak_data['source'] = source
                            leak_data['line_number'] = line_num
                            leaks.append(leak_data)
                    except Exception as e:
                        logger.error(f"Error processing line {line_num}: {e}")
                        continue
            
            logger.info(f"Processed {len(leaks)} valid credentials from {file_path}")
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
        
        return leaks

class DatabaseImporter:
    """Import processed data into Django database"""
    
    def __init__(self):
        self.processor = CredentialProcessor()
    
    def import_leaks(self, leaks: List[Dict[str, str]], source: str = 'import') -> int:
        """Import leaks into database"""
        imported_count = 0
        
        for leak_data in leaks:
            try:
                # Create hash for deduplication
                leak_hash = self._create_hash(leak_data)
                
                # Check if already exists
                if DataLeak.objects.filter(
                    email=leak_data.get('email', ''),
                    password=leak_data.get('password', ''),
                    raw_data=leak_data['raw_data']
                ).exists():
                    continue
                
                # Create new leak record
                DataLeak.objects.create(
                    email=leak_data.get('email', ''),
                    username=leak_data.get('username', ''),
                    password=leak_data.get('password', ''),
                    domain=leak_data.get('domain', ''),
                    source=leak_data.get('source', source),
                    source_url='',
                    leak_date=None,
                    severity=leak_data.get('severity', 'medium'),
                    raw_data=leak_data['raw_data'],
                    is_processed=True
                )
                
                imported_count += 1
                
            except Exception as e:
                logger.error(f"Error importing leak: {e}")
                continue
        
        logger.info(f"Imported {imported_count} new leaks to database")
        return imported_count
    
    def _create_hash(self, leak_data: Dict[str, str]) -> str:
        """Create hash for deduplication"""
        hash_string = f"{leak_data.get('email', '')}:{leak_data.get('password', '')}:{leak_data['raw_data']}"
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def import_file(self, file_path: str, source: str = None) -> int:
        """Import data from file"""
        if source is None:
            source = os.path.basename(file_path)
        
        leaks = self.processor.process_file(file_path, source)
        return self.import_leaks(leaks, source)

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process leaked credential data')
    parser.add_argument('file', help='File to process')
    parser.add_argument('--source', help='Source name for the data')
    parser.add_argument('--dry-run', action='store_true', help='Process but do not import to database')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File {args.file} not found")
        return
    
    processor = CredentialProcessor()
    leaks = processor.process_file(args.file, args.source or 'file')
    
    print(f"Processed {len(leaks)} valid credentials")
    
    if not args.dry_run:
        importer = DatabaseImporter()
        imported = importer.import_leaks(leaks, args.source or 'file')
        print(f"Imported {imported} new records to database")
    else:
        print("Dry run mode - no data imported")

if __name__ == "__main__":
    main()
