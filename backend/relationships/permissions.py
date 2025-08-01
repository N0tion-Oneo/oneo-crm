"""
Relationship permission management system
"""
from typing import List, Dict, Any, Optional, Set
from django.core.cache import cache
from django.contrib.auth import get_user_model
from authentication.permissions import AsyncPermissionManager
from .models import RelationshipType, Relationship, PermissionTraversal
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class RelationshipPermissionManager:
    """Manage relationship traversal permissions"""
    
    def __init__(self, user: User):
        self.user = user
        self.base_permission_manager = AsyncPermissionManager(user)
        self.cache_key_prefix = f"rel_perms:{user.id}"
    
    def can_traverse_relationship(
        self, 
        relationship_type: RelationshipType, 
        direction: str = 'forward'
    ) -> bool:
        """Check if user can traverse a specific relationship type"""
        cache_key = f"{self.cache_key_prefix}:traverse:{relationship_type.id}:{direction}"
        result = cache.get(cache_key)
        
        if result is None:
            result = self._calculate_traversal_permission(relationship_type, direction)
            cache.set(cache_key, result, 300)  # 5 minutes
        
        return result
    
    def _calculate_traversal_permission(
        self, 
        relationship_type: RelationshipType, 
        direction: str
    ) -> bool:
        """Calculate if user can traverse relationship in given direction"""
        # Basic permission check - user must be authenticated
        if not self.user.is_authenticated:
            return False
        
        # Get user type specific traversal settings
        try:
            traversal_config = PermissionTraversal.objects.get(
                user_type=self.user.user_type,
                relationship_type=relationship_type
            )
            
            if direction == 'forward':
                return traversal_config.can_traverse_forward
            else:
                return traversal_config.can_traverse_reverse
                
        except PermissionTraversal.DoesNotExist:
            # Default to allowing traversal if no specific config
            return True
    
    def get_max_traversal_depth(self, relationship_type: RelationshipType) -> int:
        """Get maximum traversal depth for user and relationship type"""
        cache_key = f"{self.cache_key_prefix}:max_depth:{relationship_type.id}"
        result = cache.get(cache_key)
        
        if result is None:
            try:
                traversal_config = PermissionTraversal.objects.get(
                    user_type=self.user.user_type,
                    relationship_type=relationship_type
                )
                result = traversal_config.max_depth
            except PermissionTraversal.DoesNotExist:
                result = 3  # Default max depth
            
            cache.set(cache_key, result, 300)
        
        return result
    
    def get_visible_fields_through_relationship(
        self, 
        relationship_type: RelationshipType,
        target_pipeline_id: int
    ) -> Dict[str, bool]:
        """Get field visibility when accessing records through relationships"""
        cache_key = f"{self.cache_key_prefix}:fields:{relationship_type.id}:{target_pipeline_id}"
        result = cache.get(cache_key)
        
        if result is None:
            result = self._calculate_field_visibility(relationship_type, target_pipeline_id)
            cache.set(cache_key, result, 300)
        
        return result
    
    def _calculate_field_visibility(
        self, 
        relationship_type: RelationshipType,
        target_pipeline_id: int
    ) -> Dict[str, bool]:
        """Calculate field visibility through relationship"""
        # Start with base pipeline permissions
        base_permissions = self.base_permission_manager.get_user_permissions()
        pipeline_perms = base_permissions.get('pipelines', {}).get(str(target_pipeline_id), {})
        base_field_perms = pipeline_perms.get('fields', {})
        
        # Apply relationship-specific restrictions
        try:
            traversal_config = PermissionTraversal.objects.get(
                user_type=self.user.user_type,
                relationship_type=relationship_type
            )
            
            # Start with visible fields from traversal config
            visible_fields = traversal_config.visible_fields.get(str(target_pipeline_id), {})
            restricted_fields = traversal_config.restricted_fields.get(str(target_pipeline_id), {})
            
            # Combine with base permissions (more restrictive wins)
            final_permissions = {}
            
            # If no specific config, use base permissions
            if not visible_fields and not restricted_fields:
                return base_field_perms
            
            # Apply restrictions
            for field_name, base_perm in base_field_perms.items():
                if field_name in restricted_fields:
                    final_permissions[field_name] = False
                elif field_name in visible_fields:
                    final_permissions[field_name] = visible_fields[field_name] and base_perm
                else:
                    final_permissions[field_name] = base_perm
            
            return final_permissions
            
        except PermissionTraversal.DoesNotExist:
            return base_field_perms
    
    def validate_relationship_path(
        self, 
        path: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate if user can traverse entire relationship path"""
        if not path:
            return {'valid': True, 'accessible_depth': 0}
        
        accessible_depth = 0
        
        for i, step in enumerate(path):
            relationship_type_id = step.get('relationship_type_id')
            direction = step.get('direction', 'forward')
            
            try:
                relationship_type = RelationshipType.objects.get(id=relationship_type_id)
            except RelationshipType.DoesNotExist:
                return {
                    'valid': False, 
                    'accessible_depth': accessible_depth,
                    'error': f'Invalid relationship type at step {i+1}'
                }
            
            # Check traversal permission
            if not self.can_traverse_relationship(relationship_type, direction):
                return {
                    'valid': False,
                    'accessible_depth': accessible_depth,
                    'error': f'No permission to traverse {relationship_type.name} {direction} at step {i+1}'
                }
            
            # Check depth limit
            max_depth = self.get_max_traversal_depth(relationship_type)
            if i >= max_depth:
                return {
                    'valid': False,
                    'accessible_depth': accessible_depth,
                    'error': f'Maximum traversal depth ({max_depth}) exceeded'
                }
            
            accessible_depth += 1
        
        return {'valid': True, 'accessible_depth': accessible_depth}
    
    def can_create_relationship(
        self,
        relationship_type: RelationshipType,
        source_pipeline_id: int,
        target_pipeline_id: int
    ) -> bool:
        """Check if user can create a specific relationship"""
        # Check base permission for relationship creation
        if not self.base_permission_manager.has_permission(
            'action', 'relationships', 'create'
        ):
            return False
        
        # Check if user has write access to both pipelines
        source_perm = self.base_permission_manager.has_permission(
            'pipeline', str(source_pipeline_id), 'write'
        )
        target_perm = self.base_permission_manager.has_permission(
            'pipeline', str(target_pipeline_id), 'write'
        )
        
        return source_perm and target_perm
    
    def can_delete_relationship(self, relationship: Relationship) -> bool:
        """Check if user can delete a specific relationship"""
        # Check base permission for relationship deletion
        if not self.base_permission_manager.has_permission(
            'action', 'relationships', 'delete'
        ):
            return False
        
        # Check if user created the relationship or has admin access
        if relationship.created_by == self.user:
            return True
        
        # Check if user has admin access to either pipeline
        source_admin = self.base_permission_manager.has_permission(
            'pipeline', str(relationship.source_pipeline_id), 'admin'
        )
        target_admin = self.base_permission_manager.has_permission(
            'pipeline', str(relationship.target_pipeline_id), 'admin'
        )
        
        return source_admin or target_admin
    
    def clear_cache(self):
        """Clear relationship permission cache for user"""
        # In production, this would use Redis SCAN to clear matching keys
        # For now, we'll rely on TTL expiration
        logger.info(f"Clearing relationship permission cache for user {self.user.id}")
        pass