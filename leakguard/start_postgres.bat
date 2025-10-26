@echo off
echo Starting PostgreSQL container for LeakGuard...
echo.

REM Start only PostgreSQL container
docker-compose up -d postgres

echo.
echo Waiting for PostgreSQL to be ready...
timeout /t 10 /nobreak > nul

echo.
echo PostgreSQL is running on localhost:5432
echo Database: leakguard
echo Username: leakguard
echo Password: leakguard123
echo.

echo Testing connection...
python manage.py check --database default

echo.
echo If connection is successful, you can now run:
echo   python manage.py migrate
echo   python manage.py runserver
echo.
pause
