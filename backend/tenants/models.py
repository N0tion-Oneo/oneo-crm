from django_tenants.models import TenantMixin, DomainMixin
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import json

User = get_user_model()


class Tenant(TenantMixin):
    name = models.CharField(max_length=100)
    created_on = models.DateTimeField(auto_now_add=True)
    
    # Tenant-specific settings
    max_users = models.IntegerField(default=100)
    features_enabled = models.JSONField(default=dict)
    billing_settings = models.JSONField(default=dict)
    
    # Organization Profile
    organization_logo = models.ImageField(upload_to='tenant_logos/', null=True, blank=True)
    organization_description = models.TextField(blank=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=20, blank=True)
    business_hours = models.JSONField(default=dict, help_text="Business hours by day of week")
    
    # Localization Settings (stored in JSON)
    localization_settings = models.JSONField(
        default=dict,
        help_text="Contains: timezone, date_format, time_format, currency, language, week_start_day"
    )
    
    # Branding Settings (stored in JSON)
    branding_settings = models.JSONField(
        default=dict,
        help_text="Contains: primary_color, secondary_color, email_header_html, login_message"
    )
    
    # Security Policies (stored in JSON)
    security_policies = models.JSONField(
        default=dict,
        help_text="Contains: password_min_length, password_complexity, session_timeout_minutes, require_2fa, ip_whitelist"
    )
    
    # Data Policies (stored in JSON)
    data_policies = models.JSONField(
        default=dict,
        help_text="Contains: retention_days, backup_frequency, auto_archive_days, export_formats"
    )
    
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
    
    def get_default_localization(self):
        """Get default localization settings"""
        return {
            'timezone': 'UTC',
            'date_format': 'MM/DD/YYYY',
            'time_format': '12h',
            'currency': 'USD',
            'language': 'en',
            'week_start_day': 'sunday'
        }
    
    def get_default_branding(self):
        """Get default branding settings"""
        return {
            'primary_color': '#3B82F6',  # Blue
            'secondary_color': '#10B981',  # Green
            'email_header_html': '',
            'login_message': ''
        }
    
    def get_default_security_policies(self):
        """Get default security policies"""
        return {
            'password_min_length': 8,
            'password_complexity': {
                'require_uppercase': True,
                'require_lowercase': True,
                'require_numbers': True,
                'require_special': False
            },
            'session_timeout_minutes': 60,
            'require_2fa': False,
            'ip_whitelist': []
        }
    
    def get_default_data_policies(self):
        """Get default data policies"""
        return {
            'retention_days': 365,
            'backup_frequency': 'daily',
            'auto_archive_days': 90,
            'export_formats': ['csv', 'json', 'excel']
        }
    
    def save(self, *args, **kwargs):
        """Override save to set defaults for JSON fields if empty"""
        if not self.localization_settings:
            self.localization_settings = self.get_default_localization()
        if not self.branding_settings:
            self.branding_settings = self.get_default_branding()
        if not self.security_policies:
            self.security_policies = self.get_default_security_policies()
        if not self.data_policies:
            self.data_policies = self.get_default_data_policies()
        super().save(*args, **kwargs)
    
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



class TenantMaintenance(models.Model):
    """
    Track tenant maintenance mode status for schema migrations and system updates
    When active, all tenant access is blocked except for superusers
    """
    tenant = models.OneToOneField(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='maintenance',
        help_text="Tenant under maintenance"
    )
    
    # Maintenance status
    is_active = models.BooleanField(
        default=False,
        help_text="Whether maintenance mode is currently active"
    )
    reason = models.CharField(
        max_length=200,
        help_text="Reason for maintenance (e.g., 'Schema Migration', 'System Update')"
    )
    
    # Timing information
    started_at = models.DateTimeField(
        default=timezone.now,
        help_text="When maintenance mode was activated"
    )
    estimated_completion = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Estimated completion time"
    )
    completed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When maintenance mode was deactivated"
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(
        default=0,
        help_text="Progress percentage (0-100)"
    )
    status_message = models.TextField(
        blank=True,
        help_text="Current status message to display to users"
    )
    
    # Migration specific data
    migration_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of migration being performed (field_rename, type_change, etc.)"
    )
    migration_data = models.JSONField(
        default=dict,
        help_text="Migration-specific data and parameters"
    )
    
    # Tracking
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="User who initiated maintenance mode"
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['started_at']),
        ]
        ordering = ['-started_at']
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.tenant.name} - {status} - {self.reason}"
    
    @property
    def duration_seconds(self):
        """Get duration of maintenance in seconds"""
        end_time = self.completed_at or timezone.now()
        return (end_time - self.started_at).total_seconds()
    
    @property
    def is_overdue(self):
        """Check if maintenance is taking longer than estimated"""
        if not self.estimated_completion or not self.is_active:
            return False
        return timezone.now() > self.estimated_completion
    
    def activate(self, reason, estimated_minutes=None, created_by=None):
        """Activate maintenance mode"""
        self.is_active = True
        self.reason = reason
        self.started_at = timezone.now()
        self.completed_at = None
        self.progress_percentage = 0
        self.created_by = created_by
        
        if estimated_minutes:
            self.estimated_completion = timezone.now() + timezone.timedelta(minutes=estimated_minutes)
        
        self.save()
    
    def deactivate(self, status_message="Maintenance completed"):
        """Deactivate maintenance mode"""
        self.is_active = False
        self.completed_at = timezone.now()
        self.progress_percentage = 100
        self.status_message = status_message
        self.save()
    
    def update_progress(self, percentage, message=""):
        """Update maintenance progress"""
        self.progress_percentage = max(0, min(100, percentage))
        if message:
            self.status_message = message
        self.save()


class Domain(DomainMixin):
    pass
