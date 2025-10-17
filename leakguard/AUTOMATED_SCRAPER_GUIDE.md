# Automated Telegram Scraper Guide

## Overview

The LeakGuard system now includes an **Automated Telegram Scraper** that works without user input, based on the proven `telegram-scraper.py` that you've already tested successfully.

## Key Features

✅ **No User Input Required** - Fully automated operation  
✅ **MinIO Integration** - Saves raw files to MinIO storage  
✅ **Django Integration** - Saves messages to database  
✅ **Media Download** - Downloads and stores media files  
✅ **Background Processing** - Works with Celery tasks  
✅ **Error Handling** - Graceful fallback mechanisms  

## Setup Instructions

### 1. First-Time Authentication

Before using the automated scraper, you need to authenticate with Telegram **once**:

```bash
# Run the authentication setup script
python scripts/telegram/setup_telegram_auth.py
```

This will:
- Create a Telegram session file
- Allow you to authenticate via QR code or phone number
- Store the session for future automated use

### 2. Using the Automated Scraper

Once authenticated, the automated scraper works in two ways:

#### Option A: Web Interface (Recommended)
1. Go to the Telegram Monitor page
2. Click **"Start Scraping Messages"**
3. The system will automatically:
   - Try to run as a Celery background task
   - Fall back to synchronous scraping if Celery is unavailable
   - Use the new automated scraper

#### Option B: Direct Script Usage
```python
from scripts.telegram.automated_telegram_scraper import run_automated_scraping_sync

# Scrape all active channels
run_automated_scraping_sync()

# Or scrape specific channels
channel_usernames = ['channel1', 'channel2']
run_automated_scraping_sync(channel_usernames)
```

## How It Works

### 1. **Channel Processing**
- Gets active channels from Django database
- Creates/updates channel records automatically
- Processes messages in batches for efficiency

### 2. **Data Storage**
- **Django Database**: Message metadata, channel info
- **MinIO**: Raw message JSON files and media files
- **OpenSearch**: Indexed data for searching (via existing integration)

### 3. **Media Handling**
- Downloads photos, documents, and other media
- Uploads to MinIO with organized folder structure
- Cleans up local temporary files
- Updates database with media file paths

### 4. **Error Recovery**
- Individual channel failures don't stop the entire process
- Graceful handling of network issues
- Automatic retry mechanisms for downloads

## File Structure

```
leakguard/
├── scripts/telegram/
│   ├── automated_telegram_scraper.py    # New automated scraper
│   ├── setup_telegram_auth.py          # Authentication setup
│   └── telegram_integrated_scraper.py   # Original integrated scraper
├── scripts/storage/
│   └── minio_client.py                 # MinIO integration
└── scripts/tasks/
    └── celery_tasks.py                 # Background task integration
```

## Configuration

The automated scraper uses these Django settings:

```python
# In settings.py
TELEGRAM_API_ID = 28362044
TELEGRAM_API_HASH = 'your_api_hash'
```

## Session Management

- Session files are stored in `leakguard/temp/telegram_session.session`
- Once authenticated, the session persists across restarts
- No need to re-authenticate unless session expires

## Troubleshooting

### "Telegram client not authorized"
- Run the authentication setup script first
- Make sure you completed the QR code or phone authentication

### "No channels to scrape"
- Add channels to the database via the web interface
- Make sure channels are marked as active

### "Celery not available"
- The system automatically falls back to synchronous scraping
- This is normal and expected behavior

### Connection Issues
- Check your internet connection
- Verify Telegram API credentials in settings
- Ensure MinIO and other services are running

## Performance

- **Batch Processing**: Processes messages in batches of 100
- **Concurrent Downloads**: Up to 5 concurrent media downloads
- **Progress Tracking**: Shows progress for large operations
- **Memory Efficient**: Processes data in chunks to avoid memory issues

## Integration with Existing Workflow

The automated scraper seamlessly integrates with your existing LeakGuard workflow:

1. **Scraping** → Automated scraper collects data
2. **Storage** → MinIO stores raw files
3. **Indexing** → OpenSearch indexes the data
4. **Matching** → Credential matcher finds leaks
5. **Alerting** → Users get notified of matches
6. **Investigation** → Users can access raw files via MinIO

## Next Steps

1. **Run Authentication**: `python scripts/telegram/setup_telegram_auth.py`
2. **Test Scraping**: Use the web interface to start scraping
3. **Monitor Results**: Check the database and MinIO for scraped data
4. **Set Up Scheduling**: Configure Celery Beat for regular scraping

The automated scraper is now ready to replace the manual scraping process and provide continuous, reliable data collection for your LeakGuard system!

