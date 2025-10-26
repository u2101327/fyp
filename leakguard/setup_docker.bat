@echo off
echo 🐳 Setting up LeakGuard with Docker Compose
echo ==========================================

REM Check if .env file exists
if not exist .env (
    echo 📝 Creating .env file from template...
    copy env_template.txt .env
    echo ⚠️  Please edit .env file and add your Telegram API credentials!
    echo    Get them from: https://my.telegram.org/apps
    echo.
    echo Required values:
    echo - TELEGRAM_API_ID
    echo - TELEGRAM_API_HASH
    echo - TELEGRAM_PHONE
    echo.
    pause
)

echo 🔨 Building Docker images...
docker-compose build

echo 🚀 Starting all services...
docker-compose up -d

echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak > nul

echo 📊 Checking service status...
docker-compose ps

echo.
echo 🎉 LeakGuard is now running!
echo.
echo Access your services:
echo - Django App: http://localhost:8000
echo - MinIO Console: http://localhost:9001 (admin123/admin123456)
echo - OpenSearch: http://localhost:9200
echo - OpenSearch Dashboards: http://localhost:5601
echo.
echo Useful commands:
echo - View logs: docker-compose logs -f
echo - Stop services: docker-compose down
echo - Restart services: docker-compose restart
echo - Create superuser: docker-compose exec web python manage.py createsuperuser
echo.
echo To run Telegram collection:
echo docker-compose exec web python manage.py telegram_collector
pause

