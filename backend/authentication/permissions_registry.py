"""
Global Permission Schema Registry for Multi-Tenant System

This module defines the universal permission schema available to all tenants.
Lives in SHARED_APPS so all tenants use the same permission categories and actions.

Architecture:
- Permission Schema: Global (defined here)
- Permission Assignments: Tenant-specific (UserType instances in tenant schemas)
"""

from typing import Dict, List, Any
from django.utils import timezone


# Global permission schema available to all tenants
PERMISSION_CATEGORIES = {
    'system': {
        'actions': ['full_access'],
        'description': 'System-wide administrative access and platform management',
        'category_display': 'System Administration'
    },
    'users': {
        'actions': ['create', 'read', 'update', 'delete', 'impersonate', 'assign_roles'],
        'description': 'User account management and role assignment',
        'category_display': 'User Management'
    },
    'user_types': {
        'actions': ['create', 'read', 'update', 'delete'],
        'description': 'User type and role management',
        'category_display': 'User Type Management'
    },
    'pipelines': {
        'actions': ['access', 'create', 'read', 'update', 'delete', 'clone', 'export', 'import'],
        'description': 'Pipeline management and configuration',
        'category_display': 'Pipeline Management'
    },
    'records': {
        'actions': ['create', 'read', 'update', 'delete', 'bulk_edit', 'export', 'import'],
        'description': 'Record data management and operations',
        'category_display': 'Record Management'
    },
    'fields': {
        'actions': ['create', 'read', 'update', 'delete', 'configure'],
        'description': 'Field definition and configuration management',
        'category_display': 'Field Management'
    },
    'relationships': {
        'actions': ['create', 'read', 'update', 'delete', 'traverse'],
        'description': 'Relationship management and traversal',
        'category_display': 'Relationship Management'
    },
    'workflows': {
        'actions': ['create', 'read', 'update', 'delete', 'execute'],
        'description': 'Workflow automation and execution',
        'category_display': 'Workflow Management'
    },
    'business_rules': {
        'actions': ['create', 'read', 'update', 'delete'],
        'description': 'Business rules configuration and management',
        'category_display': 'Business Rules'
    },
    'communications': {
        'actions': ['create', 'read', 'update', 'delete', 'send'],
        'description': 'Communication management and messaging',
        'category_display': 'Communication Management'
    },
    'settings': {
        'actions': ['read', 'update'],
        'description': 'System and tenant settings management',
        'category_display': 'Settings'
    },
    'monitoring': {
        'actions': ['read', 'update'],
        'description': 'System monitoring and analytics',
        'category_display': 'System Monitoring'
    },
    'ai_features': {
        'actions': ['create', 'read', 'update', 'delete', 'configure'],
        'description': 'AI features and configuration management',
        'category_display': 'AI Features'
    },
    'reports': {
        'actions': ['create', 'read', 'update', 'delete', 'export'],
        'description': 'Report generation and management',
        'category_display': 'Reports & Analytics'
    },
    'api_access': {
        'actions': ['read', 'write', 'full_access'],
        'description': 'API access control and management',
        'category_display': 'API Access'
    }
}

# Action descriptions for UI display
ACTION_DESCRIPTIONS = {
    'create': 'Create new items',
    'read': 'View and access items',
    'update': 'Modify existing items',
    'delete': 'Remove items permanently',
    'clone': 'Duplicate existing items',
    'export': 'Export data to external formats',
    'import': 'Import data from external sources',
    'execute': 'Run processes and operations',
    'configure': 'Modify configuration settings',
    'send': 'Send messages and communications',
    'traverse': 'Navigate through relationships',
    'bulk_edit': 'Perform bulk operations',
    'impersonate': 'Act on behalf of other users',
    'assign_roles': 'Assign roles to users',
    'access': 'Basic access to resources',
    'full_access': 'Complete administrative access',
    'write': 'Create and modify content'
}


def get_permission_schema() -> Dict[str, List[str]]:
    """
    Return the complete permission schema for all tenants.
    
    Returns:
        Dict mapping category names to lists of available actions
    """
    return {
        category: data['actions'] 
        for category, data in PERMISSION_CATEGORIES.items()
    }


def get_permission_categories_with_metadata() -> Dict[str, Any]:
    """
    Return permission categories with full metadata for UI display.
    
    Returns:
        Dict containing categories with descriptions and display names
    """
    return PERMISSION_CATEGORIES.copy()


def get_action_description(action: str) -> str:
    """
    Get user-friendly description for a permission action.
    
    Args:
        action: The permission action name
        
    Returns:
        Human-readable description of the action
    """
    return ACTION_DESCRIPTIONS.get(action, f'{action.replace("_", " ").title()} operation')


def validate_permissions(permissions_dict: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Validate user type permissions against the global schema.
    
    Args:
        permissions_dict: Dictionary of category -> actions to validate
        
    Returns:
        Dict containing validation results with errors and warnings
    """
    errors = []
    warnings = []
    valid_permissions = {}
    schema = get_permission_schema()
    
    for category, actions in permissions_dict.items():
        if category not in schema:
            errors.append(f"Unknown permission category: '{category}'")
            continue
            
        valid_actions = []
        for action in actions:
            if action not in schema[category]:
                warnings.append(f"Unknown action '{action}' in category '{category}'")
            else:
                valid_actions.append(action)
        
        if valid_actions:
            valid_permissions[category] = valid_actions
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'validated_permissions': valid_permissions
    }


def get_default_permissions_for_role(role_level: str) -> Dict[str, List[str]]:
    """
    Get default permission set for different role levels.
    
    Args:
        role_level: 'admin', 'manager', 'user', or 'viewer'
        
    Returns:
        Dict of appropriate permissions for the role level
    """
    schema = get_permission_schema()
    
    if role_level == 'admin':
        # Admin gets all permissions
        return schema.copy()
    
    elif role_level == 'manager':
        # Manager gets most permissions except system and delete operations
        return {
            'users': ['create', 'read', 'update', 'assign_roles'],
            'user_types': ['read'],
            'pipelines': ['create', 'read', 'update', 'clone', 'export'],
            'records': ['create', 'read', 'update', 'bulk_edit', 'export'],
            'fields': ['create', 'read', 'update', 'configure'],
            'relationships': ['create', 'read', 'update', 'traverse'],
            'workflows': ['create', 'read', 'update', 'execute'],
            'business_rules': ['create', 'read', 'update'],
            'communications': ['create', 'read', 'update', 'send'],
            'settings': ['read'],
            'monitoring': ['read'],
            'ai_features': ['create', 'read', 'update'],
            'reports': ['create', 'read', 'update', 'export'],
            'api_access': ['read', 'write']
        }
    
    elif role_level == 'user':
        # User gets standard permissions
        return {
            'users': ['read'],
            'user_types': ['read'],
            'pipelines': ['read', 'update'],
            'records': ['create', 'read', 'update', 'export'],
            'fields': ['read', 'update'],
            'relationships': ['create', 'read', 'update', 'traverse'],
            'workflows': ['read', 'execute'],
            'business_rules': ['read'],
            'communications': ['create', 'read', 'update'],
            'settings': ['read'],
            'ai_features': ['read', 'update'],
            'reports': ['read', 'export'],
            'api_access': ['read', 'write']
        }
    
    elif role_level == 'viewer':
        # Viewer gets read-only permissions
        return {
            'users': ['read'],
            'user_types': ['read'],
            'pipelines': ['read'],
            'records': ['read', 'export'],
            'fields': ['read'],
            'relationships': ['read'],
            'workflows': ['read'],
            'business_rules': ['read'],
            'communications': ['read'],
            'settings': ['read'],
            'ai_features': ['read'],
            'reports': ['read', 'export'],
            'api_access': ['read']
        }
    
    else:
        # Custom role - minimal default permissions
        return {
            'users': ['read'],
            'pipelines': ['read'],
            'records': ['read'],
            'business_rules': ['read'],
            'api_access': ['read']
        }


def get_permission_registry_info() -> Dict[str, Any]:
    """
    Get information about the permission registry for debugging/admin purposes.
    
    Returns:
        Dict containing registry metadata and statistics
    """
    schema = get_permission_schema()
    
    total_permissions = sum(len(actions) for actions in schema.values())
    categories_count = len(schema)
    
    category_stats = {
        category: {
            'action_count': len(actions),
            'actions': actions
        }
        for category, actions in schema.items()
    }
    
    return {
        'version': '1.0',
        'last_updated': timezone.now().isoformat(),
        'total_categories': categories_count,
        'total_permissions': total_permissions,
        'categories': list(schema.keys()),
        'category_stats': category_stats,
        'available_role_levels': ['admin', 'manager', 'user', 'viewer', 'custom']
    }