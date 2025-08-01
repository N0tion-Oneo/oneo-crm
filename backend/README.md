# Oneo CRM Backend

Django-based backend API for the Oneo CRM enterprise workflow automation platform.

## Features

- **Multi-tenant Architecture**: Complete schema isolation using django-tenants
- **Advanced API Layer**: REST + GraphQL with real-time subscriptions
- **AI Integration**: OpenAI integration with tenant-specific configuration
- **Workflow Automation**: 26+ node processors across 17 specialized modules
- **Real-time Collaboration**: WebSocket support with operational transform
- **Enterprise Security**: RBAC, field-level permissions, audit trails
- **Communication Integration**: Omni-channel messaging via UniPile
- **Recovery System**: Workflow replay and intelligent error recovery

## Quick Start

```bash
# Setup environment
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run migrations
python manage.py migrate_schemas

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

## Access Points

- **Admin Interface**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/v1/docs/
- **GraphQL Playground**: http://localhost:8000/graphql/
- **Demo Tenant**: http://demo.localhost:8000/

## Management Commands

```bash
# Create new tenant
python manage.py create_tenant "Company Name" "company.localhost"

# Configure AI for tenant
python manage.py configure_tenant_ai "Company Name" --enable

# Setup recovery system
python manage.py setup_recovery_system

# Run system tests
python test_full_integration.py
```

## Architecture

The backend is organized into the following Django apps:

- **authentication**: Custom user model with async permissions
- **tenants**: Multi-tenant management and configuration
- **pipelines**: Dynamic schema system with 18+ field types
- **relationships**: Graph traversal and bidirectional relationships
- **workflows**: Advanced workflow automation with recovery
- **communications**: Omni-channel messaging and tracking
- **api**: REST/GraphQL APIs with real-time features
- **realtime**: WebSocket consumers and operational transform
- **monitoring**: System health and performance tracking