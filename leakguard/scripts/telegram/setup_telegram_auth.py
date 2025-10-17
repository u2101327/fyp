"""
Setup Telegram Authentication for LeakGuard
Run this script once to authenticate with Telegram before using the automated scraper
"""

import os
import sys
import asyncio
from pathlib import Path

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')

import django
django.setup()

from django.conf import settings
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import qrcode
from io import StringIO

def display_qr_code_ascii(qr_login):
    """Display QR code in ASCII format"""
    qr = qrcode.QRCode(box_size=1, border=1)
    qr.add_data(qr_login.url)
    qr.make()
    
    f = StringIO()
    qr.print_ascii(out=f)
    f.seek(0)
    print(f.read())

async def setup_telegram_auth():
    """Setup Telegram authentication"""
    print("=== LeakGuard Telegram Authentication Setup ===")
    print("This script will help you authenticate with Telegram for automated scraping.")
    print()
    
    # Get API credentials from settings
    api_id = getattr(settings, 'TELEGRAM_API_ID', None)
    api_hash = getattr(settings, 'TELEGRAM_API_HASH', None)
    
    if not api_id or not api_hash:
        print("Error: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in Django settings")
        return False
    
    print(f"Using API ID: {api_id}")
    print()
    
    # Create session file path
    session_file = Path(settings.BASE_DIR) / 'temp' / 'telegram_session'
    session_file.parent.mkdir(exist_ok=True)
    
    client = TelegramClient(str(session_file), api_id, api_hash)
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            print("You are already authenticated with Telegram!")
            print("The automated scraper should work now.")
            return True
        
        print("Starting authentication process...")
        print()
        print("Choose authentication method:")
        print("[1] QR Code (Recommended - No phone number needed)")
        print("[2] Phone Number (Traditional method)")
        print()
        
        while True:
            choice = input("Enter your choice (1 or 2): ").strip()
            if choice in ['1', '2']:
                break
            print("Please enter 1 or 2")
        
        if choice == '1':
            # QR Code authentication
            print("\nQR Code Authentication")
            print("Please scan the QR code with your Telegram app:")
            print("1. Open Telegram on your phone")
            print("2. Go to Settings > Devices > Scan QR")
            print("3. Scan the code below")
            print()
            
            qr_login = await client.qr_login()
            display_qr_code_ascii(qr_login)
            
            try:
                await qr_login.wait()
                print("\nSuccessfully authenticated via QR code!")
            except SessionPasswordNeededError:
                password = input("\nTwo-factor authentication enabled. Enter your password: ")
                await client.sign_in(password=password)
                print("Successfully authenticated with 2FA!")
            except Exception as e:
                print(f"\nQR code authentication failed: {e}")
                return False
                
        else:
            # Phone authentication
            print("\nPhone Number Authentication")
            phone = input("Enter your phone number (with country code, e.g., +1234567890): ")
            
            try:
                await client.send_code_request(phone)
                code = input("Enter the code you received: ")
                await client.sign_in(phone, code)
                print("Successfully authenticated via phone!")
            except SessionPasswordNeededError:
                password = input("Two-factor authentication enabled. Enter your password: ")
                await client.sign_in(password=password)
                print("Successfully authenticated with 2FA!")
            except Exception as e:
                print(f"\nPhone authentication failed: {e}")
                return False
        
        print()
        print("Authentication completed successfully!")
        print("You can now use the 'Start Scraping Messages' button in the web interface.")
        print("The automated scraper will use this session for future scraping operations.")
        
        return True
        
    except Exception as e:
        print(f"Authentication setup failed: {e}")
        return False
    finally:
        await client.disconnect()

async def main():
    """Main function"""
    success = await setup_telegram_auth()
    if success:
        print("\nSetup completed successfully!")
    else:
        print("\nSetup failed. Please check your API credentials and try again.")
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        sys.exit(1)
