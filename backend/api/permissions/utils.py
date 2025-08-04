"""
Permission utility functions
"""
from typing import Dict, List, Any, Optional
from authentication.permissions import SyncPermissionManager


def check_bulk_permissions(user, action: str, resource_type: str, resource_ids: List[str]) -> Dict[str, bool]:
    """Check permissions for multiple resources at once"""
    permission_manager = SyncPermissionManager(user)
    results = {}
    
    for resource_id in resource_ids:
        results[resource_id] = permission_manager.has_permission('action', resource_type, action, resource_id)
    
    return results


def get_accessible_resource_ids(user, resource_type: str, action: str, resource_ids: List[str]) -> List[str]:
    """Filter resource IDs to only those the user can access"""
    permission_results = check_bulk_permissions(user, action, resource_type, resource_ids)
    return [resource_id for resource_id, has_access in permission_results.items() if has_access]


def validate_resource_access(user, resource_type: str, resource_id: str, required_actions: List[str]) -> Dict[str, bool]:
    """Validate user has all required actions for a resource"""
    permission_manager = SyncPermissionManager(user)
    results = {}
    
    for action in required_actions:
        results[action] = permission_manager.has_permission('action', resource_type, action, resource_id)
    
    return results


def has_any_permission(user, resource_type: str, actions: List[str], resource_id: Optional[str] = None) -> bool:
    """Check if user has any of the specified permissions"""
    permission_manager = SyncPermissionManager(user)
    
    for action in actions:
        if permission_manager.has_permission('action', resource_type, action, resource_id):
            return True
    
    return False


def has_all_permissions(user, resource_type: str, actions: List[str], resource_id: Optional[str] = None) -> bool:
    """Check if user has all of the specified permissions"""
    permission_manager = SyncPermissionManager(user)
    
    for action in actions:
        if not permission_manager.has_permission('action', resource_type, action, resource_id):
            return False
    
    return True


def get_user_permission_summary(user) -> Dict[str, Any]:
    """Get a summary of user's permissions for debugging/admin purposes"""
    permission_manager = SyncPermissionManager(user)
    permissions = permission_manager.get_user_permissions()
    
    return {
        'user_id': user.id,
        'user_type': user.user_type.name,
        'permissions': permissions,
        'is_admin': user.user_type.name == 'Admin',
        'tenant': getattr(user, 'tenant', None)
    }