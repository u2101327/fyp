@echo off
echo 🚀 Starting LeakGuard with Docker Compose
echo ========================================

REM Check if .env file exists
if not exist .env (
    echo ⚠️  .env file not found!
    echo 📝 Please create .env file with your Telegram API credentials
    echo.
    echo Copy env_template.txt to .env and edit it:
    echo copy env_template.txt .env
    echo.
    echo Required values in .env:
    echo - TELEGRAM_API_ID=your_api_id
    echo - TELEGRAM_API_HASH=your_api_hash  
    echo - TELEGRAM_PHONE=+1234567890
    echo.
    pause
    exit /b 1
)

echo 🔨 Starting all services...
docker-compose up -d

echo ⏳ Waiting for services to start...
timeout /t 15 /nobreak > nul

echo 📊 Checking service status...
docker-compose ps

echo.
echo 🎉 LeakGuard is now running!
echo.
echo 🌐 Access your services:
echo - Django App: http://localhost:8000
echo - MinIO Console: http://localhost:9001 (admin123/admin123456)
echo - OpenSearch: http://localhost:9200
echo - OpenSearch Dashboards: http://localhost:5601
echo.
echo 📋 Useful commands:
echo - View logs: docker-compose logs -f
echo - Stop services: docker-compose down
echo - Restart services: docker-compose restart
echo - Create superuser: docker-compose exec web python manage.py createsuperuser
echo.
echo 🤖 To run Telegram collection:
echo docker-compose exec web python manage.py telegram_collector
echo.
pause

