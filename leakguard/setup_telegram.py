#!/usr/bin/env python3
"""
Setup script for Telegram automation
Helps configure the Telegram API and run initial setup
"""

import os
import sys
import subprocess
import getpass
from pathlib import Path

def print_banner():
    """Print setup banner"""
    print("=" * 60)
    print("🚀 LeakGuard Telegram Automation Setup")
    print("=" * 60)
    print()

def check_requirements():
    """Check if required packages are installed"""
    print("📦 Checking requirements...")
    
    required_packages = [
        'telethon',
        'django',
        'requests',
        'asyncio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install them with: pip install -r requirements.txt")
        return False
    
    print("✓ All requirements satisfied")
    return True

def get_telegram_config():
    """Get Telegram API configuration from user"""
    print("\n🔧 Telegram API Configuration")
    print("Get your API credentials from: https://my.telegram.org/apps")
    print()
    
    api_id = input("Enter your Telegram API ID: ").strip()
    api_hash = input("Enter your Telegram API Hash: ").strip()
    phone = input("Enter your phone number (with country code, e.g., +1234567890): ").strip()
    
    # Validate inputs
    try:
        int(api_id)
    except ValueError:
        print("❌ API ID must be a number")
        return None
    
    if not api_hash or len(api_hash) < 10:
        print("❌ API Hash seems invalid")
        return None
    
    if not phone.startswith('+'):
        print("❌ Phone number should start with +")
        return None
    
    return {
        'api_id': api_id,
        'api_hash': api_hash,
        'phone': phone
    }

def create_env_file(config):
    """Create .env file with configuration"""
    env_content = f"""# Telegram API Configuration
TELEGRAM_API_ID={config['api_id']}
TELEGRAM_API_HASH={config['api_hash']}
TELEGRAM_PHONE={config['phone']}

# Django Configuration
DEBUG=True
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=sqlite:///db.sqlite3
"""
    
    env_file = Path('.env')
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✓ Created {env_file}")

def run_migrations():
    """Run Django migrations"""
    print("\n🗄️  Running database migrations...")
    
    try:
        result = subprocess.run([
            sys.executable, 'manage.py', 'makemigrations'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Migration creation failed: {result.stderr}")
            return False
        
        result = subprocess.run([
            sys.executable, 'manage.py', 'migrate'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Migration failed: {result.stderr}")
            return False
        
        print("✓ Database migrations completed")
        return True
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

def test_telegram_connection(config):
    """Test Telegram API connection"""
    print("\n🔌 Testing Telegram connection...")
    
    try:
        # Create a simple test script
        test_script = """
import asyncio
import os
from telethon import TelegramClient

async def test_connection():
    client = TelegramClient('test_session', {api_id}, '{api_hash}')
    await client.start(phone='{phone}')
    me = await client.get_me()
    print(f"✓ Connected as: {{me.first_name}} {{me.last_name}} (@{{me.username}})")
    await client.disconnect()

asyncio.run(test_connection())
""".format(**config)
        
        with open('test_telegram.py', 'w') as f:
            f.write(test_script)
        
        result = subprocess.run([
            sys.executable, 'test_telegram.py'
        ], capture_output=True, text=True)
        
        # Clean up test file
        os.remove('test_telegram.py')
        
        if result.returncode == 0:
            print("✓ Telegram connection successful")
            print(result.stdout.strip())
            return True
        else:
            print(f"❌ Telegram connection failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

def create_sample_data():
    """Create sample data from the provided file"""
    print("\n📊 Processing sample data...")
    
    sample_file = "50K edu mix.txt"
    if os.path.exists(sample_file):
        try:
            result = subprocess.run([
                sys.executable, 'data_processor.py', sample_file, '--source', 'sample_data'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✓ Sample data processed successfully")
                print(result.stdout.strip())
                return True
            else:
                print(f"❌ Sample data processing failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Sample data error: {e}")
            return False
    else:
        print(f"⚠️  Sample file {sample_file} not found, skipping...")
        return True

def main():
    """Main setup function"""
    print_banner()
    
    # Check requirements
    if not check_requirements():
        return
    
    # Get configuration
    config = get_telegram_config()
    if not config:
        print("❌ Configuration failed")
        return
    
    # Create environment file
    create_env_file(config)
    
    # Run migrations
    if not run_migrations():
        print("❌ Database setup failed")
        return
    
    # Test Telegram connection
    if not test_telegram_connection(config):
        print("❌ Telegram setup failed")
        return
    
    # Process sample data
    create_sample_data()
    
    print("\n" + "=" * 60)
    print("🎉 Setup completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Run: python manage.py telegram_collector --channels-only")
    print("2. Run: python manage.py telegram_collector --limit 50")
    print("3. Set up automated collection: python telegram_scheduler.py start")
    print()
    print("For manual collection:")
    print("- python manage.py telegram_collector")
    print("- python telegram_automation.py")
    print()

if __name__ == "__main__":
    main()
