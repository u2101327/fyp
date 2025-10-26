#!/usr/bin/env python
"""
Test script to verify PostgreSQL connection and setup
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leakguard.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def test_postgres_connection():
    """Test PostgreSQL connection"""
    print("🔍 Testing PostgreSQL connection...")
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ PostgreSQL connected successfully!")
            print(f"📊 Version: {version[0]}")
            return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False

def test_django_check():
    """Run Django system check"""
    print("\n🔍 Running Django system check...")
    
    try:
        execute_from_command_line(['manage.py', 'check', '--database', 'default'])
        print("✅ Django system check passed!")
        return True
    except Exception as e:
        print(f"❌ Django system check failed: {e}")
        return False

def test_migrations():
    """Check migration status"""
    print("\n🔍 Checking migration status...")
    
    try:
        execute_from_command_line(['manage.py', 'showmigrations'])
        print("✅ Migration check completed!")
        return True
    except Exception as e:
        print(f"❌ Migration check failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 LeakGuard PostgreSQL Setup Test")
    print("=" * 50)
    
    # Test connection
    if not test_postgres_connection():
        print("\n❌ Setup failed: Cannot connect to PostgreSQL")
        print("💡 Make sure Docker Desktop is running and PostgreSQL container is started")
        return False
    
    # Test Django check
    if not test_django_check():
        print("\n❌ Setup failed: Django system check failed")
        return False
    
    # Test migrations
    if not test_migrations():
        print("\n❌ Setup failed: Migration check failed")
        return False
    
    print("\n🎉 All tests passed! PostgreSQL is ready for LeakGuard")
    print("\n📋 Next steps:")
    print("   1. Run: python manage.py migrate")
    print("   2. Run: python manage.py createsuperuser")
    print("   3. Run: python manage.py runserver")
    print("   4. Test the credential monitoring form")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
