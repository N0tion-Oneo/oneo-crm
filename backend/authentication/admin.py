from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.html import format_html
from .models import CustomUser, UserType, UserSession, ExtendedPermission, UserTypePermission, StaffProfile


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'user_type')


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = '__all__'


class StaffProfileInline(admin.StackedInline):
    """Inline admin for StaffProfile in CustomUser admin"""
    model = StaffProfile
    fk_name = 'user'  # Specify which ForeignKey to use (not reporting_manager)
    extra = 0
    fields = (
        'employee_id', 'job_title', 'department',
        'employment_type', 'employment_status', 'start_date', 'end_date',
        'work_location', 'office_location', 'work_phone_extension',
        'reporting_manager', 'bio', 'linkedin_profile'
    )
    verbose_name = 'Staff Profile'
    verbose_name_plural = 'Staff Profile'
    can_delete = False


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    inlines = [StaffProfileInline]  # Add inline for staff profile
    
    list_display = (
        'username', 'email', 'user_type', 'is_active', 
        'last_activity', 'created_at'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'user_type', 
        'created_at', 'last_activity'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': (
                'first_name', 'last_name', 'email', 'phone', 
                'timezone', 'language', 'avatar_url'
            )
        }),
        ('User Type & Permissions', {
            'fields': ('user_type', 'permission_overrides')
        }),
        ('Status & Timestamps', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'last_login', 'last_activity', 'date_joined'
            )
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'user_type', 
                'password1', 'password2'
            ),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined')


@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'slug', 'is_system_default', 'is_custom', 
        'user_count', 'created_at'
    )
    list_filter = ('is_system_default', 'is_custom', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-is_system_default', 'name')
    
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description')}),
        ('Configuration', {
            'fields': (
                'is_system_default', 'is_custom',
                'base_permissions', 'dashboard_config', 'menu_permissions'
            )
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def user_count(self, obj):
        count = obj.customuser_set.count()
        return format_html(
            '<span style="color: {};">{}</span>',
            '#28a745' if count > 0 else '#6c757d',
            count
        )
    user_count.short_description = 'Users'


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'session_key_short', 'ip_address', 
        'last_activity', 'expires_at', 'is_expired'
    )
    list_filter = ('created_at', 'last_activity', 'expires_at')
    search_fields = ('user__username', 'user__email', 'ip_address', 'session_key')
    ordering = ('-last_activity',)
    
    fieldsets = (
        (None, {
            'fields': ('user', 'session_key', 'ip_address')
        }),
        ('Device & Browser', {
            'fields': ('user_agent', 'device_info')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_activity', 'expires_at')
        }),
    )
    
    readonly_fields = ('created_at', 'last_activity')
    
    def session_key_short(self, obj):
        return f"{obj.session_key[:8]}..." if obj.session_key else ""
    session_key_short.short_description = 'Session Key'
    
    def is_expired(self, obj):
        from django.utils import timezone
        expired = obj.expires_at < timezone.now()
        return format_html(
            '<span style="color: {};">{}</span>',
            '#dc3545' if expired else '#28a745',
            'Expired' if expired else 'Active'
        )
    is_expired.short_description = 'Status'


@admin.register(ExtendedPermission)
class ExtendedPermissionAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'codename', 'permission_type', 
        'resource_type', 'resource_id', 'is_system'
    )
    list_filter = ('permission_type', 'resource_type', 'is_system')
    search_fields = ('name', 'codename', 'description')
    ordering = ('permission_type', 'resource_type', 'name')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'codename', 'description')
        }),
        ('Permission Configuration', {
            'fields': (
                'permission_type', 'resource_type', 'resource_id',
                'content_type', 'is_system'
            )
        }),
    )


@admin.register(UserTypePermission)
class UserTypePermissionAdmin(admin.ModelAdmin):
    list_display = (
        'user_type', 'permission', 'is_granted', 
        'traversal_depth', 'created_at'
    )
    list_filter = ('is_granted', 'traversal_depth', 'created_at')
    search_fields = (
        'user_type__name', 'permission__name', 
        'permission__codename'
    )
    ordering = ('user_type', 'permission')
    
    fieldsets = (
        (None, {
            'fields': ('user_type', 'permission', 'is_granted')
        }),
        ('Advanced Configuration', {
            'fields': (
                'conditions', 'traversal_depth', 'field_restrictions'
            ),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at',)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    """Admin for StaffProfile model with comprehensive management"""
    
    list_display = (
        'employee_id', 'get_user_name', 'get_user_email', 'job_title', 
        'department', 'employment_status', 'reporting_manager', 'start_date'
    )
    list_filter = (
        'employment_status', 'employment_type', 'work_location', 
        'department', 'start_date'
    )
    search_fields = (
        'employee_id', 'user__email', 'user__first_name', 
        'user__last_name', 'job_title', 'department'
    )
    ordering = ('employee_id',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',),
        }),
        ('Professional Information', {
            'fields': (
                'employee_id', 'job_title', 'department',
                'employment_type', 'employment_status',
                'start_date', 'end_date'
            )
        }),
        ('Work Details', {
            'fields': (
                'work_location', 'office_location', 
                'work_phone_extension', 'reporting_manager'
            )
        }),
        ('Professional Details', {
            'fields': (
                'certifications', 'languages_spoken', 'education',
                'bio', 'linkedin_profile', 'professional_links'
            ),
            'classes': ('collapse',)
        }),
        ('Emergency & Personal Information', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_phone',
                'emergency_contact_relationship', 'date_of_birth',
                'nationality', 'personal_email', 'home_address'
            ),
            'classes': ('collapse',)
        }),
        ('Administrative', {
            'fields': ('internal_notes', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'reporting_manager', 'created_by')
    
    def get_user_name(self, obj):
        return obj.user.get_full_name()
    get_user_name.short_description = 'Name'
    get_user_name.admin_order_field = 'user__first_name'
    
    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'Email'
    get_user_email.admin_order_field = 'user__email'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating a new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
