#!/bin/bash

# Oneo CRM Backend Setup Script
# This script sets up the backend development environment for the multi-tenant CRM system

set -e

echo "🚀 Setting up Oneo CRM Backend Development Environment"

# Navigate to backend directory
cd "$(dirname "$0")/../backend"

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

# Set Django settings for management commands
export DJANGO_SETTINGS_MODULE=oneo_crm.settings

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

# Check system readiness
echo ""
echo "🔍 Checking system readiness..."

# Check if migrations are applied
if python manage.py showmigrations --verbosity=0 | grep -q "\[ \]"; then
    MIGRATIONS_PENDING=true
    echo "⚠️  Database migrations pending"
else
    MIGRATIONS_PENDING=false
    echo "✅ Database migrations applied"
fi

# Check if superuser exists
SUPERUSER_COUNT=$(python -c "from django.contrib.auth import get_user_model; import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings'); django.setup(); User = get_user_model(); print(User.objects.filter(is_superuser=True).count())" 2>/dev/null || echo "0")
if [ "$SUPERUSER_COUNT" -gt 0 ]; then
    SUPERUSER_EXISTS=true
    echo "✅ Superuser exists ($SUPERUSER_COUNT found)"
else
    SUPERUSER_EXISTS=false
    echo "⚠️  No superuser found"
fi

echo ""
echo "📋 Next steps based on current system state:"

if [ "$POSTGRES_RUNNING" = false ] || [ "$REDIS_RUNNING" = false ]; then
    echo "1. 🔥 PRIORITY: Start required services:"
    if [ "$POSTGRES_RUNNING" = false ]; then
        echo "   📦 PostgreSQL: brew services start postgresql@14"
    fi
    if [ "$REDIS_RUNNING" = false ]; then
        echo "   📦 Redis: brew services start redis"
    fi
    STEP=2
else
    STEP=1
fi

if [ "$MIGRATIONS_PENDING" = true ]; then
    echo "$STEP. Run database migrations: python manage.py migrate_schemas"
    STEP=$((STEP+1))
fi

if [ "$SUPERUSER_EXISTS" = false ]; then
    echo "$STEP. Create a superuser: python manage.py createsuperuser"
    STEP=$((STEP+1))
fi

if [ "$POSTGRES_RUNNING" = true ] && [ "$REDIS_RUNNING" = true ] && [ "$MIGRATIONS_PENDING" = false ]; then
    echo "$STEP. 🚀 SYSTEM READY! Start the development server: python manage.py runserver"
    echo ""
    echo "📍 Access Points:"
    echo "   🔧 Admin Interface: http://localhost:8000/admin/"
    echo "   📊 API Docs: http://localhost:8000/api/v1/docs/"
    echo "   🌐 Demo Tenant: http://demo.localhost:8000/"
    echo ""
    echo "🧪 System Tests:"
    echo "   ✅ Full Integration: python test_full_integration.py"
    echo "   📈 Performance: python -m pytest tests/test_performance.py -v"
    echo ""
    echo "🛠️  Management Commands:"
    echo "   👤 Create tenant: python manage.py create_tenant 'Company Name' 'company.localhost'"
    echo "   🤖 Configure AI: python manage.py configure_tenant_ai 'Company Name' --enable"
    echo "   📊 System status: python manage.py check --deploy"
else
    echo ""
    echo "⚠️  Complete the steps above before starting the server."
    echo "🔄 Re-run this script after completing steps to see updated status."
fi