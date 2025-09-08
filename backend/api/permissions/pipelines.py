"""
Pipeline-specific permission classes
"""
from rest_framework import permissions
from authentication.permissions import SyncPermissionManager as PermissionManager


class PipelinePermission(permissions.BasePermission):
    """Pipeline-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general pipeline access"""
        if not request.user.is_authenticated:
            print(f"🚨 Permission denied: User not authenticated")
            return False
        
        permission_manager = PermissionManager(request.user)
        
        # Debug logging
        pipeline_pk = view.kwargs.get('pipeline_pk')
        
        if view.action == 'list':
            # Check if this is a field list or pipeline list
            if view.kwargs.get('pipeline_pk'):
                # Field list - requires pipeline ACCESS AND field read permission
                pipeline_id = view.kwargs.get('pipeline_pk')
                pipeline_access = permission_manager.has_pipeline_access(pipeline_id)
                field_access = permission_manager.has_permission('action', 'fields', 'read', pipeline_id)
                result = pipeline_access and field_access
                print(f"🔍 Field list permission check: pipeline_access={pipeline_access}, fields.read={field_access}, result={result}")
                return result
            else:
                # Pipeline list - requires pipeline read permission
                return permission_manager.has_permission('action', 'pipelines', 'read')
        elif view.action == 'create':
            # Check if this is field creation or pipeline creation
            if view.kwargs.get('pipeline_pk'):
                # Field creation - requires pipeline ACCESS (not update) AND field create permission
                pipeline_id = view.kwargs.get('pipeline_pk')
                pipeline_access = permission_manager.has_pipeline_access(pipeline_id)
                field_access = permission_manager.has_permission('action', 'fields', 'create', pipeline_id)
                result = pipeline_access and field_access
                print(f"🔍 Field create permission check: pipeline_access={pipeline_access}, fields.create={field_access}, result={result}")
                return result
            else:
                # Pipeline creation - requires pipeline create permission
                return permission_manager.has_permission('action', 'pipelines', 'create')
        elif view.action in ['retrieve', 'analytics', 'export']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'destroy':
            return True  # Object-level check in has_object_permission
        elif view.action == 'manage':
            return True  # Object-level check in has_object_permission for field management
        elif view.action == 'reorder':
            # Field reordering requires field update permission (detail=False action)
            pipeline_id = view.kwargs.get('pipeline_pk')
            if pipeline_id:
                pipeline_access = permission_manager.has_pipeline_access(pipeline_id)
                field_access = permission_manager.has_permission('action', 'fields', 'update', pipeline_id)
                return pipeline_access and field_access
            return False
        elif view.action in ['validate_migration', 'migrate_schema']:
            return True  # Object-level check in has_object_permission for field migration
        elif view.action in ['deleted', 'restore', 'bulk_restore']:
            # Field recovery requires field update permission
            # For detail=False actions (deleted, bulk_restore), we need to check here
            # For detail=True actions (restore), object-level check will be called
            if view.action in ['deleted', 'bulk_restore']:
                # Field recovery operations require specific field.recover permission
                pipeline_id = view.kwargs.get('pipeline_pk')
                if pipeline_id:
                    pipeline_access = permission_manager.has_pipeline_access(pipeline_id)
                    field_access = permission_manager.has_permission('action', 'fields', 'recover', pipeline_id)
                    return pipeline_access and field_access
                return False
            else:
                # restore action - object-level check will handle this
                return True
        elif view.action in ['internal_full', 'stage_internal', 'shared_record', 'public_filtered', 'stage_public']:
            # Form generation actions - require pipeline read access
            pipeline_id = view.kwargs.get('pipeline_pk')
            if pipeline_id:
                return permission_manager.has_permission('action', 'pipelines', 'read', pipeline_id)
            return permission_manager.has_permission('action', 'pipelines', 'read')
        elif view.action == 'submit_form':
            # Form submission - needs record create/update permission for the pipeline
            pipeline_id = view.kwargs.get('pipeline_pk')
            if pipeline_id:
                # Check if it's an update (has record_id) or create
                record_id = request.data.get('record_id') if hasattr(request, 'data') else None
                if record_id:
                    return permission_manager.has_permission('action', 'records', 'update', pipeline_id)
                else:
                    return permission_manager.has_permission('action', 'records', 'create', pipeline_id)
            return False
        elif view.action in ['assign_fields', 'ungroup_fields', 'reorder_groups']:
            # Field group management actions require field update permission
            pipeline_id = view.kwargs.get('pipeline_pk')
            if pipeline_id:
                pipeline_access = permission_manager.has_pipeline_access(pipeline_id)
                field_access = permission_manager.has_permission('action', 'fields', 'update', pipeline_id)
                return pipeline_access and field_access
            return False
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = PermissionManager(request.user)
        
        if view.action in ['assign_fields', 'ungroup_fields']:
            # Field group actions - check if user has field update permission for the pipeline
            if hasattr(obj, 'pipeline'):
                # This is a field group object
                pipeline_access = permission_manager.has_pipeline_access(str(obj.pipeline.id))
                field_access = permission_manager.has_permission('action', 'fields', 'update', str(obj.pipeline.id))
                return pipeline_access and field_access
            return False
        elif view.action in ['retrieve', 'analytics', 'export']:
            # Check if this is a field or pipeline object
            if hasattr(obj, 'pipeline'):
                # Field object - requires pipeline ACCESS AND field read permission
                pipeline_access = permission_manager.has_pipeline_access(str(obj.pipeline.id))
                field_access = permission_manager.has_permission('action', 'fields', 'read', str(obj.pipeline.id))
                return pipeline_access and field_access
            else:
                # Pipeline object - requires pipeline read permission
                return permission_manager.has_permission('action', 'pipelines', 'read', str(obj.id))
        elif view.action in ['update', 'partial_update']:
            # Check if this is a field or pipeline object
            if hasattr(obj, 'pipeline'):
                # Field object - requires pipeline ACCESS AND field update permission
                pipeline_access = permission_manager.has_pipeline_access(str(obj.pipeline.id))
                field_access = permission_manager.has_permission('action', 'fields', 'update', str(obj.pipeline.id))
                return pipeline_access and field_access
            else:
                # Pipeline object - requires pipeline update permission
                return permission_manager.has_permission('action', 'pipelines', 'update', str(obj.id))
        elif view.action == 'destroy':
            # Check if this is a field or pipeline object
            if hasattr(obj, 'pipeline'):
                # Field object - requires pipeline ACCESS AND field delete permission
                pipeline_access = permission_manager.has_pipeline_access(str(obj.pipeline.id))
                field_access = permission_manager.has_permission('action', 'fields', 'delete', str(obj.pipeline.id))
                return pipeline_access and field_access
            else:
                # Pipeline object - requires pipeline delete permission
                return permission_manager.has_permission('action', 'pipelines', 'delete', str(obj.id))
        elif view.action == 'manage':
            # Field management (soft delete/restore) operations require update permission
            if hasattr(obj, 'pipeline'):
                # This is a field object - field management requires update permission
                pipeline_access = permission_manager.has_pipeline_access(str(obj.pipeline.id))
                field_access = permission_manager.has_permission('action', 'fields', 'update', str(obj.pipeline.id))
                return pipeline_access and field_access
            else:
                # This is a pipeline object (shouldn't happen for field management)
                return permission_manager.has_permission('action', 'fields', 'update', str(obj.id))
        elif view.action == 'reorder':
            # Field reordering requires field update permission
            pipeline_id = view.kwargs.get('pipeline_pk')
            if pipeline_id:
                pipeline_access = permission_manager.has_pipeline_access(pipeline_id)
                field_access = permission_manager.has_permission('action', 'fields', 'update', pipeline_id)
                return pipeline_access and field_access
            return False
        elif view.action in ['validate_migration', 'migrate_schema']:
            # Field migration requires specific field.migrate permission
            if hasattr(obj, 'pipeline'):
                # This is a field object
                pipeline_access = permission_manager.has_pipeline_access(str(obj.pipeline.id))
                field_access = permission_manager.has_permission('action', 'fields', 'migrate', str(obj.pipeline.id))
                return pipeline_access and field_access
            else:
                # This is a pipeline object (shouldn't happen for field actions, but safe fallback)
                pipeline_access = permission_manager.has_pipeline_access(str(obj.id))
                field_access = permission_manager.has_permission('action', 'fields', 'migrate', str(obj.id))
                return pipeline_access and field_access
        elif view.action in ['deleted', 'restore', 'bulk_restore']:
            # Field recovery operations require specific field.recover permission
            pipeline_id = view.kwargs.get('pipeline_pk')
            if pipeline_id:
                pipeline_access = permission_manager.has_pipeline_access(pipeline_id)
                field_access = permission_manager.has_permission('action', 'fields', 'recover', pipeline_id)
                return pipeline_access and field_access
            elif hasattr(obj, 'pipeline'):
                # This is a field object
                pipeline_access = permission_manager.has_pipeline_access(str(obj.pipeline.id))
                field_access = permission_manager.has_permission('action', 'fields', 'recover', str(obj.pipeline.id))
                return pipeline_access and field_access
            else:
                # This is a pipeline object
                pipeline_access = permission_manager.has_pipeline_access(str(obj.id))
                field_access = permission_manager.has_permission('action', 'fields', 'recover', str(obj.id))
                return pipeline_access and field_access
        
        return False


class RecordPermission(permissions.BasePermission):
    """Record-specific permissions"""
    
    def has_permission(self, request, view):
        """Check if user has general record access"""
        if not request.user.is_authenticated:
            return False
        
        permission_manager = PermissionManager(request.user)
        pipeline_id = view.kwargs.get('pipeline_pk') or request.data.get('pipeline_id')
        
        if view.action == 'list':
            if pipeline_id:
                # Check pipeline access first, then record permission
                has_access = permission_manager.has_pipeline_access(pipeline_id)
                has_record_perm = permission_manager.has_permission('action', 'records', 'read', pipeline_id)
                return has_access and has_record_perm
            return permission_manager.has_permission('action', 'records', 'read')
        elif view.action == 'create':
            if pipeline_id:
                # Check pipeline access first, then record permission
                has_access = permission_manager.has_pipeline_access(pipeline_id)
                has_record_perm = permission_manager.has_permission('action', 'records', 'create', pipeline_id)
                return has_access and has_record_perm
            return False
        elif view.action in ['retrieve', 'relationships', 'history']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['update', 'partial_update']:
            return True  # Object-level check in has_object_permission
        elif view.action in ['destroy', 'soft_delete', 'restore']:
            return True  # Object-level check in has_object_permission
        elif view.action == 'deleted':
            # List deleted records - requires read permission for the pipeline
            if pipeline_id:
                has_access = permission_manager.has_pipeline_access(pipeline_id)
                has_record_perm = permission_manager.has_permission('action', 'records', 'read', pipeline_id)
                return has_access and has_record_perm
            return permission_manager.has_permission('action', 'records', 'read')
        elif view.action == 'bulk_create':
            # Bulk create requires create permission for the pipeline
            if pipeline_id:
                has_access = permission_manager.has_pipeline_access(pipeline_id)
                has_record_perm = permission_manager.has_permission('action', 'records', 'create', pipeline_id)
                return has_access and has_record_perm
            return False
        elif view.action == 'bulk_update':
            # Bulk update requires update permission for the pipeline
            if pipeline_id:
                has_access = permission_manager.has_pipeline_access(pipeline_id)
                has_record_perm = permission_manager.has_permission('action', 'records', 'update', pipeline_id)
                return has_access and has_record_perm
            return False
        elif view.action == 'validate':
            # Record validation requires read permission for the pipeline
            if pipeline_id:
                has_access = permission_manager.has_pipeline_access(pipeline_id)
                has_record_perm = permission_manager.has_permission('action', 'records', 'read', pipeline_id)
                return has_access and has_record_perm
            return False
        elif view.action in ['generate_share_link', 'preview_shared_form']:
            # Share link generation requires read permission for the pipeline
            # Users can share records they can read
            return True  # Object-level check in has_object_permission
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        permission_manager = PermissionManager(request.user)
        pipeline_id = str(obj.pipeline_id)
        
        # First check if user has access to the pipeline at all
        if not permission_manager.has_pipeline_access(pipeline_id):
            return False
        
        if view.action in ['retrieve', 'relationships', 'history']:
            return permission_manager.has_permission('action', 'records', 'read', pipeline_id)
        elif view.action in ['update', 'partial_update']:
            return permission_manager.has_permission('action', 'records', 'update', pipeline_id)
        elif view.action in ['destroy', 'soft_delete']:
            return permission_manager.has_permission('action', 'records', 'delete', pipeline_id)
        elif view.action == 'restore':
            # Restore requires delete permission (ability to manage deleted records)
            return permission_manager.has_permission('action', 'records', 'delete', pipeline_id)
        elif view.action in ['generate_share_link', 'preview_shared_form']:
            # Share link generation requires read permission for the record's pipeline
            return permission_manager.has_permission('action', 'records', 'read', pipeline_id)
        
        return False