from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings


class TenantSettings(models.Model):
    """Tenant-specific configuration settings stored in tenant schema"""
    setting_key = models.CharField(max_length=100, unique=True)
    setting_value = models.JSONField()
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['setting_key']
    
    def __str__(self):
        return f"{self.setting_key}: {self.setting_value}"


class AuditLog(models.Model):
    """Audit log for tracking changes within tenant"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    changes = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} on {self.model_name} at {self.timestamp}"
