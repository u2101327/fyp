# Telegram Scraper Integration with Django & OpenSearch

This document explains how to use the integrated Telegram scraper that saves data to both Django database and OpenSearch.

## 🚀 Features

- **Django Integration**: Seamlessly integrates with your existing Django project
- **OpenSearch Storage**: Automatically saves scraped data to OpenSearch for advanced search and analytics
- **Data Extraction**: Extracts structured data (emails, phone numbers, API keys, etc.) from messages
- **Leak Detection**: Automatically detects potential data leaks and security issues
- **Media Download**: Downloads media files with organized storage
- **Progress Tracking**: Real-time progress bars and status updates
- **Resume Capability**: Can resume scraping from where it left off

## 📋 Prerequisites

1. **Django Project**: Your Django project should be set up with the required models
2. **OpenSearch**: OpenSearch should be running (see `opensearch/docker-compose.yml`)
3. **Telegram API**: You need Telegram API credentials from https://my.telegram.org

## 🛠️ Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start OpenSearch**:
   ```bash
   cd opensearch
   docker-compose up -d
   ```

3. **Configure Settings**:
   Update your `settings.py` with Telegram API credentials:
   ```python
   TELEGRAM_API_ID = 'your_api_id'
   TELEGRAM_API_HASH = 'your_api_hash'
   TELEGRAM_PHONE = '+your_phone_number'
   ```

## 🎯 Usage

### 1. Interactive Mode (Recommended for first-time setup)

```bash
python manage.py run_telegram_scraper --interactive
```

This will start an interactive menu where you can:
- Add channels to scrape
- List available channels
- Configure scraping options
- Start scraping

### 2. Command Line Usage

**Add a new channel**:
```bash
python manage.py run_telegram_scraper --add-channel "-1001234567890" "Channel Name"
```

**Scrape specific channels**:
```bash
python manage.py run_telegram_scraper --channels "-1001234567890" "-1009876543210"
```

**Scrape all configured channels**:
```bash
python manage.py run_telegram_scraper
```

### 3. Data Extraction

After scraping, extract structured data from messages:

```bash
# Extract data from all messages
python manage.py extract_telegram_data extract

# Extract data from first 1000 messages
python manage.py extract_telegram_data extract --limit 1000

# Detect data leaks
python manage.py extract_telegram_data leaks

# Export extracted data to JSON
python manage.py extract_telegram_data export --output my_data.json

# Show statistics
python manage.py extract_telegram_data stats
```

## 📊 Data Storage

### Django Database
- **TelegramChannel**: Stores channel information
- **TelegramMessage**: Stores individual messages
- **DataLeak**: Stores detected potential data leaks

### OpenSearch Indices
- **telegram-messages**: Raw message data
- **telegram-extracted-data**: Structured data extracted from messages
- **data-leaks**: Detected security issues and leaks

### Media Files
Media files are stored in: `media/telegram/{channel_name}/`

## 🔍 Data Extraction Patterns

The system automatically extracts:

### High-Risk Data
- Passwords
- API Keys
- Secrets/Tokens
- Credit Card Numbers
- Social Security Numbers

### Medium-Risk Data
- Email Addresses
- Phone Numbers
- IP Addresses

### Low-Risk Data
- URLs
- Bitcoin Addresses
- Ethereum Addresses

## 🚨 Leak Detection

The system automatically detects potential data leaks and creates `DataLeak` records with:
- **Severity Levels**: High, Medium, Low
- **Leak Types**: password, api_key, secret, etc.
- **Context**: Surrounding text for analysis
- **Status**: detected, investigated, resolved

## 📈 Monitoring & Analytics

### OpenSearch Dashboards
Access OpenSearch Dashboards at: http://localhost:5601

Create visualizations for:
- Message volume over time
- Data leak trends
- Channel activity
- Extracted data types

### Django Admin
Access Django admin to:
- View scraped messages
- Manage detected leaks
- Configure channels

## 🔧 Configuration

### OpenSearch Settings
Update `opensearch_config.py` for:
- Connection credentials
- Index mappings
- Extraction patterns

### Scraper Settings
Modify `telegram_integrated_scraper.py` for:
- Batch sizes
- Concurrent downloads
- Progress intervals

## 🛡️ Security Considerations

1. **API Credentials**: Store Telegram API credentials securely
2. **OpenSearch Access**: Configure proper authentication for OpenSearch
3. **Data Privacy**: Ensure compliance with data protection regulations
4. **Rate Limiting**: The scraper respects Telegram's rate limits

## 📝 Example Workflow

1. **Setup**:
   ```bash
   # Start OpenSearch
   cd opensearch && docker-compose up -d
   
   # Run migrations
   python manage.py migrate
   ```

2. **Configure Channels**:
   ```bash
   # Interactive mode to add channels
   python manage.py run_telegram_scraper --interactive
   ```

3. **Scrape Data**:
   ```bash
   # Scrape all configured channels
   python manage.py run_telegram_scraper
   ```

4. **Extract & Analyze**:
   ```bash
   # Extract structured data
   python manage.py extract_telegram_data extract
   
   # Detect leaks
   python manage.py extract_telegram_data leaks
   
   # View statistics
   python manage.py extract_telegram_data stats
   ```

5. **Monitor**:
   - Check Django admin for scraped data
   - Use OpenSearch Dashboards for analytics
   - Review detected leaks

## 🐛 Troubleshooting

### Common Issues

1. **OpenSearch Connection Failed**:
   - Ensure OpenSearch is running: `docker ps`
   - Check credentials in `opensearch_config.py`
   - Verify port 9200 is accessible

2. **Telegram Authentication Failed**:
   - Verify API credentials in settings
   - Check phone number format
   - Ensure 2FA is handled correctly

3. **Permission Errors**:
   - Check file permissions for media directory
   - Ensure Django has write access

4. **Memory Issues**:
   - Reduce batch size in scraper settings
   - Process messages in smaller chunks

### Logs
- Scraper logs: Check console output
- Django logs: Check Django logging configuration
- OpenSearch logs: `docker logs opensearch-node1`

## 📚 API Reference

### TelegramIntegratedScraper Class

```python
scraper = IntegratedTelegramScraper()

# Initialize and authenticate
await scraper.initialize_client()

# Add a channel
await scraper.add_channel(channel_id, channel_name)

# Scrape channel
await scraper.scrape_channel(channel_id, channel_name)

# Run scraper for all channels
await scraper.run_scraper()
```

### TelegramDataExtractor Class

```python
extractor = TelegramDataExtractor()

# Process messages for data extraction
extractor.process_telegram_messages(limit=1000)

# Detect data leaks
extractor.process_data_leaks()

# Export data
extractor.export_extracted_data('output.json')

# Get statistics
extractor.get_statistics()
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for educational and research purposes only. Make sure to:
- Respect Telegram's Terms of Service
- Obtain necessary permissions before scraping
- Use responsibly and ethically
- Comply with data protection regulations
- Respect privacy and intellectual property rights
