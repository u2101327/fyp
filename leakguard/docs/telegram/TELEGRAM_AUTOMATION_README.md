# Telegram Data Collection Automation

This system automatically fetches Telegram links from the [deepdarkCTI repository](https://github.com/fastfire/deepdarkCTI/blob/main/telegram_infostealer.md), joins channels, and collects leaked credential data.

## 🚀 Quick Start

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run setup script
python setup_telegram.py
```

### 2. Get Telegram API Credentials
1. Go to [https://my.telegram.org/apps](https://my.telegram.org/apps)
2. Create a new application
3. Note down your `api_id` and `api_hash`
4. Use your phone number with country code (e.g., +1234567890)

### 3. Run Collection
```bash
# Join channels only
python manage.py telegram_collector --channels-only

# Collect messages (50 per channel)
python manage.py telegram_collector --limit 50

# Full collection
python manage.py telegram_collector
```

## 📁 Files Overview

### Core Files
- `telegram_automation.py` - Main automation script
- `telegram_scheduler.py` - Automated scheduling
- `data_processor.py` - Data parsing and validation
- `setup_telegram.py` - Initial setup helper

### Django Integration
- `socradar/management/commands/telegram_collector.py` - Django management command
- `socradar/models.py` - Updated with Telegram models

### Configuration
- `telegram_config.py` - Configuration template
- `.env` - Environment variables (created by setup)

## 🗄️ Database Models

### New Models Added
- `TelegramChannel` - Stores channel information
- `TelegramMessage` - Stores collected messages
- `DataLeak` - Stores parsed credential leaks

### Data Structure
```python
# TelegramChannel
- name: Channel display name
- username: Channel username (@channel)
- url: Full Telegram URL
- is_active: Whether channel is being monitored
- last_scanned: Last collection timestamp

# TelegramMessage
- channel: Foreign key to TelegramChannel
- message_id: Telegram message ID
- text: Message content
- date: Message timestamp
- sender_id: Sender's Telegram ID

# DataLeak
- email: Extracted email address
- username: Username
- password: Password
- domain: Email domain
- source: Source channel
- severity: low/medium/high/critical
- raw_data: Original message text
```

## 🔧 Usage Examples

### Manual Collection
```bash
# Collect from specific channels only
python manage.py telegram_collector --messages-only --limit 100

# Join new channels without collecting messages
python manage.py telegram_collector --channels-only

# Full collection with custom limit
python manage.py telegram_collector --limit 200
```

### Automated Scheduling
```bash
# Start scheduler (runs continuously)
python telegram_scheduler.py start

# Run single collection
python telegram_scheduler.py run

# Join channels only
python telegram_scheduler.py channels
```

### Data Processing
```bash
# Process sample data file
python data_processor.py "50K edu mix.txt" --source "sample_data"

# Dry run (process but don't import)
python data_processor.py "data.txt" --dry-run
```

## ⚙️ Configuration

### Environment Variables
```bash
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890
```

### Scheduler Settings
The scheduler runs:
- Full collection: every 6 hours
- Channel joining: daily at 2:00 AM
- Quick collection: every hour

## 🔍 Data Processing

### Supported Formats
- `email:password` - Standard credential format
- `username:password` - Username-based credentials

### Severity Classification
- **Critical**: Government domains + strong passwords
- **High**: Educational domains + strong passwords
- **Medium**: Standard credentials
- **Low**: Weak passwords or suspicious data

### Educational Domain Detection
Automatically detects educational institutions:
- `.edu` domains
- `.ac.uk`, `.ac.za` (academic domains)
- Keywords: university, college, school

## 🛡️ Security & Compliance

### Important Notes
- **Legal Compliance**: Ensure you have permission to collect data
- **Rate Limiting**: Built-in delays to respect Telegram's limits
- **Data Privacy**: Process data according to privacy laws
- **Terms of Service**: Respect Telegram's ToS

### Best Practices
- Use dedicated Telegram account for automation
- Monitor collection logs regularly
- Implement data retention policies
- Secure API credentials

## 📊 Monitoring & Logs

### Log Files
- `telegram_automation.log` - Main automation logs
- `telegram_scheduler.log` - Scheduler logs

### Database Queries
```python
# Get recent leaks
from socradar.models import DataLeak
recent_leaks = DataLeak.objects.filter(
    created_at__gte=timezone.now() - timedelta(days=1)
)

# Get high severity leaks
critical_leaks = DataLeak.objects.filter(severity='critical')

# Get educational domain leaks
edu_leaks = DataLeak.objects.filter(domain__icontains='edu')
```

## 🚨 Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Verify API credentials
   - Check phone number format
   - Ensure internet connection

2. **Channel Join Failed**
   - Channel may be private
   - Rate limiting (wait and retry)
   - Channel may not exist

3. **Database Errors**
   - Run migrations: `python manage.py migrate`
   - Check database permissions
   - Verify Django settings

4. **No Data Collected**
   - Check channel activity
   - Verify message parsing logic
   - Review log files

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python manage.py telegram_collector
```

## 🔄 Integration with Dashboard

The collected data automatically appears in your dashboard:
- Statistics cards show leak counts
- Recent alerts display new findings
- Monitoring status shows collection health

## 📈 Performance Tips

- Use `--limit` to control message collection
- Run `--channels-only` periodically to discover new channels
- Monitor disk space for large message collections
- Use database indexing for large datasets

## 🤝 Contributing

To extend the system:
1. Add new data sources in `GitHubLinkExtractor`
2. Enhance parsing logic in `DataParser`
3. Add new severity rules in `CredentialProcessor`
4. Extend models for additional data types

## 📞 Support

For issues or questions:
1. Check log files for error details
2. Verify configuration settings
3. Test with small limits first
4. Review Telegram API documentation
