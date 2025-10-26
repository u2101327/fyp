#!/bin/bash

echo "Starting PostgreSQL container for LeakGuard..."
echo

# Start only PostgreSQL container
docker-compose up -d postgres

echo
echo "Waiting for PostgreSQL to be ready..."
sleep 10

echo
echo "PostgreSQL is running on localhost:5432"
echo "Database: leakguard"
echo "Username: leakguard"
echo "Password: leakguard123"
echo

echo "Testing connection..."
python manage.py check --database default

echo
echo "If connection is successful, you can now run:"
echo "  python manage.py migrate"
echo "  python manage.py runserver"
echo
