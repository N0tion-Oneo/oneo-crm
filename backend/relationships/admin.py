from django.contrib import admin
from django.utils.html import format_html
from .models import RelationshipType, Relationship, PermissionTraversal, RelationshipPath


@admin.register(RelationshipType)
class RelationshipTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'slug', 'cardinality', 'is_bidirectional', 
        'source_pipeline', 'target_pipeline', 'is_system', 'created_at'
    ]
    list_filter = ['cardinality', 'is_bidirectional', 'is_system', 'created_at']
    search_fields = ['name', 'slug', 'description']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        ('Configuration', {
            'fields': ('cardinality', 'is_bidirectional', 'source_pipeline', 'target_pipeline')
        }),
        ('Labels', {
            'fields': ('forward_label', 'reverse_label')
        }),
        ('Permissions', {
            'fields': ('requires_permission', 'permission_config')
        }),
        ('Behavior', {
            'fields': ('cascade_delete', 'allow_self_reference', 'allow_user_relationships', 'is_system')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.is_system:
            readonly.extend(['name', 'cardinality', 'is_bidirectional'])
        return readonly


@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    list_display = [
        'get_relationship_display', 'relationship_type', 'get_relationship_kind',
        'status', 'strength', 'is_verified', 'created_by', 'created_at'
    ]
    list_filter = ['relationship_type', 'status', 'is_verified', 'is_deleted', 'role', 'created_at']
    search_fields = ['source_pipeline__name', 'target_pipeline__name', 'user__email', 'metadata']
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']
    
    fieldsets = (
        (None, {
            'fields': ('relationship_type',)
        }),
        ('User Assignment (Optional)', {
            'fields': ('user', 'role', 'can_edit', 'can_delete'),
            'description': 'For user-to-record assignments. Leave user blank for record-to-record relationships.'
        }),
        ('Source Record (Optional for User Assignments)', {
            'fields': ('source_pipeline', 'source_record_id'),
            'description': 'Leave blank when user is specified'
        }),
        ('Target Record', {
            'fields': ('target_pipeline', 'target_record_id')
        }),
        ('Relationship Data', {
            'fields': ('metadata', 'strength', 'status', 'is_verified')
        }),
        ('Lifecycle', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
        ('Soft Delete', {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_relationship_display(self, obj):
        if obj.user:
            return format_html(
                '<strong>{}</strong> → <strong>{}:{}</strong>',
                obj.user.email,
                obj.target_pipeline.name,
                obj.target_record_id
            )
        else:
            return format_html(
                '<strong>{}:{}</strong> → <strong>{}:{}</strong>',
                obj.source_pipeline.name if obj.source_pipeline else 'N/A',
                obj.source_record_id or 'N/A',
                obj.target_pipeline.name,
                obj.target_record_id
            )
    get_relationship_display.short_description = 'Relationship'
    
    def get_relationship_kind(self, obj):
        if obj.user:
            color = 'blue'
            kind = f'User Assignment ({obj.role})'
        else:
            color = 'green'
            kind = 'Record-to-Record'
        return format_html(
            '<span style="color: {};">{}</span>',
            color, kind
        )
    get_relationship_kind.short_description = 'Kind'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'relationship_type', 'source_pipeline', 'target_pipeline',
            'user', 'created_by', 'deleted_by'
        )


@admin.register(PermissionTraversal)
class PermissionTraversalAdmin(admin.ModelAdmin):
    list_display = [
        'user_type', 'relationship_type', 'can_traverse_forward', 
        'can_traverse_reverse', 'max_depth', 'created_at'
    ]
    list_filter = ['can_traverse_forward', 'can_traverse_reverse', 'max_depth', 'created_at']
    search_fields = ['user_type__name', 'relationship_type__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('user_type', 'relationship_type')
        }),
        ('Traversal Permissions', {
            'fields': ('can_traverse_forward', 'can_traverse_reverse', 'max_depth')
        }),
        ('Field Visibility', {
            'fields': ('visible_fields', 'restricted_fields'),
            'description': 'Configure which fields are visible/restricted when accessing records through this relationship'
        }),
        ('Advanced', {
            'fields': ('traversal_conditions',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(RelationshipPath)
class RelationshipPathAdmin(admin.ModelAdmin):
    list_display = [
        'get_path_display', 'path_length', 'path_strength', 
        'computed_at', 'expires_at', 'is_expired_display'
    ]
    list_filter = ['path_length', 'computed_at', 'expires_at']
    search_fields = ['source_pipeline__name', 'target_pipeline__name']
    readonly_fields = ['computed_at', 'is_expired_display']
    
    def get_path_display(self, obj):
        return format_html(
            '<strong>{}:{}</strong> → <strong>{}:{}</strong>',
            obj.source_pipeline.name,
            obj.source_record_id,
            obj.target_pipeline.name,
            obj.target_record_id
        )
    get_path_display.short_description = 'Path'
    
    def is_expired_display(self, obj):
        expired = obj.is_expired()
        color = 'red' if expired else 'green'
        status = 'Expired' if expired else 'Valid'
        return format_html(
            '<span style="color: {};">{}</span>',
            color, status
        )
    is_expired_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'source_pipeline', 'target_pipeline'
        )
