# Oneo CRM Troubleshooting Guide

## Common Issues and Solutions

### 1. Application Won't Start

#### Issue: `ImproperlyConfigured: DATABASE_ROUTERS setting must contain 'django_tenants.routers.TenantSyncRouter'`

**Solution:**
```python
# Add to settings.py
DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']
```

#### Issue: `django.db.utils.OperationalError: FATAL: database "oneo_crm" does not exist`

**Solution:**
```bash
# Create database
sudo -u postgres createdb oneo_crm
sudo -u postgres createuser oneo_crm_user
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE oneo_crm TO oneo_crm_user;"
sudo -u postgres psql -c "ALTER USER oneo_crm_user CREATEDB;"
```

#### Issue: `Redis ConnectionError: Error 111 connecting to 127.0.0.1:6379. Connection refused.`

**Solution:**
```bash
# Start Redis
sudo systemctl start redis-server
# Or using Docker
docker compose up -d redis
```

### 2. Multi-tenant Issues

#### Issue: Tenant not found / Schema doesn't exist

**Symptoms:**
- 404 errors for tenant domains
- "relation does not exist" errors

**Diagnosis:**
```bash
# Check if tenant exists
python manage.py shell
```
```python
from tenants.models import Tenant, Domain
print(Tenant.objects.all())
print(Domain.objects.all())
```

**Solution:**
```bash
# Create missing tenant
python manage.py create_tenant "Company Name" "company.localhost"

# Or migrate existing tenant
python manage.py migrate_schemas --tenant
```

#### Issue: Cross-tenant data leakage

**Symptoms:**
- Users seeing data from other tenants
- Cache returning wrong tenant data

**Diagnosis:**
```python
# Check current tenant context
from django_tenants.utils import get_current_tenant
print(get_current_tenant())

# Verify cache keys
from core.cache import tenant_cache_key
print(tenant_cache_key("test_key"))
```

**Solution:**
- Verify domain configuration
- Clear cache: `python manage.py shell -c "from django.core.cache import cache; cache.clear()"`
- Check middleware order in settings

### 3. Database Issues

#### Issue: Migration fails with "permission denied to create extension"

**Solution:**
```sql
-- Connect as superuser
sudo -u postgres psql oneo_crm
-- Grant permissions
ALTER USER oneo_crm_user SUPERUSER;
-- Or create extensions manually
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

#### Issue: JSONB queries are slow

**Diagnosis:**
```sql
-- Check if GIN indexes exist
\d+ auth_user
\d+ core_tenantsettings
```

**Solution:**
```sql
-- Create missing indexes
CREATE INDEX CONCURRENTLY idx_user_metadata_gin ON auth_user USING GIN (metadata);
CREATE INDEX CONCURRENTLY idx_tenant_permissions_gin ON auth_user USING GIN (tenant_permissions);
CREATE INDEX CONCURRENTLY idx_tenant_settings_gin ON core_tenantsettings USING GIN (setting_value);
```

#### Issue: Too many database connections

**Symptoms:**
- "too many connections for role" errors
- Connection timeouts

**Solution:**
```python
# In settings.py
DATABASES['default']['CONN_MAX_AGE'] = 600
DATABASES['default']['OPTIONS'] = {
    'MAX_CONNS': 20
}
```

### 4. Cache Issues

#### Issue: Cache not working / stale data

**Diagnosis:**
```bash
# Test Redis connection
redis-cli ping

# Check cache configuration
python manage.py shell
```
```python
from django.core.cache import cache
cache.set('test', 'value', 60)
print(cache.get('test'))
```

**Solution:**
```bash
# Clear all cache
redis-cli FLUSHALL

# Restart Redis
sudo systemctl restart redis-server
```

#### Issue: Cache keys colliding between tenants

**Symptoms:**
- Wrong data returned for different tenants
- Cache invalidation affecting other tenants

**Solution:**
- Verify `tenant_cache_key()` function usage
- Check cache key prefixes in logs
- Clear cache and verify tenant isolation

### 5. Performance Issues

#### Issue: Slow page load times

**Diagnosis:**
```bash
# Enable query logging
# In settings.py (development only)
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}
```

**Solution:**
- Add database indexes for frequently queried fields
- Use `select_related()` and `prefetch_related()` in queries
- Implement caching for expensive operations
- Optimize database queries

#### Issue: High memory usage

**Diagnosis:**
```bash
# Monitor memory usage
top -p $(pgrep -f "python manage.py runserver")

# Check Django memory usage
python manage.py shell
```
```python
import psutil
import os
process = psutil.Process(os.getpid())
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

**Solution:**
- Implement proper pagination
- Clear unused cache entries
- Optimize Django queries
- Consider using a production WSGI server (gunicorn)

### 6. Development Environment Issues

#### Issue: Docker services won't start

**Diagnosis:**
```bash
docker compose ps
docker compose logs db
docker compose logs redis
```

**Solution:**
```bash
# Remove containers and volumes
docker compose down -v
docker compose up -d

# Check port conflicts
sudo netstat -tulpn | grep :5432
sudo netstat -tulpn | grep :6379
```

#### Issue: `manage.py` commands fail

**Symptoms:**
- Commands hang or fail silently
- Import errors

**Solution:**
```bash
# Verify virtual environment
which python
pip list

# Check Django installation
python -c "import django; print(django.get_version())"

# Verify environment variables
python manage.py shell -c "from django.conf import settings; print(settings.DATABASES)"
```

### 7. Testing Issues

#### Issue: Tests fail due to schema isolation

**Symptoms:**
- Tests can see data from other tests
- TenantTestCase failures

**Solution:**
```python
# Use proper test classes
from django_tenants.test.cases import TenantTestCase

class MyTestCase(TenantTestCase):
    def setUp(self):
        # Ensure clean tenant context
        super().setUp()
```

#### Issue: Test database creation fails

**Solution:**
```bash
# Grant test database creation permissions
sudo -u postgres psql -c "ALTER USER oneo_crm_user CREATEDB;"

# Or use separate test settings
python manage.py test --settings=oneo_crm.test_settings
```

### 8. Production Issues

#### Issue: Static files not loading

**Solution:**
```bash
# Collect static files
python manage.py collectstatic --noinput

# Check Nginx configuration
sudo nginx -t
sudo systemctl reload nginx

# Verify file permissions
ls -la /path/to/staticfiles/
```

#### Issue: SSL certificate errors

**Solution:**
```bash
# Renew certificate
sudo certbot renew

# Check certificate status
sudo certbot certificates

# Verify Nginx SSL configuration
sudo nginx -t
```

## Debugging Tools and Commands

### Useful Django Commands

```bash
# Check system status
python manage.py check

# Database shell
python manage.py dbshell

# Django shell with tenant context
python manage.py tenant_command shell --schema=tenant1

# Show migrations
python manage.py showmigrations

# Validate models
python manage.py validate
```

### Database Debugging

```sql
-- Show all schemas
SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast');

-- Show tables in tenant schema
\dt tenant1.*

-- Check active connections
SELECT pid, usename, application_name, client_addr, state FROM pg_stat_activity;

-- Show slow queries
SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

### Cache Debugging

```bash
# Redis CLI commands
redis-cli
> KEYS *
> FLUSHALL
> INFO memory
> MONITOR
```

### Log Analysis

```bash
# Follow application logs
tail -f /var/log/oneo-crm/app.log

# Search for errors
grep -i error /var/log/oneo-crm/app.log

# Analyze Nginx logs
tail -f /var/log/nginx/access.log | grep -v "200\|304"
```

## Performance Monitoring

### Key Metrics to Monitor

1. **Response Times**
   - Average response time < 200ms
   - 95th percentile < 500ms

2. **Database Performance**
   - Connection pool utilization
   - Query execution time
   - Index hit ratio > 95%

3. **Memory Usage**
   - Application memory growth
   - Redis memory usage
   - Available system memory

4. **Cache Performance**
   - Cache hit ratio > 80%
   - Cache eviction rate
   - Key expiration patterns

### Monitoring Commands

```bash
# System resources
htop
iostat -x 1
free -h

# Database performance
sudo -u postgres psql -c "SELECT * FROM pg_stat_database WHERE datname='oneo_crm';"

# Redis performance
redis-cli info stats
```

## Emergency Procedures

### Database Recovery

```bash
# Restore from backup
sudo -u postgres psql -c "DROP DATABASE oneo_crm;"
sudo -u postgres psql -c "CREATE DATABASE oneo_crm;"
sudo -u postgres psql oneo_crm < backup.sql
```

### Application Recovery

```bash
# Emergency restart
sudo systemctl restart oneo-crm
sudo systemctl restart nginx

# Rollback deployment
git checkout previous-stable-commit
sudo systemctl restart oneo-crm
```

### Cache Recovery

```bash
# Clear all cache
redis-cli FLUSHALL

# Restart Redis
sudo systemctl restart redis-server
```

## Getting Help

### Log Files to Check
1. Application logs: `/var/log/oneo-crm/app.log`
2. Django logs: Check `LOGGING` configuration in settings
3. Database logs: `/var/log/postgresql/`
4. Web server logs: `/var/log/nginx/`
5. System logs: `journalctl -u oneo-crm`

### Information to Gather Before Reporting Issues
1. Error message and full stack trace
2. Steps to reproduce the issue
3. Environment details (development/production)
4. Recent changes or deployments
5. Relevant log entries
6. System resource usage at time of issue

### Community Resources
- Django documentation: https://docs.djangoproject.com/
- django-tenants documentation: https://django-tenants.readthedocs.io/
- PostgreSQL documentation: https://www.postgresql.org/docs/
- Redis documentation: https://redis.io/documentation