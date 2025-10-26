"""
Utility functions for Telegram link validation and processing
"""
import re
import requests
import time
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Tuple, Optional
from django.utils import timezone
from .models import TelegramLink, TelegramMessage, TelegramChannel


def extract_links_from_text(text: str) -> List[str]:
    """
    Extract all URLs from text content
    
    Args:
        text: The text content to extract links from
        
    Returns:
        List of unique URLs found in the text
    """
    # URL regex pattern - matches most common URL formats
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    
    # Find all URLs in the text
    urls = re.findall(url_pattern, text)
    
    # Remove duplicates while preserving order
    unique_urls = []
    seen = set()
    for url in urls:
        if url not in seen:
            unique_urls.append(url)
            seen.add(url)
    
    return unique_urls


def is_telegram_link(url: str) -> bool:
    """
    Check if a URL is a Telegram link
    
    Args:
        url: The URL to check
        
    Returns:
        True if it's a Telegram link, False otherwise
    """
    telegram_domains = [
        't.me', 'telegram.me', 'telegram.org',
        'web.telegram.org', 'desktop.telegram.org'
    ]
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(telegram_domain in domain for telegram_domain in telegram_domains)
    except:
        return False


def calculate_risk_score(url: str, is_telegram: bool = False) -> int:
    """
    Calculate risk score for a URL (0-100)
    
    Args:
        url: The URL to analyze
        is_telegram: Whether this is a Telegram link
        
    Returns:
        Risk score from 0 (safe) to 100 (very risky)
    """
    risk_score = 0
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # High-risk indicators
        if any(suspicious in domain for suspicious in [
            'bit.ly', 'tinyurl', 'short.link', 'goo.gl', 't.co',
            'is.gd', 'v.gd', 'ow.ly', 'buff.ly'
        ]):
            risk_score += 30
        
        # Suspicious patterns
        if re.search(r'[0-9]{4,}', domain):  # Many numbers in domain
            risk_score += 20
            
        if len(domain) > 50:  # Very long domain
            risk_score += 15
            
        if 'phishing' in domain or 'scam' in domain:
            risk_score += 50
            
        # File extensions that might be malicious
        if any(ext in url.lower() for ext in ['.exe', '.bat', '.cmd', '.scr', '.pif']):
            risk_score += 40
            
        # Telegram links are generally safer
        if is_telegram:
            risk_score = max(0, risk_score - 20)
            
    except:
        risk_score += 25  # Unknown URLs get some risk
        
    return min(100, max(0, risk_score))


def validate_url(url: str, timeout: int = 10) -> Tuple[str, Dict]:
    """
    Validate a URL by making a request
    
    Args:
        url: The URL to validate
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (status, response_data)
        Status: 'valid', 'invalid', 'error', 'timeout', 'redirect'
        Response data: dict with status_code, final_url, response_time, etc.
    """
    start_time = time.time()
    response_data = {}
    
    try:
        # Make request with timeout
        response = requests.get(
            url, 
            timeout=timeout,
            allow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        
        response_time = time.time() - start_time
        response_data = {
            'status_code': response.status_code,
            'final_url': response.url,
            'response_time': response_time,
            'content_type': response.headers.get('content-type', ''),
            'content_length': len(response.content) if response.content else 0,
        }
        
        # Determine status based on response
        if response.status_code == 200:
            return 'valid', response_data
        elif 300 <= response.status_code < 400:
            return 'redirect', response_data
        elif 400 <= response.status_code < 500:
            return 'invalid', response_data
        else:
            return 'error', response_data
            
    except requests.exceptions.Timeout:
        return 'timeout', {'error_message': 'Request timeout'}
    except requests.exceptions.ConnectionError:
        return 'error', {'error_message': 'Connection error'}
    except requests.exceptions.RequestException as e:
        return 'error', {'error_message': str(e)}
    except Exception as e:
        return 'error', {'error_message': f'Unexpected error: {str(e)}'}


def process_telegram_message_links(message: TelegramMessage) -> Dict[str, int]:
    """
    Process all links in a Telegram message and create TelegramLink objects
    
    Args:
        message: The TelegramMessage object to process
        
    Returns:
        Dict with counts of processed links by status
    """
    # Extract links from message text
    links = extract_links_from_text(message.text)
    
    if not links:
        return {'total': 0, 'valid': 0, 'invalid': 0, 'error': 0}
    
    # Update message link count
    message.has_links = True
    message.link_count = len(links)
    
    # Process each link
    status_counts = {'total': len(links), 'valid': 0, 'invalid': 0, 'error': 0}
    
    for url in links:
        # Check if link already exists
        existing_link = TelegramLink.objects.filter(
            message=message, 
            url=url
        ).first()
        
        if existing_link:
            continue  # Skip if already processed
            
        # Determine if it's a Telegram link
        is_telegram = is_telegram_link(url)
        
        # Calculate risk score
        risk_score = calculate_risk_score(url, is_telegram)
        
        # Create TelegramLink object
        link_obj = TelegramLink.objects.create(
            url=url,
            message=message,
            channel=message.channel,
            is_telegram_link=is_telegram,
            risk_score=risk_score,
            is_suspicious=risk_score > 50
        )
        
        # Validate the link
        status, response_data = validate_url(url)
        
        # Update link with validation results
        if status == 'valid':
            link_obj.mark_as_valid(
                final_url=response_data.get('final_url'),
                status_code=response_data.get('status_code'),
                response_time=response_data.get('response_time')
            )
            status_counts['valid'] += 1
            
        elif status == 'invalid':
            link_obj.mark_as_invalid(
                error_message=f"HTTP {response_data.get('status_code', 'Unknown')}"
            )
            status_counts['invalid'] += 1
            
        else:  # error, timeout, etc.
            link_obj.mark_as_error(
                error_message=response_data.get('error_message', 'Unknown error')
            )
            status_counts['error'] += 1
    
    # Update message validation status based on link results
    if status_counts['valid'] > 0 and status_counts['invalid'] == 0 and status_counts['error'] == 0:
        message.validation_status = 'valid'
    elif status_counts['invalid'] > 0 or status_counts['error'] > 0:
        message.validation_status = 'invalid'
    else:
        message.validation_status = 'pending'
    
    message.save()
    
    return status_counts


def retry_failed_links(max_retries: int = 3) -> Dict[str, int]:
    """
    Retry validation for failed links that haven't exceeded max retries
    
    Args:
        max_retries: Maximum number of retries allowed
        
    Returns:
        Dict with counts of retried links by status
    """
    # Get links that need retry
    failed_links = TelegramLink.objects.filter(
        validation_status__in=['error', 'timeout'],
        retry_count__lt=max_retries
    )
    
    retry_counts = {'total': 0, 'valid': 0, 'invalid': 0, 'error': 0}
    
    for link in failed_links:
        retry_counts['total'] += 1
        
        # Retry validation
        status, response_data = validate_url(link.url)
        
        if status == 'valid':
            link.mark_as_valid(
                final_url=response_data.get('final_url'),
                status_code=response_data.get('status_code'),
                response_time=response_data.get('response_time')
            )
            retry_counts['valid'] += 1
            
        elif status == 'invalid':
            link.mark_as_invalid(
                error_message=f"HTTP {response_data.get('status_code', 'Unknown')}"
            )
            retry_counts['invalid'] += 1
            
        else:
            link.mark_as_error(
                error_message=response_data.get('error_message', 'Unknown error'),
                increment_retry=True
            )
            retry_counts['error'] += 1
    
    return retry_counts


def get_link_statistics(channel: TelegramChannel = None) -> Dict[str, int]:
    """
    Get statistics about links for a channel or all channels
    
    Args:
        channel: Optional TelegramChannel to filter by
        
    Returns:
        Dict with link statistics
    """
    queryset = TelegramLink.objects.all()
    if channel:
        queryset = queryset.filter(channel=channel)
    
    return {
        'total_links': queryset.count(),
        'valid_links': queryset.filter(validation_status='valid').count(),
        'invalid_links': queryset.filter(validation_status='invalid').count(),
        'error_links': queryset.filter(validation_status='error').count(),
        'pending_links': queryset.filter(validation_status='pending').count(),
        'suspicious_links': queryset.filter(is_suspicious=True).count(),
        'telegram_links': queryset.filter(is_telegram_link=True).count(),
    }

def validate_telegram_channel(username: str) -> dict:
    """
    Validate Telegram channel using Telegram API (more accurate)
    
    Args:
        username: Telegram channel username (without @)
        
    Returns:
        Dict with validation results including status, title, member count, etc.
    """
    import asyncio
    import os
    from django.conf import settings
    
    # Get API credentials from environment or Django settings
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    # Check if credentials are properly set
    if not api_id or not api_hash or api_id == '' or api_hash == '':
        # Fallback to simple validation if no API credentials
        return {
            'status': 'NO_API_CREDENTIALS',
            'is_active': False,
            'title': None,
            'members_count': None,
            'entity_type': None,
            'error': 'Telegram API credentials not configured'
        }
    
    async def check_channel():
        try:
            from telethon import TelegramClient, errors, functions, types
            
            client = TelegramClient("leakguard_session", int(api_id), api_hash)
            
            # Try to start client with timeout
            try:
                await asyncio.wait_for(client.start(), timeout=10.0)
            except asyncio.TimeoutError:
                return {
                    'status': 'AUTH_TIMEOUT',
                    'is_active': False,
                    'title': None,
                    'members_count': None,
                    'entity_type': None,
                    'error': 'Telegram authentication timeout - please authenticate manually first'
                }
            except Exception as e:
                return {
                    'status': 'AUTH_ERROR',
                    'is_active': False,
                    'title': None,
                    'members_count': None,
                    'entity_type': None,
                    'error': f'Authentication error: {str(e)}'
                }
            
            # Try to get channel info
            try:
                result = await client(functions.channels.GetFullChannelRequest(channel=username))
                chat = result.chats[0] if result.chats else None
                full = result.full_chat
                
                return {
                    'status': 'PUBLIC_OK',
                    'is_active': True,
                    'title': getattr(chat, "title", None),
                    'members_count': getattr(full, "participants_count", None),
                    'entity_type': 'channel',
                    'error': None
                }
                
            except errors.UsernameNotOccupiedError:
                return {
                    'status': 'NOT_FOUND',
                    'is_active': False,
                    'title': None,
                    'members_count': None,
                    'entity_type': None,
                    'error': 'Channel not found'
                }
                
            except errors.FloodWaitError as e:
                return {
                    'status': 'FLOODWAIT',
                    'is_active': False,
                    'title': None,
                    'members_count': None,
                    'entity_type': None,
                    'error': f'Rate limited: {str(e)}'
                }
                
            except errors.RPCError as e:
                return {
                    'status': 'RPC_ERROR',
                    'is_active': False,
                    'title': None,
                    'members_count': None,
                    'entity_type': None,
                    'error': f'API error: {str(e)}'
                }
                
        except ImportError:
            return {
                'status': 'TELEGRAM_LIBRARY_MISSING',
                'is_active': False,
                'title': None,
                'members_count': None,
                'entity_type': None,
                'error': 'Telethon library not installed'
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'is_active': False,
                'title': None,
                'members_count': None,
                'entity_type': None,
                'error': f'Connection error: {str(e)}'
            }
        finally:
            try:
                await client.disconnect()
            except:
                pass
    
    # Run the async function
    try:
        return asyncio.run(check_channel())
    except Exception as e:
        return {
            'status': 'ERROR',
            'is_active': False,
            'title': None,
            'members_count': None,
            'entity_type': None,
            'error': f'Async error: {str(e)}'
        }
