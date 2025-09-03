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
        """Create system default user types asynchronously with comprehensive permissions"""
        defaults = [
            {
                'name': 'Admin',
                'slug': 'admin',
                'description': 'Full access to all tenant features and system administration',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'system': ['full_access'],
                    'users': ['create', 'read', 'update', 'delete', 'impersonate', 'assign_roles'],
                    'user_types': ['create', 'read', 'update', 'delete'],
                    'pipelines': ['access', 'create', 'read', 'update', 'delete', 'clone', 'export', 'import'],
                    'records': ['create', 'read', 'update', 'delete', 'export', 'import'],
                    'fields': ['create', 'read', 'update', 'delete', 'recover', 'migrate'],
                    'relationships': ['create', 'read', 'update', 'delete', 'traverse'],
                    'workflows': ['create', 'read', 'update', 'delete', 'execute', 'clone', 'export'],
                    'business_rules': ['create', 'read', 'update', 'delete'],
                    'communications': ['create', 'read', 'update', 'delete', 'send'],
                    'settings': ['read', 'update'],
                    'monitoring': ['read', 'update'],
                    'ai_features': ['create', 'read', 'update', 'delete', 'configure'],
                    'reports': ['create', 'read', 'update', 'delete', 'export'],
                    'api_access': ['full_access'],
                    'duplicates': ['create', 'read', 'update', 'delete', 'resolve', 'detect'],
                    'filters': ['create_filters', 'edit_filters', 'delete_filters'],
                    'sharing': ['create_shared_views', 'create_shared_forms', 'configure_shared_views_forms', 'revoke_shared_views_forms'],
                    'permissions': ['read', 'update'],
                    'staff_profiles': ['create', 'read', 'update', 'delete', 'read_all', 'update_all', 'read_sensitive', 'update_sensitive']
                }
            },
            {
                'name': 'Manager',
                'slug': 'manager',
                'description': 'Management access with user oversight and advanced features',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'users': ['create', 'read', 'update', 'assign_roles'],
                    'user_types': ['read'],
                    'pipelines': ['access', 'create', 'read', 'update', 'clone', 'export'],
                    'records': ['create', 'read', 'update', 'export'],
                    'fields': ['create', 'read', 'update', 'recover'],
                    'relationships': ['create', 'read', 'update', 'traverse'],
                    'workflows': ['create', 'read', 'update', 'execute', 'clone', 'export'],
                    'business_rules': ['create', 'read', 'update'],
                    'communications': ['create', 'read', 'update', 'send'],
                    'settings': ['read'],
                    'monitoring': ['read'],
                    'ai_features': ['create', 'read', 'update', 'configure'],
                    'reports': ['create', 'read', 'update', 'export'],
                    'api_access': ['read', 'write'],
                    'duplicates': ['create', 'read', 'update', 'resolve', 'detect'],
                    'filters': ['create_filters', 'edit_filters', 'delete_filters'],
                    'sharing': ['create_shared_views', 'create_shared_forms', 'configure_shared_views_forms', 'revoke_shared_views_forms'],
                    'permissions': ['read', 'update'],
                    'staff_profiles': ['read', 'update', 'read_all']
                }
            },
            {
                'name': 'User',
                'slug': 'user',
                'description': 'Standard user access with record management capabilities',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'users': ['read'],
                    'user_types': ['read'],
                    'pipelines': ['access', 'read', 'update'],
                    'records': ['create', 'read', 'update', 'export'],
                    'fields': ['read', 'update'],
                    'relationships': ['create', 'read', 'update', 'traverse'],
                    'workflows': ['read', 'execute'],
                    'business_rules': ['read'],
                    'communications': ['create', 'read', 'update'],
                    'settings': ['read'],
                    'ai_features': ['read', 'update'],
                    'reports': ['read', 'export'],
                    'api_access': ['read', 'write'],
                    'duplicates': ['read', 'detect'],
                    'filters': ['create_filters', 'edit_filters'],
                    'sharing': ['create_shared_views', 'create_shared_forms'],
                    'permissions': ['read'],
                    'staff_profiles': ['read', 'update']
                }
            },
            {
                'name': 'Viewer',
                'slug': 'viewer',
                'description': 'Read-only access with limited interaction capabilities',
                'is_system_default': True,
                'is_custom': False,
                'base_permissions': {
                    'users': ['read'],
                    'user_types': ['read'],
                    'pipelines': ['access', 'read'],
                    'records': ['read', 'export'],
                    'fields': ['read'],
                    'relationships': ['read'],
                    'workflows': ['read'],
                    'business_rules': ['read'],
                    'communications': ['read'],
                    'settings': ['read'],
                    'ai_features': ['read'],
                    'reports': ['read', 'export'],
                    'api_access': ['read'],
                    'duplicates': ['read'],
                    'filters': [],  # Viewers cannot create or edit filters
                    'sharing': [],  # Viewers cannot create shares
                    'permissions': ['read'],
                    'staff_profiles': ['read']
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


class UserTypePipelinePermission(models.Model):
    """Pipeline-specific permissions for user types"""
    
    user_type = models.ForeignKey(
        UserType,
        on_delete=models.CASCADE,
        related_name='pipeline_permissions'
    )
    pipeline_id = models.IntegerField()  # Reference to Pipeline model (from pipelines app)
    
    # Permissions for this pipeline
    permissions = models.JSONField(default=list)  # e.g., ['read', 'create', 'update', 'delete']
    
    # Access level
    ACCESS_LEVELS = [
        ('none', 'No Access'),
        ('read', 'Read Only'),
        ('write', 'Read & Write'),
        ('admin', 'Full Admin'),
    ]
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='read')
    
    # Restrictions
    can_view_all_records = models.BooleanField(default=True)
    can_edit_all_records = models.BooleanField(default=False)
    can_delete_records = models.BooleanField(default=False)
    can_export_data = models.BooleanField(default=True)
    can_import_data = models.BooleanField(default=False)
    
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_pipeline_permissions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auth_usertypepipelinepermission'
        unique_together = ['user_type', 'pipeline_id']
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['pipeline_id']),
            models.Index(fields=['access_level']),
        ]
    
    def __str__(self):
        return f"{self.user_type.name} - Pipeline {self.pipeline_id} ({self.access_level})"


class UserTypeFieldPermission(models.Model):
    """Field-level permissions for user types"""
    
    user_type = models.ForeignKey(
        UserType,
        on_delete=models.CASCADE,
        related_name='field_permissions'
    )
    pipeline_id = models.IntegerField()  # Reference to Pipeline model
    field_id = models.IntegerField()  # Reference to Field model (from pipelines app)
    
    # Field permissions
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
    can_require = models.BooleanField(default=False)  # Can make field required/optional
    
    # Field visibility
    VISIBILITY_LEVELS = [
        ('visible', 'Always Visible'),
        ('hidden', 'Always Hidden'),
        ('conditional', 'Conditional Visibility'),
        ('readonly', 'Read Only'),
    ]
    visibility = models.CharField(max_length=20, choices=VISIBILITY_LEVELS, default='visible')
    
    # Conditional visibility rules (JSON)
    visibility_conditions = models.JSONField(default=dict)
    
    # Default values and constraints
    default_value = models.JSONField(null=True, blank=True)
    value_constraints = models.JSONField(default=dict)  # Min/max, regex, etc.
    
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_field_permissions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auth_usertypefieldpermission'
        unique_together = ['user_type', 'pipeline_id', 'field_id']
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['pipeline_id']),
            models.Index(fields=['field_id']),
            models.Index(fields=['visibility']),
        ]
    
    def __str__(self):
        return f"{self.user_type.name} - Pipeline {self.pipeline_id} Field {self.field_id} ({self.visibility})"


class UserPipelinePermissionOverride(models.Model):
    """Individual user overrides for pipeline permissions"""
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='pipeline_permission_overrides'
    )
    pipeline_id = models.IntegerField()
    
    # Override permissions
    permissions = models.JSONField(default=list)
    access_level = models.CharField(max_length=20, default='read')
    
    # Override flags
    can_view_all_records = models.BooleanField(default=True)
    can_edit_all_records = models.BooleanField(default=False)
    can_delete_records = models.BooleanField(default=False)
    can_export_data = models.BooleanField(default=True)
    can_import_data = models.BooleanField(default=False)
    
    # Metadata
    granted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_pipeline_overrides'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'auth_userpipelinepermissionoverride'
        unique_together = ['user', 'pipeline_id']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['pipeline_id']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - Pipeline {self.pipeline_id} Override ({self.access_level})"
    
    def is_expired(self):
        """Check if override is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class StaffProfile(models.Model):
    """
    Extended staff profile for users with comprehensive professional and personal information.
    Designed to avoid duplicating fields already in CustomUser model.
    """
    
    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contractor', 'Contractor'),
        ('intern', 'Intern'),
        ('consultant', 'Consultant'),
    ]
    
    EMPLOYMENT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
        ('resigned', 'Resigned'),
    ]
    
    WORK_LOCATION_CHOICES = [
        ('office', 'Office'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ]
    
    # One-to-one relationship with user
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    
    # Professional Information
    employee_id = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Unique employee identifier"
    )
    job_title = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True)
    employment_type = models.CharField(
        max_length=20, 
        choices=EMPLOYMENT_TYPE_CHOICES,
        default='full_time'
    )
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        default='active'
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    # Work Details
    work_location = models.CharField(
        max_length=20,
        choices=WORK_LOCATION_CHOICES,
        default='office'
    )
    office_location = models.CharField(max_length=255, blank=True)
    work_phone_extension = models.CharField(max_length=20, blank=True)
    reporting_manager = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports'
    )
    
    # Professional Details
    certifications = models.JSONField(
        default=list,
        help_text="Array of professional certifications"
    )
    education = models.JSONField(
        default=dict,
        help_text="Education details including degrees, institutions, and years"
    )
    bio = models.TextField(
        blank=True,
        help_text="Professional biography or summary"
    )
    linkedin_profile = models.URLField(
        max_length=500,
        blank=True,
        help_text="LinkedIn profile URL"
    )
    professional_links = models.JSONField(
        default=dict,
        help_text="Other professional profile links (GitHub, portfolio, etc.)"
    )
    
    # Emergency & Personal Information
    emergency_contact_name = models.CharField(max_length=255, blank=True)
    emergency_contact_phone = models.CharField(max_length=50, blank=True)
    emergency_contact_relationship = models.CharField(max_length=100, blank=True)
    
    # Sensitive personal information (consider encryption in production)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    personal_email = models.EmailField(blank=True)
    home_address = models.JSONField(
        default=dict,
        help_text="Home address details"
    )
    
    # Administrative
    internal_notes = models.TextField(
        blank=True,
        help_text="Internal HR notes (permission-restricted)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_staff_profiles'
    )
    
    class Meta:
        db_table = 'auth_staffprofile'
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['department']),
            models.Index(fields=['reporting_manager']),
            models.Index(fields=['employment_status']),
        ]
        ordering = ['employee_id']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.job_title} ({self.employee_id})"
    
    @property
    def is_manager(self):
        """Check if this staff member is a manager"""
        return self.direct_reports.exists()
    
    @property
    def full_name(self):
        """Get full name from associated user"""
        return self.user.get_full_name()
    
    @property
    def email(self):
        """Get work email from associated user"""
        return self.user.email
    
    def get_direct_reports(self):
        """Get all direct reports"""
        return StaffProfile.objects.filter(reporting_manager=self.user)
    
    def get_reporting_chain(self):
        """Get the reporting chain up to the top"""
        chain = []
        current = self.reporting_manager
        while current:
            try:
                profile = current.staff_profile
                chain.append(profile)
                current = profile.reporting_manager
            except StaffProfile.DoesNotExist:
                break
        return chain
