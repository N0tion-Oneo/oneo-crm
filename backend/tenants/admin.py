from django.contrib import admin
from .models import Tenant, Domain


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'schema_name', 'created_on', 'max_users']
    list_filter = ['created_on']
    search_fields = ['name', 'schema_name']
    readonly_fields = ['schema_name', 'created_on']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'schema_name', 'created_on')
        }),
        ('Configuration', {
            'fields': ('max_users', 'features_enabled', 'billing_settings')
        }),
    )


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain', 'tenant__name']
