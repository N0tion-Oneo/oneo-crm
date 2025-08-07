"""
Django settings for oneo_crm project.
Multi-tenant configuration with django-tenants for schema isolation.
"""

import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = config('SECRET_KEY', default='django-insecure-development-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)

# Enhanced logging for debugging tenant issues
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django_tenants': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
# Dynamic ALLOWED_HOSTS configuration
# Use wildcard and base hosts - tenant domains will be validated by django-tenants middleware
ALLOWED_HOSTS = [
    'localhost', 
    '127.0.0.1',
    '.localhost',  # Subdomain wildcard for development (demo.localhost, test.localhost, etc.)
    '.example.com',  # Production domain pattern (customize as needed)
]

# Add environment-configured hosts
env_hosts = config('ALLOWED_HOSTS', default='').split(',')
if env_hosts and env_hosts != ['']:
    ALLOWED_HOSTS.extend([host.strip() for host in env_hosts if host.strip()])

# Database configuration for multi-tenancy
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': config('DB_NAME', default='oneo_crm'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'sslmode': 'prefer',  # Use SSL if available
        }
    }
}

# Multi-tenant configuration
TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"

# Database routing for multi-tenancy
DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']

# Apps configuration - shared across all tenants
SHARED_APPS = [
    'daphne',  # ASGI server - must be first for runserver override
    'django_tenants',  # Must be second for tenant support
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',  # DRF for API endpoints
    'rest_framework_simplejwt',  # JWT authentication
    'corsheaders',
    'tenants',
    'authentication',  # Custom authentication app
]

# Apps specific to each tenant
TENANT_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'rest_framework',  # DRF for tenant-specific APIs
    'django_filters',  # Advanced filtering
    'drf_spectacular',  # OpenAPI documentation
    'channels',  # Real-time support
    'django_extensions',  # For debugging URLs
    'core',
    'authentication',  # Authentication app in tenant context
    'pipelines',  # Pipeline system app
    'relationships',  # Relationship engine app
    'api',  # Phase 05 - API Layer
    'realtime',  # Phase 06 - Real-time collaboration
    'workflows',  # Phase 07 - Workflow Automation  
    'communications',  # Phase 08 - Communication Layer
    'duplicates',  # Duplicate detection system
    'ai',  # Phase 09 - AI Integration & Intelligent Workflows
]

# Combine apps (avoid duplicates)
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

# Middleware configuration
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',  # Must be first
    'core.middleware.MaintenanceModeMiddleware',  # Block access during maintenance
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    # Temporarily disabled async middleware for testing
    # 'authentication.middleware.AsyncSessionAuthenticationMiddleware',  # Custom async auth
    # 'authentication.middleware.AsyncTenantMiddleware',  # Tenant context for async
    # 'authentication.middleware.AsyncPermissionMiddleware',  # Permission context
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.monitoring.PerformanceMiddleware',  # Performance monitoring
]

# URL configuration for multi-tenant routing
ROOT_URLCONF = 'oneo_crm.urls_tenants'  # Tenant-specific URLs
PUBLIC_SCHEMA_URLCONF = 'oneo_crm.urls_public'  # Public schema URLs

# Template configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI/ASGI application
WSGI_APPLICATION = 'oneo_crm.wsgi.application'
ASGI_APPLICATION = 'oneo_crm.asgi.application'

# Redis Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Cache configuration
CACHE_TTL = 60 * 15  # 15 minutes
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# REST Framework Configuration (JWT + comprehensive settings)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'authentication.jwt_authentication.TenantAwareJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',  # Fallback for browsable API
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'api.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 50,
    'MAX_PAGE_SIZE': 1000,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Configuration
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    
    'JTI_CLAIM': 'jti',
    
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(hours=1),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS configuration for multi-tenant subdomains
# Allow all localhost subdomains for development
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Only in development
CORS_ALLOWED_ORIGINS = []

if not DEBUG:
    # In production, configure specific origins
    CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ALLOWED_ORIGINS if origin.strip()]

# For development, we also need to allow wildcard subdomains
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://.*\.localhost:3000$",  # Any subdomain of localhost:3000
    r"^http://localhost:3000$",     # Regular localhost:3000
    r"^http://127\.0\.0\.1:3000$",  # IP address access
] if DEBUG else []

CORS_ALLOW_CREDENTIALS = True

# CSRF trusted origins for development
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://demo.localhost:3000',
    'http://testorg.localhost:3000',
    'http://*.localhost:3000',  # Wildcard for any subdomain
] if DEBUG else []

# Allow custom headers including tenant header
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-tenant',  # Custom tenant header for multi-tenant support
]

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# HTTPS settings (enable in production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Custom User Model
AUTH_USER_MODEL = 'authentication.CustomUser'

# Session security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 60 * 60 * 24  # 24 hours

# Duplicate REST_FRAMEWORK configuration removed - merged into main config above

# DRF Spectacular settings for OpenAPI
SPECTACULAR_SETTINGS = {
    'TITLE': 'Oneo CRM API',
    'DESCRIPTION': 'Comprehensive API for the Oneo CRM system with dynamic pipeline support',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAuthenticated'],
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    # 'PREPROCESSING_HOOKS': [
    #     'api.schema.custom_preprocessing_hook',
    # ],
}

# GraphQL Configuration removed - using DRF only

# Channels Configuration for WebSocket support
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [config('REDIS_URL', default='redis://127.0.0.1:6379/2')],
        },
    },
}

# WebSocket settings
ALLOWED_WEBSOCKET_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://your-domain.com",
    # Allow tenant subdomains for development
    "http://demo.localhost:3000",
    "http://demoorg.localhost:3000", 
    "http://test.localhost:3000",
    "http://testorg.localhost:3000",
    # Pattern for any *.localhost:3000 subdomain (development)
    "http://*.localhost:3000",
]

# SSE settings
SSE_HEARTBEAT_INTERVAL = 30  # seconds
SSE_MAX_CONNECTION_TIME = 3600  # 1 hour

# Rate limiting configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_VIEW = 'api.views.ratelimit_exceeded'

# API Security settings
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
API_RATE_LIMITS = {
    'burst': '60/min',
    'sustained': '1000/hour', 
    'graphql': '100/min',
    'apikey': '10000/hour',
}

# Security middleware
SECURITY_MIDDLEWARE_ENABLED = True
SUSPICIOUS_PATTERN_DETECTION = True
MAX_SECURITY_VIOLATIONS_PER_HOUR = 10

# Celery Configuration (for future use)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/1')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://127.0.0.1:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django_tenants': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'pipelines': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Tenant AI Configuration Encryption
TENANT_AI_ENCRYPTION_KEY = config('TENANT_AI_ENCRYPTION_KEY', default='dummy-key-for-development-only-replace-in-prod')

# AI processing is now purely tenant-based - no global OpenAI key
# Each tenant must configure their own OpenAI API key via tenant settings

# AI Field Configuration
AI_MAX_TOOL_BUDGET = {
    'web_search': 10,
    'code_interpreter': 5,
    'dalle': 3,
}
AI_MAX_TIMEOUT = 600  # 10 minutes maximum

# Pipeline System Configuration
PIPELINE_CONFIG = {
    'MAX_FIELDS_PER_PIPELINE': 50,
    'MAX_RECORDS_PER_PIPELINE': 10000,
    'DEFAULT_CACHE_DURATION': 3600,  # 1 hour
    'AI_FIELD_PROCESSING_ENABLED': True,
}

# File upload configuration for pipeline file fields
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Celery Configuration for Workflow Tasks
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Workflow System Configuration
WORKFLOW_CONFIG = {
    'MAX_CONCURRENT_EXECUTIONS': 10,
    'DEFAULT_EXECUTION_TIMEOUT': 3600,  # 1 hour
    'MAX_EXECUTION_RETRIES': 3,
    'APPROVAL_TIMEOUT_HOURS': 24,
    'SCHEDULE_CHECK_INTERVAL': 60,  # seconds
    'CLEANUP_RETENTION_DAYS': 30,
}