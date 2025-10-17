# 📁 Project Structure

This document describes the organized structure of the LeakGuard project.

## 🏗️ Directory Structure

```
leakguard/
├── 📁 api/                          # Django API app
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   ├── admin.py
│   ├── management/commands/
│   └── migrations/
│
├── 📁 config/                       # Configuration files
│   └── opensearch_config.py
│
├── 📁 data/                         # Data storage
│   ├── raw/                         # Raw data files
│   │   ├── 50K edu mix.txt
│   │   ├── backup_data.json
│   │   └── tele.txt
│   ├── processed/                   # Processed data
│   └── exports/                     # Exported data
│
├── 📁 docs/                         # Documentation
│   ├── api/
│   │   └── API_DOCUMENTATION.md
│   └── telegram/
│       ├── TELEGRAM_AUTOMATION_README.md
│       ├── TELEGRAM_INTEGRATION_README.md
│       └── QUICK_START_GUIDE.md
│
├── 📁 leakguard/                    # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── 📁 logs/                         # Log files
│   └── telegram_automation.log
│
├── 📁 media/                        # Media files
│   └── telegram/                    # Telegram media files
│
├── 📁 scripts/                      # Python scripts
│   ├── api_client_example.py
│   ├── data_processing/
│   │   ├── data_processor.py
│   │   ├── add_sample_fyptest_data.py
│   │   ├── check_fyptest_data.py
│   │   └── scrape_fyptest.py
│   ├── telegram/
│   │   ├── telegram_integrated_scraper.py
│   │   ├── telegram_automation.py
│   │   ├── telegram_config.py
│   │   ├── telegram_scheduler.py
│   │   └── setup_telegram.py
│   └── testing/
│       └── test_opensearch_connection.py
│
├── 📁 socradar/                     # Main Django app
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── admin.py
│   ├── management/commands/
│   │   ├── extract_telegram_data.py
│   │   ├── import_telegram_json.py
│   │   ├── run_telegram_scraper.py
│   │   └── telegram_collector.py
│   ├── static/
│   ├── templates/
│   └── migrations/
│
├── 📁 static/                       # Static files
├── 📁 staticfiles/                  # Collected static files
├── 📁 templates/                    # Global templates
├── 📁 temp/                         # Temporary files
│   └── fyptest_session.session
│
├── 📁 telegram-scraper/             # Original telegram scraper
│   ├── telegram-scraper.py
│   ├── requirements.txt
│   ├── README.md
│   └── LICENSE
│
├── 📄 manage.py                     # Django management script
├── 📄 requirements.txt              # Python dependencies
├── 📄 docker-compose.yml            # Docker configuration
├── 📄 db.sqlite3                    # SQLite database
└── 📄 PROJECT_STRUCTURE.md          # This file
```

## 📋 File Categories

### 🔧 **Scripts** (`scripts/`)
- **Telegram Scripts**: All Telegram-related automation and scraping
- **Data Processing**: Data manipulation and processing utilities
- **Testing**: Test scripts and connection validators
- **API Examples**: Sample API usage scripts

### 📊 **Data** (`data/`)
- **Raw**: Original, unprocessed data files
- **Processed**: Cleaned and structured data
- **Exports**: Generated reports and exports

### 📚 **Documentation** (`docs/`)
- **API**: API documentation and guides
- **Telegram**: Telegram integration documentation

### ⚙️ **Configuration** (`config/`)
- **OpenSearch**: Search engine configuration
- **Other**: Additional configuration files

### 📝 **Logs** (`logs/`)
- **Application Logs**: System and application logs
- **Error Logs**: Error tracking and debugging

### 🖼️ **Media** (`media/`)
- **Telegram**: Downloaded media files from Telegram
- **Other**: Other media assets

### 🗂️ **Temporary** (`temp/`)
- **Session Files**: Temporary session data
- **Cache**: Temporary cache files

## 🚀 **Usage Examples**

### Running Scripts
```bash
# From project root
python scripts/telegram/telegram_integrated_scraper.py
python scripts/data_processing/data_processor.py
python scripts/testing/test_opensearch_connection.py
```

### Django Management Commands
```bash
# From project root
python manage.py run_telegram_scraper --interactive
python manage.py extract_telegram_data extract
```

### Data Access
```bash
# Raw data
ls data/raw/

# Processed data
ls data/processed/

# Exports
ls data/exports/
```

## 🔄 **Import Path Updates**

After reorganization, update import paths in your scripts:

### Before:
```python
from telegram_integrated_scraper import IntegratedTelegramScraper
from opensearch_config import OPENSEARCH_CONFIG
```

### After:
```python
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from scripts.telegram.telegram_integrated_scraper import IntegratedTelegramScraper
from config.opensearch_config import OPENSEARCH_CONFIG
```

## 📁 **Benefits of This Structure**

1. **Clear Separation**: Each type of file has its dedicated location
2. **Easy Navigation**: Logical grouping makes finding files simple
3. **Scalability**: Easy to add new scripts and data without cluttering
4. **Maintenance**: Easier to maintain and update specific components
5. **Collaboration**: Team members can easily understand the structure
6. **Documentation**: All docs are centralized and organized

## 🔧 **Maintenance**

- **Regular Cleanup**: Remove old files from `temp/` directory
- **Log Rotation**: Archive old logs in `logs/` directory
- **Data Management**: Move processed data to appropriate subdirectories
- **Documentation**: Keep docs updated when adding new features

