"""
Telegram Configuration Template
Copy this file to telegram_config_local.py and fill in your actual values
"""

# Telegram API Configuration
# Get these from https://my.telegram.org/apps
TELEGRAM_API_ID = 'YOUR_API_ID_HERE'  # Integer
TELEGRAM_API_HASH = 'YOUR_API_HASH_HERE'  # String
TELEGRAM_PHONE = '+1234567890'  # Your phone number with country code

# Optional: Session file location
TELEGRAM_SESSION_NAME = 'leakguard_session'

# Collection settings
DEFAULT_MESSAGE_LIMIT = 100
COLLECTION_INTERVAL_HOURS = 6  # How often to run collection

# Data processing settings
MIN_PASSWORD_LENGTH = 3
MAX_MESSAGE_LENGTH = 10000

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'telegram_automation.log'

# Database settings (if using custom database)
# DATABASE_URL = 'postgresql://user:password@localhost/leakguard'
