#!/bin/bash

# Oneo CRM Setup Script
# This script sets up the development environment for the multi-tenant CRM system

set -e

echo "🚀 Setting up Oneo CRM Development Environment"

# Check if Python 3.11+ is available
python_version=$(python3 --version 2>&1 | cut -d" " -f2 | cut -d"." -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python version check passed"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Dependencies installed successfully"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from template..."
    cp .env.example .env
    echo "📝 Please update .env file with your database credentials"
fi

echo "🎉 Setup completed successfully!"
echo ""
echo "🔍 Checking local services..."

# Check if PostgreSQL is running
if pg_isready -q 2>/dev/null; then
    echo "✅ PostgreSQL is running locally"
    POSTGRES_RUNNING=true
else
    echo "⚠️  PostgreSQL not detected"
    POSTGRES_RUNNING=false
fi

# Check if Redis is running
if redis-cli ping >/dev/null 2>&1; then
    echo "✅ Redis is running locally"
    REDIS_RUNNING=true
else
    echo "⚠️  Redis not detected"
    REDIS_RUNNING=false
fi

echo ""
echo "Next steps:"
echo "1. Update .env file with your database credentials"

if [ "$POSTGRES_RUNNING" = true ] && [ "$REDIS_RUNNING" = true ]; then
    echo "2. ✅ PostgreSQL and Redis are already running!"
    echo "   🎯 READY TO GO! Database services detected and functional."
    echo "3. Run migrations: python manage.py migrate_schemas"
    echo "4. Create a superuser: python manage.py createsuperuser"
    echo "5. Create your first tenant: python manage.py create_tenant --schema_name company --name 'Company Name' --domain-domain 'company.localhost' --noinput"
    echo "6. Start the development server: python manage.py runserver"
    echo ""
    echo "🚀 Alternative: Test full system with: python test_full_integration.py"
else
    echo "2. Start services:"
    if [ "$POSTGRES_RUNNING" = false ]; then
        echo "   📦 PostgreSQL: brew services start postgresql@14"
    fi
    if [ "$REDIS_RUNNING" = false ]; then
        echo "   📦 Redis: brew services start redis"
    fi
    echo "3. Run migrations: python manage.py migrate_schemas"
    echo "4. Create a superuser: python manage.py createsuperuser"
    echo "5. Create your first tenant: python manage.py create_tenant --schema_name company --name 'Company Name' --domain-domain 'company.localhost' --noinput"
    echo "6. Start the development server: python manage.py runserver"
fi