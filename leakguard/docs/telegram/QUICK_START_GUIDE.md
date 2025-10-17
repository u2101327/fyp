# 🚀 Quick Start Guide - Telegram Scraper Integration

## 📋 What's Been Created

I've successfully modified the Telegram scraper to integrate with your Django system and OpenSearch database. Here's what you now have:

### 🔧 New Files Created:
1. **`telegram_integrated_scraper.py`** - Main integrated scraper
2. **`telegram_data_extractor.py`** - Data extraction and processing
3. **`opensearch_config.py`** - OpenSearch configuration
4. **`test_opensearch_connection.py`** - Connection testing script
5. **Management Commands**:
   - `socradar/management/commands/run_telegram_scraper.py`
   - `socradar/management/commands/extract_telegram_data.py`
6. **Documentation**:
   - `TELEGRAM_INTEGRATION_README.md` - Comprehensive guide
   - `QUICK_START_GUIDE.md` - This file

### 🔄 Modified Files:
- **`requirements.txt`** - Added OpenSearch and scraper dependencies

## 🎯 Key Features Added

### ✅ Django Integration
- Uses your existing Django models (`TelegramChannel`, `TelegramMessage`, `DataLeak`)
- Saves all scraped data to Django database
- Integrates with your authentication system

### ✅ OpenSearch Integration
- Automatically saves data to OpenSearch indices
- Creates separate indices for messages, extracted data, and leaks
- Enables advanced search and analytics

### ✅ Data Extraction
- Extracts emails, phone numbers, API keys, passwords, etc.
- Detects potential data leaks automatically
- Categorizes data by risk level (high/medium/low)

### ✅ Media Handling
- Downloads media files to organized directory structure
- Stores file paths in database and OpenSearch
- Prevents file overwrites with unique naming

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies
```bash
cd leakguard
pip install -r requirements.txt
```

### 2. Start OpenSearch
```bash
cd opensearch
docker-compose up -d
```

### 3. Test Integration
```bash
cd ..
python test_opensearch_connection.py
```

### 4. Run Scraper (Interactive Mode)
```bash
python manage.py run_telegram_scraper --interactive
```

### 5. Extract Data
```bash
python manage.py extract_telegram_data extract
python manage.py extract_telegram_data leaks
```

## 📊 Data Flow

```
Telegram Channels → Scraper → Django DB + OpenSearch
                                    ↓
                            Data Extractor → Structured Data
                                    ↓
                            Leak Detector → Security Alerts
```

## 🔍 What Gets Extracted

### High-Risk Data (Auto-detected as leaks):
- Passwords
- API Keys
- Secrets/Tokens
- Credit Card Numbers
- Social Security Numbers

### Medium-Risk Data:
- Email Addresses
- Phone Numbers
- IP Addresses

### Low-Risk Data:
- URLs
- Bitcoin/Ethereum Addresses

## 📈 Monitoring & Analytics

### OpenSearch Dashboards
- Access: http://localhost:5601
- Create visualizations for message trends, leak detection, etc.

### Django Admin
- View scraped messages
- Manage detected leaks
- Configure channels

## 🛠️ Common Commands

```bash
# Add a channel
python manage.py run_telegram_scraper --add-channel "-1001234567890" "Channel Name"

# Scrape all channels
python manage.py run_telegram_scraper

# Extract data from messages
python manage.py extract_telegram_data extract

# Detect leaks
python manage.py extract_telegram_data leaks

# Export data
python manage.py extract_telegram_data export --output my_data.json

# View statistics
python manage.py extract_telegram_data stats
```

## 🔧 Configuration

### OpenSearch Credentials
Update `opensearch_config.py`:
```python
OPENSEARCH_CONFIG = {
    'http_auth': ('your_username', 'your_password'),
    # ... other settings
}
```

### Telegram API
Your settings are already configured in `settings.py`:
```python
TELEGRAM_API_ID = 28362044
TELEGRAM_API_HASH = 'b0eacf843a2e57669a5fe96f8d22c9ba'
TELEGRAM_PHONE = '+60175861045'
```

## 📁 File Structure

```
leakguard/
├── telegram_integrated_scraper.py    # Main scraper
├── telegram_data_extractor.py        # Data extraction
├── opensearch_config.py              # OpenSearch config
├── test_opensearch_connection.py     # Test script
├── socradar/management/commands/
│   ├── run_telegram_scraper.py       # Django command
│   └── extract_telegram_data.py      # Django command
├── media/telegram/                   # Media files storage
└── telegram_scraper_state.json       # Scraper state
```

## 🚨 Security Features

1. **Automatic Leak Detection**: Scans messages for sensitive data
2. **Risk Classification**: Categorizes findings by severity
3. **Context Preservation**: Saves surrounding text for analysis
4. **Audit Trail**: Tracks when data was scraped and processed

## 📊 Example Output

### Scraped Data in OpenSearch:
```json
{
  "message_id": 12345,
  "channel_name": "Security Channel",
  "message_text": "API key: sk-1234567890abcdef",
  "extracted_data": {
    "api_key": ["sk-1234567890abcdef"]
  },
  "data_types_found": ["api_key"]
}
```

### Detected Leak:
```json
{
  "leak_type": "api_key",
  "severity": "high",
  "content": "Found API key: sk-1234567890abcdef",
  "status": "detected"
}
```

## 🆘 Troubleshooting

### OpenSearch Connection Issues:
```bash
# Check if OpenSearch is running
docker ps | grep opensearch

# Test connection
python test_opensearch_connection.py
```

### Telegram Authentication Issues:
- Verify API credentials in settings.py
- Check phone number format
- Ensure 2FA is handled correctly

### Permission Issues:
```bash
# Fix media directory permissions
chmod -R 755 media/telegram/
```

## 🎉 You're Ready!

Your Telegram scraper is now fully integrated with:
- ✅ Django database storage
- ✅ OpenSearch for advanced analytics
- ✅ Automatic data extraction
- ✅ Leak detection and security monitoring
- ✅ Media file management
- ✅ Progress tracking and resume capability

Start scraping and analyzing your Telegram data! 🚀
