# 🐳 LeakGuard Docker Setup

This guide will help you run your entire LeakGuard system using Docker Compose with a single command.

## 🚀 Quick Start

### 1. **Setup Environment Variables**
```bash
# Copy the template and edit with your values
cp env_template.txt .env
```

Edit `.env` file and add your Telegram API credentials:
```bash
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE=+1234567890
```

### 2. **Start Everything**
```bash
# Windows
setup_docker.bat

# Linux/Mac
./setup_docker.sh

# Or manually
docker-compose up -d
```

### 3. **Access Your Services**
- **Django App**: http://localhost:8000
- **MinIO Console**: http://localhost:9001 (admin123/admin123456)
- **OpenSearch**: http://localhost:9200
- **OpenSearch Dashboards**: http://localhost:5601

## 📋 Services Included

| Service | Port | Description |
|---------|------|-------------|
| **web** | 8000 | Django application |
| **postgres** | 5432 | PostgreSQL database |
| **redis** | 6379 | Redis cache & message broker |
| **minio** | 9000/9001 | Object storage |
| **opensearch-node1** | 9200 | Search engine (primary) |
| **opensearch-node2** | - | Search engine (secondary) |
| **opensearch-dashboards** | 5601 | Search dashboard |
| **celery** | - | Background task worker |
| **celery-beat** | - | Scheduled task scheduler |

## 🛠️ Common Commands

### **Start/Stop Services**
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Restart specific service
docker-compose restart web
```

### **View Logs**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery
```

### **Django Management Commands**
```bash
# Create superuser
docker-compose exec web python manage.py createsuperuser

# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic

# Run Telegram collection
docker-compose exec web python manage.py telegram_collector

# Access Django shell
docker-compose exec web python manage.py shell
```

### **Database Operations**
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U leakguard -d leakguard

# Backup database
docker-compose exec postgres pg_dump -U leakguard leakguard > backup.sql

# Restore database
docker-compose exec -T postgres psql -U leakguard -d leakguard < backup.sql
```

## 🔧 Configuration

### **Environment Variables**
All configuration is done through environment variables in the `.env` file:

```bash
# Telegram API (Required)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890

# Django
DEBUG=1
SECRET_KEY=your-secret-key

# Database (Auto-configured)
DATABASE_URL=postgresql://leakguard:leakguard123@postgres:5432/leakguard

# Redis (Auto-configured)
REDIS_URL=redis://redis:6379/0

# MinIO (Auto-configured)
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=admin123
MINIO_SECRET_KEY=admin123456

# OpenSearch (Auto-configured)
OPENSEARCH_HOST=opensearch-node1:9200
```

### **Volume Mounts**
- **Code**: `.:/app` - Your code is mounted for development
- **Static Files**: `static_volume:/app/staticfiles`
- **Media Files**: `media_volume:/app/media`
- **Database**: `postgres_data:/var/lib/postgresql/data`
- **Redis**: `redis_data:/data`
- **MinIO**: `minio_data:/data`
- **OpenSearch**: `opensearch-data1:/usr/share/opensearch/data`

## 🐛 Troubleshooting

### **Common Issues**

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   netstat -tulpn | grep :8000
   
   # Stop conflicting services or change ports in docker-compose.yml
   ```

2. **Database Connection Issues**
   ```bash
   # Check if postgres is running
   docker-compose ps postgres
   
   # View postgres logs
   docker-compose logs postgres
   ```

3. **Build Failures**
   ```bash
   # Rebuild without cache
   docker-compose build --no-cache
   
   # Check Dockerfile syntax
   docker build -t test .
   ```

4. **Permission Issues (Linux/Mac)**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

### **Reset Everything**
```bash
# Stop and remove everything
docker-compose down -v

# Remove all images
docker-compose down --rmi all

# Start fresh
docker-compose up -d --build
```

## 📊 Monitoring

### **Service Health**
```bash
# Check all services status
docker-compose ps

# Check resource usage
docker stats

# Check service health
docker-compose exec web python manage.py check
```

### **Logs Monitoring**
```bash
# Follow all logs
docker-compose logs -f

# Follow specific service
docker-compose logs -f web celery

# View last 100 lines
docker-compose logs --tail=100 web
```

## 🔄 Development Workflow

### **Code Changes**
- Code changes are automatically reflected (volume mount)
- Static files: Run `docker-compose exec web python manage.py collectstatic`
- Database changes: Run `docker-compose exec web python manage.py migrate`

### **Adding Dependencies**
1. Add to `requirements.txt`
2. Rebuild: `docker-compose build web`
3. Restart: `docker-compose restart web`

### **Database Migrations**
```bash
# Create migration
docker-compose exec web python manage.py makemigrations

# Apply migration
docker-compose exec web python manage.py migrate
```

## 🚀 Production Deployment

For production, modify the docker-compose.yml:

1. **Change SECRET_KEY** to a secure random string
2. **Set DEBUG=0**
3. **Use environment-specific database credentials**
4. **Add SSL certificates**
5. **Use a reverse proxy (nginx)**
6. **Set up proper logging**

## 📞 Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Verify environment variables in `.env`
3. Ensure all required ports are available
4. Check Docker and Docker Compose versions

## 🎉 Benefits

- **Single Command**: Start everything with `docker-compose up -d`
- **Isolated Environment**: Each service runs in its own container
- **Easy Scaling**: Add more workers or services easily
- **Development Friendly**: Code changes reflected immediately
- **Production Ready**: Same setup works in production
- **Background Tasks**: Celery handles Telegram collection automatically

