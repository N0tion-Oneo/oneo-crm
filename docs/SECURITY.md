# Oneo CRM Security Guide

## Overview

This document outlines security considerations, best practices, and implementation details for the Oneo CRM multi-tenant system.

## Multi-tenant Security Model

### Schema Isolation

**Primary Security Mechanism**: PostgreSQL schema-per-tenant
- Each tenant's data exists in separate database schema
- No shared tables between tenants
- Impossible cross-tenant data access at database level

**Implementation Details**:
```python
# Tenant context is always maintained
with schema_context(tenant.schema_name):
    # All database operations are isolated to this schema
    users = User.objects.all()  # Only tenant users
```

**Security Benefits**:
- Complete data isolation
- No risk of cross-tenant queries
- Database-level security enforcement
- Audit trail per tenant

### Domain-based Tenant Resolution

**Security Considerations**:
- Domain spoofing prevention
- SSL certificate validation
- Subdomain wildcard security

**Implementation**:
```python
# Domain validation in middleware
def validate_tenant_domain(request):
    host = request.get_host()
    if not Domain.objects.filter(domain=host).exists():
        raise SuspiciousOperation("Invalid tenant domain")
```

## Authentication and Authorization

### Current Implementation (Phase 01)

**Admin Authentication**:
- Django admin for public schema access
- Superuser required for tenant management
- Session-based authentication

**Future Implementation (Phase 02+)**:
- JWT token-based authentication
- Per-tenant user management
- Role-based access control (RBAC)
- Multi-factor authentication (MFA)

### Session Security

**Configuration**:
```python
# In settings.py
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
```

**Cache-based Sessions**:
- Sessions stored in Redis (tenant-isolated)
- Automatic session cleanup
- No database session table needed

## Database Security

### Connection Security

**SSL Configuration**:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'OPTIONS': {
            'sslmode': 'require',
            'sslcert': '/path/to/client-cert.pem',
            'sslkey': '/path/to/client-key.pem',
            'sslrootcert': '/path/to/ca-cert.pem',
        }
    }
}
```

**Database User Permissions**:
```sql
-- Create limited-privilege user
CREATE USER oneo_crm_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE oneo_crm TO oneo_crm_user;
GRANT USAGE ON SCHEMA public TO oneo_crm_user;
GRANT CREATE ON SCHEMA public TO oneo_crm_user;

-- Grant tenant schema permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA tenant1 TO oneo_crm_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA tenant1 TO oneo_crm_user;
```

### SQL Injection Prevention

**Django ORM Protection**:
- Always use parameterized queries
- ORM automatically escapes parameters
- Never use raw SQL with user input

**Safe Practices**:
```python
# Safe - parameterized query
users = User.objects.filter(email=user_email)

# Safe - raw query with parameters
User.objects.raw("SELECT * FROM auth_user WHERE email = %s", [user_email])

# UNSAFE - never do this
User.objects.raw(f"SELECT * FROM auth_user WHERE email = '{user_email}'")
```

### Data Encryption

**At Rest**:
- PostgreSQL database encryption (LUKS/dm-crypt)
- Encrypted backups
- Secure key management

**In Transit**:
- SSL/TLS for all connections
- Certificate pinning for API clients
- HSTS headers for web traffic

**Application Level**:
```python
# Encrypt sensitive fields
from django.contrib.auth.hashers import make_password, check_password

# For passwords
password_hash = make_password(raw_password)

# For sensitive data
from cryptography.fernet import Fernet
key = Fernet.generate_key()
cipher = Fernet(key)
encrypted_data = cipher.encrypt(sensitive_data.encode())
```

## Cache Security

### Redis Security

**Authentication**:
```bash
# redis.conf
requirepass your_secure_password
```

**Network Security**:
```bash
# Bind to localhost only
bind 127.0.0.1

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG "CONFIG_b835r4f93"
```

### Cache Isolation

**Tenant Key Prefixing**:
```python
def tenant_cache_key(key, tenant_schema=None):
    """Generate tenant-specific cache key"""
    if not tenant_schema:
        tenant_schema = get_current_tenant().schema_name
    return f"{tenant_schema}:{key}"
```

**Security Benefits**:
- No cache key collisions
- Tenant data isolation in cache
- Automatic cleanup per tenant

## Web Application Security

### Security Headers

**Implementation**:
```python
# In settings.py
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
```

### CSRF Protection

**Django Built-in Protection**:
```python
# Enabled by default
MIDDLEWARE = [
    'django.middleware.csrf.CsrfViewMiddleware',
    # ...
]

# Template usage
{% csrf_token %}
```

**API Protection**:
```python
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token

# For API endpoints, use custom token validation
def api_csrf_protection(view_func):
    def wrapper(request, *args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE']:
            token = request.META.get('HTTP_X_CSRFTOKEN')
            if not token or token != get_token(request):
                return HttpResponseForbidden('CSRF token missing or invalid')
        return view_func(request, *args, **kwargs)
    return wrapper
```

### Input Validation

**Form Validation**:
```python
from django import forms
from django.core.validators import RegexValidator

class TenantForm(forms.ModelForm):
    name = forms.CharField(
        max_length=100,
        validators=[RegexValidator(r'^[a-zA-Z0-9\s]+$', 'Only alphanumeric characters allowed')]
    )
    
    def clean_name(self):
        name = self.cleaned_data['name']
        # Additional validation logic
        return name
```

**JSONB Validation**:
```python
import json
from django.core.exceptions import ValidationError

def validate_json_field(value):
    if not isinstance(value, dict):
        raise ValidationError('Value must be a valid JSON object')
    
    # Validate structure and content
    allowed_keys = ['option1', 'option2', 'option3']
    for key in value.keys():
        if key not in allowed_keys:
            raise ValidationError(f'Invalid key: {key}')
```

## API Security (Future Implementation)

### Authentication

**JWT Implementation**:
```python
# Token-based authentication
import jwt
from django.conf import settings

def generate_jwt_token(user, tenant):
    payload = {
        'user_id': user.id,
        'tenant_id': tenant.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
```

### Rate Limiting

**Implementation Strategy**:
```python
from django.core.cache import cache
from django.http import HttpResponseTooManyRequests

def rate_limit(max_requests=100, window=3600):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            tenant = get_current_tenant()
            key = f"rate_limit:{tenant.schema_name}:{request.META['REMOTE_ADDR']}"
            
            current = cache.get(key, 0)
            if current >= max_requests:
                return HttpResponseTooManyRequests()
            
            cache.set(key, current + 1, window)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### API Versioning Security

**Version Control**:
```python
# Ensure backward compatibility doesn't compromise security
API_VERSION_SECURITY_POLICY = {
    'v1': {'deprecated': True, 'sunset_date': '2024-12-31'},
    'v2': {'current': True, 'security_features': ['rate_limiting', 'jwt_auth']},
}
```

## Infrastructure Security

### Network Security

**Firewall Rules**:
```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 5432/tcp   # PostgreSQL (internal only)
ufw deny 6379/tcp   # Redis (internal only)
```

**Network Segmentation**:
- Database server isolated from public network
- Redis accessible only from application servers
- Load balancers in DMZ
- Application servers in private subnet

### Server Hardening

**System Security**:
```bash
# Disable root login
echo "PermitRootLogin no" >> /etc/ssh/sshd_config

# SSH key authentication only
echo "PasswordAuthentication no" >> /etc/ssh/sshd_config

# Automatic security updates
echo 'Unattended-Upgrade::Automatic-Reboot "false";' >> /etc/apt/apt.conf.d/50unattended-upgrades
```

**Application User**:
```bash
# Create dedicated user
useradd -r -s /bin/false oneo-crm
# No shell access, no home directory
```

### Logging and Monitoring

**Security Event Logging**:
```python
import logging

security_logger = logging.getLogger('security')

def log_security_event(event_type, user, tenant, details):
    security_logger.warning(
        f"Security event: {event_type}",
        extra={
            'user_id': user.id if user else None,
            'tenant_id': tenant.id if tenant else None,
            'event_details': details,
            'timestamp': timezone.now(),
        }
    )
```

**Failed Login Monitoring**:
```python
from django.contrib.auth.signals import user_login_failed

def handle_failed_login(sender, credentials, **kwargs):
    log_security_event(
        'failed_login',
        user=None,
        tenant=get_current_tenant(),
        details={'username': credentials.get('username')}
    )

user_login_failed.connect(handle_failed_login)
```

## Backup Security

### Encrypted Backups

**Database Backup Encryption**:
```bash
#!/bin/bash
# Encrypted backup script
pg_dump -U oneo_crm_user oneo_crm | \
gpg --symmetric --cipher-algo AES256 --compress-algo 1 --s2k-digest-algo SHA512 \
> backup_$(date +%Y%m%d_%H%M%S).sql.gpg
```

**Secure Storage**:
- Offsite backup storage
- Access control for backup files
- Regular backup integrity testing
- Secure key management for decryption

## Compliance Considerations

### GDPR Compliance

**Data Protection Measures**:
- Right to be forgotten implementation
- Data portability features
- Consent management
- Data retention policies

**Implementation Framework**:
```python
class GDPRMixin:
    """Mixin for GDPR-compliant models"""
    
    def anonymize(self):
        """Anonymize personal data"""
        for field in self._meta.fields:
            if hasattr(field, 'personal_data') and field.personal_data:
                setattr(self, field.name, 'ANONYMIZED')
        self.save()
    
    def export_data(self):
        """Export user data for portability"""
        return {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
            if not field.name.startswith('_')
        }
```

### SOC 2 Compliance

**Security Controls**:
- Access logging and monitoring
- Change management procedures
- Incident response plan
- Regular security assessments

## Security Testing

### Automated Security Testing

**SAST Integration**:
```bash
# Static analysis with bandit
pip install bandit
bandit -r . -f json -o security_report.json
```

**Dependency Scanning**:
```bash
# Check for vulnerable dependencies
pip-audit
safety check
```

### Manual Security Testing

**Penetration Testing Checklist**:
1. SQL injection testing
2. Cross-tenant data access attempts
3. Authentication bypass testing
4. Authorization escalation testing
5. Input validation testing
6. Session management testing

## Incident Response

### Security Incident Procedures

1. **Detection and Analysis**
   - Monitor security logs
   - Identify scope of incident
   - Assess impact on tenants

2. **Containment**
   - Isolate affected systems
   - Prevent further damage
   - Preserve evidence

3. **Eradication and Recovery**
   - Remove threat
   - Restore from clean backups
   - Implement additional controls

4. **Post-Incident Activity**
   - Document lessons learned
   - Update security procedures
   - Notify affected parties

### Emergency Contacts

**Internal Team**:
- Security Lead
- Database Administrator
- System Administrator
- Legal/Compliance Team

**External Resources**:
- Incident response consultant
- Legal counsel
- Law enforcement (if required)
- Affected customers

## Security Maintenance

### Regular Security Tasks

**Weekly**:
- Review security logs
- Check for failed login attempts
- Monitor system resources

**Monthly**:
- Update dependencies
- Review access controls
- Test backup procedures
- Security training for team

**Quarterly**:
- Security assessment
- Penetration testing
- Update incident response plan
- Review and update security policies

**Annually**:
- External security audit
- Compliance assessment
- Disaster recovery testing
- Security awareness training

## Security Best Practices Summary

1. **Never trust user input** - Always validate and sanitize
2. **Principle of least privilege** - Grant minimum necessary permissions
3. **Defense in depth** - Multiple layers of security controls
4. **Fail securely** - Default to secure state on errors
5. **Keep it simple** - Complex security is often flawed security
6. **Regular updates** - Keep all components updated
7. **Monitor everything** - Log and monitor all security events
8. **Test regularly** - Regular security testing and assessments
9. **Train your team** - Security awareness for all developers
10. **Plan for incidents** - Have a response plan ready

## Resources and References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security Documentation](https://docs.djangoproject.com/en/5.0/topics/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)
- [Redis Security](https://redis.io/docs/manual/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)