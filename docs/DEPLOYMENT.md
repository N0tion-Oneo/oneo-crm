# Oneo CRM Deployment Guide

## Prerequisites

### System Requirements
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (for containerized deployment)
- Git

### Hardware Requirements (Minimum)
- **Development**: 4GB RAM, 2 CPU cores, 20GB storage
- **Production**: 8GB RAM, 4 CPU cores, 100GB storage (SSD recommended)

## Development Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd oneo-crm
```

### 2. Automated Setup
```bash
./setup.sh
```

### 3. Manual Setup (Alternative)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials
```

### 4. Start Services
```bash
# Start PostgreSQL and Redis
docker compose up -d db redis

# Wait for services to be ready
docker compose ps
```

### 5. Database Setup
```bash
# Run migrations
python manage.py migrate_schemas

# Create superuser (for public schema)
python manage.py createsuperuser

# Create first tenant
python manage.py create_tenant "Demo Company" "demo.localhost"
```

### 6. Start Development Server
```bash
python manage.py runserver
```

### 7. Access the Application
- **Admin Interface**: http://localhost:8000/admin/
- **Tenant Interface**: http://demo.localhost:8000/
- **Health Check**: http://localhost:8000/health/

## Production Deployment

### 1. Server Preparation

#### Ubuntu/Debian
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib redis-server nginx

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

#### CentOS/RHEL
```bash
# Update system
sudo yum update -y

# Install EPEL repository
sudo yum install -y epel-release

# Install required packages
sudo yum install -y python311 python3-pip postgresql postgresql-server redis nginx

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### 2. Application Deployment

#### Option A: Docker Deployment (Recommended)
```bash
# Clone repository
git clone <repository-url>
cd oneo-crm

# Create production environment file
cp .env.example .env.production
# Edit .env.production with production values

# Build and start services
docker compose -f docker-compose.prod.yml up -d
```

#### Option B: Traditional Deployment
```bash
# Create application user
sudo useradd -m -s /bin/bash oneo-crm
sudo su - oneo-crm

# Clone and setup application
git clone <repository-url>
cd oneo-crm
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with production values
```

### 3. Database Configuration

#### PostgreSQL Setup
```bash
# Create database and user
sudo -u postgres psql
```

```sql
CREATE DATABASE oneo_crm;
CREATE USER oneo_crm_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE oneo_crm TO oneo_crm_user;
ALTER USER oneo_crm_user CREATEDB;
\q
```

#### Run Migrations
```bash
python manage.py migrate_schemas
python manage.py collectstatic --noinput
```

### 4. Web Server Configuration

#### Nginx Configuration
```nginx
# /etc/nginx/sites-available/oneo-crm
server {
    listen 80;
    server_name your-domain.com *.your-domain.com;
    
    location /static/ {
        alias /path/to/oneo-crm/staticfiles/;
        expires 30d;
    }
    
    location /media/ {
        alias /path/to/oneo-crm/media/;
        expires 30d;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/oneo-crm /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Process Management

#### Systemd Service
```ini
# /etc/systemd/system/oneo-crm.service
[Unit]
Description=Oneo CRM Django Application
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=oneo-crm
Group=oneo-crm
WorkingDirectory=/home/oneo-crm/oneo-crm
Environment=DJANGO_SETTINGS_MODULE=oneo_crm.settings
ExecStart=/home/oneo-crm/oneo-crm/venv/bin/python manage.py runserver 127.0.0.1:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable oneo-crm
sudo systemctl start oneo-crm
sudo systemctl status oneo-crm
```

## SSL Configuration

### Using Certbot (Let's Encrypt)
```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d '*.your-domain.com'

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Environment Variables

### Required Variables
```bash
# Django Settings
SECRET_KEY=your-very-secure-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,*.your-domain.com

# Database
DB_NAME=oneo_crm
DB_USER=oneo_crm_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/1

# CORS (for frontend)
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://app.your-domain.com
```

### Optional Variables
```bash
# Email (for future use)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=app-password

# Sentry (for error tracking)
SENTRY_DSN=https://your-sentry-dsn

# AWS S3 (for file storage)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket
```

## Monitoring

### Health Checks
```bash
# Application health
curl -f http://localhost:8000/health/ || exit 1

# Database health
python manage.py check --database default

# Redis health
redis-cli ping
```

### Log Files
- **Application**: `/var/log/oneo-crm/app.log`
- **Nginx**: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **PostgreSQL**: `/var/log/postgresql/postgresql-15-main.log`

## Backup Strategy

### Database Backup
```bash
# Full backup
pg_dump -U oneo_crm_user -h localhost oneo_crm > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U oneo_crm_user -h localhost oneo_crm | gzip > ${BACKUP_DIR}/oneo_crm_${DATE}.sql.gz
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +7 -delete
```

### File Backup
```bash
# Backup media files and static files
tar -czf backup_files_$(date +%Y%m%d_%H%M%S).tar.gz media/ staticfiles/
```

## Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check database connectivity
python manage.py dbshell
```

#### Permission Errors
```bash
# Fix file permissions
sudo chown -R oneo-crm:oneo-crm /home/oneo-crm/oneo-crm
sudo chmod -R 755 /home/oneo-crm/oneo-crm
```

#### Nginx Configuration Issues
```bash
# Test configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log
```

## Security Hardening

### Firewall Configuration
```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Block direct access to database and Redis
sudo ufw deny 5432
sudo ufw deny 6379
```

### Database Security
```bash
# Edit PostgreSQL configuration
sudo nano /etc/postgresql/15/main/postgresql.conf
# Set: listen_addresses = 'localhost'

sudo nano /etc/postgresql/15/main/pg_hba.conf
# Ensure only local connections allowed
```

### Application Security
- Use strong SECRET_KEY
- Set DEBUG=False in production
- Regularly update dependencies
- Monitor security advisories

## Performance Optimization

### Database Optimization
```sql
-- Create additional indexes for performance
CREATE INDEX CONCURRENTLY idx_tenant_created_on ON django_tenants_tenant(created_on);
CREATE INDEX CONCURRENTLY idx_domain_tenant_id ON django_tenants_domain(tenant_id);
```

### Application Optimization
```python
# In production settings
DATABASES['default']['CONN_MAX_AGE'] = 600  # Connection pooling
CACHES['default']['OPTIONS']['CONNECTION_POOL_KWARGS'] = {'max_connections': 100}
```

### System Optimization
```bash
# PostgreSQL tuning
sudo nano /etc/postgresql/15/main/postgresql.conf
# Adjust based on system resources:
# shared_buffers = 256MB
# effective_cache_size = 1GB
# maintenance_work_mem = 64MB
```