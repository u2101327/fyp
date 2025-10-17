# 🔍 OpenSearch Dashboard Guide

## 🚀 **Yes! After scraping channels, you can see all data in OpenSearch Dashboard**

## 📊 **How to Access OpenSearch Dashboard**

1. **Open your browser** and go to: **http://localhost:5601**
2. **Login credentials**:
   - Username: `admin`
   - Password: `admin`
3. **You'll see the OpenSearch Dashboard home page**

## 📁 **What You'll See After Scraping**

### **1. Index Management**
- Go to **"Index Management"** in the left sidebar
- You'll see indices like:
  - `telegram-messages` - Raw message data
  - `telegram-extracted-data` - Processed/structured data
  - `data-leaks` - Detected security issues
  - `telegram-channels` - Channel information

### **2. Discover (Search & Browse Data)**
- Go to **"Discover"** in the left sidebar
- Select an index (e.g., `telegram-messages`)
- You'll see all scraped messages with fields like:
  - `message_text` - The actual message content
  - `sender_username` - Who sent the message
  - `channel_name` - Which channel it came from
  - `message_date` - When it was sent
  - `extracted_data` - Structured data found (emails, phones, etc.)
  - `data_types_found` - What types of data were extracted

### **3. Visualize (Create Charts & Graphs)**
- Go to **"Visualize"** to create charts
- Examples you can create:
  - **Message volume over time**
  - **Most active channels**
  - **Data leak trends**
  - **Extracted data types distribution**

### **4. Dashboard (Combine Visualizations)**
- Go to **"Dashboard"** to create comprehensive views
- Combine multiple visualizations
- Create monitoring dashboards for your Telegram data

## 🔍 **Sample Data Structure**

When you scrape channels, each message will look like this in OpenSearch:

```json
{
  "message_id": 12345,
  "channel_id": "-1001234567890",
  "channel_name": "Security Channel",
  "sender_username": "john_doe",
  "message_text": "Found API key: sk-1234567890abcdef",
  "message_date": "2024-01-15T10:30:00Z",
  "extracted_data": {
    "api_key": ["sk-1234567890abcdef"],
    "email": ["admin@company.com"]
  },
  "data_types_found": ["api_key", "email"],
  "scraped_at": "2024-01-15T10:35:00Z"
}
```

## 🚨 **Data Leak Detection**

The system automatically detects potential leaks and creates entries in the `data-leaks` index:

```json
{
  "leak_type": "api_key",
  "severity": "high",
  "content": "Found API key: sk-1234567890abcdef",
  "detected_at": "2024-01-15T10:35:00Z",
  "status": "detected",
  "channel_name": "Security Channel"
}
```

## 📈 **Creating Useful Visualizations**

### **1. Message Volume Over Time**
- **Visualization Type**: Line Chart
- **X-axis**: `message_date` (Date Histogram)
- **Y-axis**: Count of messages

### **2. Top Channels by Message Count**
- **Visualization Type**: Pie Chart
- **Aggregation**: Terms on `channel_name`

### **3. Data Leak Severity Distribution**
- **Visualization Type**: Bar Chart
- **X-axis**: `severity` (Terms)
- **Y-axis**: Count

### **4. Extracted Data Types**
- **Visualization Type**: Tag Cloud
- **Field**: `data_types_found`

## 🔧 **Search Queries You Can Use**

### **Find messages with API keys:**
```
extracted_data.api_key:*
```

### **Find high-severity leaks:**
```
severity:high
```

### **Find messages from specific channel:**
```
channel_name:"Security Channel"
```

### **Find messages with email addresses:**
```
extracted_data.email:*
```

### **Find recent messages:**
```
message_date:[now-7d TO now]
```

## 🎯 **Step-by-Step Workflow**

1. **Start Scraping**:
   ```bash
   python manage.py run_telegram_scraper --interactive
   ```

2. **Add Channels** (use the interactive menu)

3. **Start Scraping** (select option to scrape)

4. **Extract Data**:
   ```bash
   python manage.py extract_telegram_data extract
   ```

5. **Detect Leaks**:
   ```bash
   python manage.py extract_telegram_data leaks
   ```

6. **View in Dashboard**:
   - Go to http://localhost:5601
   - Login with admin/admin
   - Explore your data!

## 📊 **Dashboard Examples**

### **Security Monitoring Dashboard**
- **Message Volume**: Track activity over time
- **Leak Alerts**: Show detected security issues
- **Channel Activity**: Monitor which channels are most active
- **Data Types**: See what types of sensitive data are being shared

### **Data Analysis Dashboard**
- **Extraction Statistics**: How much data was extracted
- **Channel Comparison**: Compare different channels
- **Trend Analysis**: Identify patterns over time
- **Geographic Distribution**: If location data is available

## 🚀 **Advanced Features**

### **1. Alerts**
- Set up alerts for high-severity leaks
- Get notified when sensitive data is detected
- Monitor unusual activity patterns

### **2. Machine Learning**
- Use OpenSearch ML features for anomaly detection
- Identify unusual patterns in message content
- Predict potential security risks

### **3. API Access**
- Use OpenSearch REST API to integrate with other tools
- Build custom applications on top of your data
- Export data for further analysis

## ✅ **Verification Steps**

1. **Check Connection**: Run `python demo_opensearch.py`
2. **Verify Indices**: Look for `telegram-*` indices in Index Management
3. **Test Search**: Use Discover to search for your data
4. **Create Visualization**: Try creating a simple chart
5. **Build Dashboard**: Combine visualizations into a dashboard

## 🎉 **You're All Set!**

After scraping Telegram channels, you'll have:
- ✅ **Real-time data** in OpenSearch
- ✅ **Searchable messages** with full-text search
- ✅ **Extracted structured data** (emails, phones, etc.)
- ✅ **Automatic leak detection** with severity levels
- ✅ **Rich visualizations** and dashboards
- ✅ **Advanced analytics** capabilities

Your Telegram data will be fully searchable, analyzable, and visualizable in OpenSearch Dashboard! 🚀
