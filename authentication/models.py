"""
Authentication models for Oneo CRM
Multi-tenant user management with async support
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class UserType(models.Model):
    """User types with configurable permissions"""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    # Type classification
    is_system_default = models.BooleanField(default=False)
    is_custom = models.BooleanField(default=True)
    
    # Permissions and configuration
    base_permissions = models.JSONField(default=dict)
    dashboard_config = models.JSONField(default=dict)
    menu_permissions = models.JSONField(default=dict)
    
    # Metadata
    created_by = models.ForeignKey(
        'CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_user_types'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auth_usertype'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_system_default']),
        ]
    
    def __str__(self):
        return self.name
    
    @classmethod
    async def acreate_default_types(cls):
        """Create system default user types asynchronously"""
        defaults = [
            {
                'name': 'Admin',
                'slug': 'admin',
                'description': 'Full access to all tenant features',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'system': ['full_access'],
                    'pipelines': ['create', 'read', 'update', 'delete'],
                    'users': ['create', 'read', 'update', 'delete'],
                    'settings': ['read', 'update']
                }
            },
            {
                'name': 'Manager',
                'slug': 'manager',
                'description': 'Management access with user oversight',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'pipelines': ['create', 'read', 'update'],
                    'users': ['read', 'update'],
                    'reports': ['read', 'export']
                }
            },
            {
                'name': 'User',
                'slug': 'user',
                'description': 'Standard user access',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'pipelines': ['read', 'update'],
                    'records': ['create', 'read', 'update']
                }
            },
            {
                'name': 'Viewer',
                'slug': 'viewer',
                'description': 'Read-only access',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'pipelines': ['read'],
                    'records': ['read']
                }
            }
        ]
        
        for default in defaults:
            user_type, created = await cls.objects.aget_or_create(
                slug=default['slug'],
                defaults=default
            )
            if created:
                print(f"Created default user type: {user_type.name}")


class CustomUser(AbstractUser):
    """Extended user model with multi-tenant support and async capabilities"""
    
    # Override email to be unique and primary identifier
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # User classification
    user_type = models.ForeignKey(
        UserType, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True
    )
    
    # Preferences
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    avatar_url = models.URLField(max_length=500, blank=True)
    
    # Metadata and overrides
    metadata = models.JSONField(default=dict)
    permission_overrides = models.JSONField(default=dict)
    
    # Tracking
    created_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'auth_customuser'
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_activity']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"
    
    async def aupdate_last_activity(self):
        """Update last activity timestamp asynchronously"""
        self.last_activity = timezone.now()
        await self.asave(update_fields=['last_activity'])


class UserSession(models.Model):
    """Track user sessions for monitoring and security"""
    
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='user_sessions'
    )
    session_key = models.CharField(max_length=40, unique=True)
    
    # Session lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    
    # Session metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_info = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'auth_usersession'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.created_at}"
    
    def is_expired(self):
        """Check if session is expired"""
        return timezone.now() > self.expires_at
    
    @classmethod
    async def acleanup_expired_sessions(cls):
        """Remove expired session records asynchronously"""
        count = 0
        async for session in cls.objects.filter(expires_at__lt=timezone.now()):
            await session.adelete()
            count += 1
        return count
    
    @classmethod
    async def aget_active_sessions(cls, user):
        """Get all active sessions for a user asynchronously"""
        sessions = []
        async for session in cls.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).order_by('-last_activity'):
            sessions.append(session)
        return sessions


class ExtendedPermission(models.Model):
    """Extended permission model for fine-grained access control"""
    
    PERMISSION_TYPES = [
        ('action', 'Action Permission'),
        ('field', 'Field Permission'),
        ('pipeline', 'Pipeline Permission'),
        ('system', 'System Permission'),
    ]
    
    RESOURCE_TYPES = [
        ('pipeline', 'Pipeline'),
        ('record', 'Record'),
        ('field', 'Field'),
        ('view', 'View'),
        ('system', 'System'),
    ]
    
    # Core permission info
    name = models.CharField(max_length=255)
    codename = models.CharField(max_length=100)
    content_type = models.ForeignKey(
        'contenttypes.ContentType', 
        on_delete=models.CASCADE
    )
    
    # Extended details
    permission_type = models.CharField(max_length=50, choices=PERMISSION_TYPES)
    resource_type = models.CharField(max_length=100, choices=RESOURCE_TYPES)
    resource_id = models.CharField(max_length=100, blank=True)
    
    # Metadata
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'auth_extendedpermission'
        unique_together = ['content_type', 'codename']
        indexes = [
            models.Index(fields=['permission_type', 'resource_type']),
            models.Index(fields=['resource_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.permission_type})"


class UserTypePermission(models.Model):
    """Many-to-many relationship between user types and permissions"""
    
    user_type = models.ForeignKey(UserType, on_delete=models.CASCADE)
    permission = models.ForeignKey(ExtendedPermission, on_delete=models.CASCADE)
    
    # Permission configuration
    is_granted = models.BooleanField(default=True)
    conditions = models.JSONField(default=dict)
    
    # Relationship permissions
    traversal_depth = models.IntegerField(default=1)
    field_restrictions = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'auth_usertypepermission'
        unique_together = ['user_type', 'permission']
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['permission']),
        ]
