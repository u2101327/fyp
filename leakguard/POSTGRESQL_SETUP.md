# PostgreSQL Setup for LeakGuard

## Prerequisites
1. **Docker Desktop** must be running
2. **Python dependencies** installed

## Quick Start

### Option 1: Using Docker (Recommended)

1. **Start Docker Desktop** (if not already running)

2. **Start PostgreSQL container:**
   ```bash
   # Windows
   start_postgres.bat
   
   # Linux/Mac
   chmod +x start_postgres.sh
   ./start_postgres.sh
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Start Django server:**
   ```bash
   python manage.py runserver
   ```

### Option 2: Manual Docker Commands

```bash
# Start PostgreSQL container
docker-compose up -d postgres

# Wait for PostgreSQL to be ready (about 10 seconds)
# Then run migrations
python manage.py migrate

# Start Django server
python manage.py runserver
```

### Option 3: Full Docker Stack

```bash
# Start all services (PostgreSQL, Redis, MinIO, OpenSearch)
docker-compose up -d

# Run migrations
python manage.py migrate

# Start Django server
python manage.py runserver
```

## Database Configuration

### Connection Details
- **Host:** localhost (or postgres when using Docker)
- **Port:** 5432
- **Database:** leakguard
- **Username:** leakguard
- **Password:** leakguard123

### Environment Variables
The system automatically detects the environment:
- **Docker:** Uses `DATABASE_URL` from docker-compose.yml
- **Local:** Uses PostgreSQL connection settings in settings.py

## Verification

### Test Database Connection
```bash
python manage.py check --database default
```

### View Database Tables
```bash
python manage.py dbshell
```

### Create Superuser
```bash
python manage.py createsuperuser
```

## Troubleshooting

### Docker Issues
- Ensure Docker Desktop is running
- Check if port 5432 is available: `netstat -an | findstr :5432`

### Connection Issues
- Wait 10-15 seconds after starting PostgreSQL container
- Check container logs: `docker logs leakguard-postgres`

### Migration Issues
- If you have existing SQLite data, you may need to dump and restore:
  ```bash
  python manage.py dumpdata > data.json
  python manage.py migrate
  python manage.py loaddata data.json
  ```

## Benefits of PostgreSQL

✅ **Production-ready** - Used by major companies
✅ **Better performance** - Handles concurrent users
✅ **Advanced features** - JSON fields, full-text search, better indexing
✅ **Scalability** - Can handle large datasets
✅ **Academic credibility** - Shows understanding of enterprise databases

## Data Migration from SQLite

If you have existing data in SQLite:

1. **Export data:**
   ```bash
   python manage.py dumpdata --natural-foreign --natural-primary > data.json
   ```

2. **Switch to PostgreSQL** (already done in settings.py)

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Import data:**
   ```bash
   python manage.py loaddata data.json
   ```

## Next Steps

After PostgreSQL is running:
1. Test the credential monitoring form
2. Verify data is saved to PostgreSQL
3. Check database performance
4. Document the setup in your FYP report
