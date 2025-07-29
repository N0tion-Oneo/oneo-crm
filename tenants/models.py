from django_tenants.models import TenantMixin, DomainMixin
from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import json


class Tenant(TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    
    # Tenant-specific settings
    max_users = models.IntegerField(default=100)
    features_enabled = models.JSONField(default=dict)
    billing_settings = models.JSONField(default=dict)
    
    # AI Configuration (encrypted)
    ai_config_encrypted = models.TextField(blank=True, null=True, help_text="Encrypted AI configuration including API keys")
    ai_enabled = models.BooleanField(default=False, help_text="Enable AI features for this tenant")
    ai_usage_limit = models.DecimalField(max_digits=10, decimal_places=2, default=100.00, help_text="Monthly AI usage limit in USD")
    ai_current_usage = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Current month AI usage in USD")
    
    # Auto-create schema
    auto_create_schema = True
    auto_drop_schema = False
    
    def __str__(self):
        return self.name
    
    @property
    def encryption_key(self):
        """Get or create encryption key for this tenant"""
        if hasattr(settings, 'TENANT_AI_ENCRYPTION_KEY'):
            return settings.TENANT_AI_ENCRYPTION_KEY.encode()
        else:
            # Fallback to a default key (should be in settings for production)
            return b'dummy-key-for-development-only-replace-in-prod'
    
    def get_ai_config(self):
        """Decrypt and return AI configuration"""
        if not self.ai_config_encrypted:
            return {}
        
        try:
            # Create Fernet instance with tenant's encryption key
            f = Fernet(base64.urlsafe_b64encode(self.encryption_key[:32]))
            
            # Decrypt the config
            decrypted_data = f.decrypt(self.ai_config_encrypted.encode())
            return json.loads(decrypted_data.decode())
        except Exception as e:
            # Log error and return empty config
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to decrypt AI config for tenant {self.name}: {e}")
            return {}
    
    def set_ai_config(self, config_dict):
        """Encrypt and store AI configuration"""
        try:
            # Create Fernet instance with tenant's encryption key
            f = Fernet(base64.urlsafe_b64encode(self.encryption_key[:32]))
            
            # Encrypt the config
            config_json = json.dumps(config_dict)
            encrypted_data = f.encrypt(config_json.encode())
            self.ai_config_encrypted = encrypted_data.decode()
            
            return True
        except Exception as e:
            # Log error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to encrypt AI config for tenant {self.name}: {e}")
            return False
    
    def get_openai_api_key(self):
        """Get OpenAI API key for this tenant"""
        ai_config = self.get_ai_config()
        return ai_config.get('openai_api_key')
    
    def set_openai_api_key(self, api_key):
        """Set OpenAI API key for this tenant"""
        ai_config = self.get_ai_config()
        ai_config['openai_api_key'] = api_key
        return self.set_ai_config(ai_config)
    
    def get_ai_model_preferences(self):
        """Get AI model preferences for this tenant"""
        ai_config = self.get_ai_config()
        return ai_config.get('model_preferences', {
            'default_model': 'gpt-4',
            'temperature': 0.3,
            'max_tokens': None,
            'timeout': 120
        })
    
    def can_use_ai_features(self):
        """Check if tenant can use AI features"""
        return (
            self.ai_enabled and 
            self.get_openai_api_key() and 
            self.ai_current_usage < self.ai_usage_limit
        )
    
    def record_ai_usage(self, cost_usd):
        """Record AI usage cost"""
        self.ai_current_usage += cost_usd
        self.save(update_fields=['ai_current_usage'])
    
    def reset_monthly_usage(self):
        """Reset monthly AI usage (called by scheduled task)"""
        self.ai_current_usage = 0.00
        self.save(update_fields=['ai_current_usage'])


class TenantUniPileConfig(models.Model):
    """Tenant-level UniPile API configuration"""
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='unipile_config')
    
    # UniPile API Configuration
    dsn = models.CharField(max_length=255, help_text="UniPile Data Source Name")
    access_token_encrypted = models.TextField(help_text="Encrypted UniPile access token")
    webhook_secret = models.CharField(max_length=255, help_text="Webhook verification secret")
    
    # Message tracking settings
    auto_create_contacts = models.BooleanField(default=True, help_text="Auto-create contact records from messages")
    default_contact_pipeline = models.ForeignKey(
        'pipelines.Pipeline', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Default pipeline for auto-created contacts"
    )
    default_contact_status = models.CharField(
        max_length=100, 
        default='new_lead', 
        help_text="Default status for auto-created contacts"
    )
    
    # Sync settings
    sync_historical_days = models.PositiveIntegerField(
        default=30, 
        help_text="Days of historical messages to sync on initial connection"
    )
    enable_real_time_sync = models.BooleanField(
        default=True, 
        help_text="Enable real-time message sync via webhooks"
    )
    
    # Rate limiting
    max_api_calls_per_hour = models.PositiveIntegerField(
        default=1000,
        help_text="Maximum UniPile API calls per hour"
    )
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    last_webhook_received = models.DateTimeField(null=True, blank=True)
    webhook_failures = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tenants_unipile_config'
    
    def __str__(self):
        return f"UniPile Config for {self.tenant.name}"
    
    @property
    def encryption_key(self):
        """Use tenant's encryption key"""
        return self.tenant.encryption_key
    
    def get_access_token(self):
        """Decrypt and return UniPile access token"""
        if not self.access_token_encrypted:
            return None
        
        try:
            f = Fernet(base64.urlsafe_b64encode(self.encryption_key[:32]))
            decrypted_token = f.decrypt(self.access_token_encrypted.encode())
            return decrypted_token.decode()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to decrypt UniPile token for tenant {self.tenant.name}: {e}")
            return None
    
    def set_access_token(self, token):
        """Encrypt and store UniPile access token"""
        try:
            f = Fernet(base64.urlsafe_b64encode(self.encryption_key[:32]))
            encrypted_token = f.encrypt(token.encode())
            self.access_token_encrypted = encrypted_token.decode()
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to encrypt UniPile token for tenant {self.tenant.name}: {e}")
            return False
    
    def is_configured(self):
        """Check if UniPile is properly configured"""
        return bool(self.dsn and self.get_access_token() and self.is_active)
    
    def record_webhook_success(self):
        """Record successful webhook reception"""
        self.last_webhook_received = timezone.now()
        self.webhook_failures = 0
        self.save(update_fields=['last_webhook_received', 'webhook_failures'])
    
    def record_webhook_failure(self):
        """Record webhook failure"""
        self.webhook_failures += 1
        self.save(update_fields=['webhook_failures'])


class Domain(DomainMixin):
    pass
