"""
PermissionMatrixManager for Frontend Configuration

This module provides a high-level interface for managing permission matrices
in the frontend, including bulk operations, validation, and UI-specific features.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import UserType
from .permissions_registry import (
    get_complete_permission_schema,
    get_permission_matrix_configuration,
    validate_permissions,
    ACTION_DESCRIPTIONS
)
from .permissions import SyncPermissionManager

User = get_user_model()


class PermissionMatrixManager:
    """
    Frontend-focused permission matrix manager with bulk operations,
    validation, and UI-specific functionality.
    """
    
    def __init__(self, tenant, user=None):
        self.tenant = tenant
        self.user = user
        
    def get_frontend_matrix_config(self) -> Dict[str, Any]:
        """
        Get complete permission matrix configuration optimized for frontend use.
        
        Returns:
            Comprehensive matrix configuration with UI helpers and performance metrics
        """
        try:
            # Generate fresh configuration
            base_config = get_permission_matrix_configuration(self.tenant)
            
            # Separate static and dynamic permissions for cleaner UI
            static_categories = {}
            dynamic_categories = {}
            resource_type_metadata = {}
            
            # Generate resource type metadata from grouped_categories
            for group_key, group_data in base_config['grouped_categories'].items():
                if group_data.get('is_expandable', False):
                    resource_type_metadata[group_key] = {
                        'display_name': f"{group_key.title()} Access",
                        'icon': self._get_resource_type_icon(group_key),
                        'count': group_data.get('total_resources', 0),
                        'is_expandable': True
                    }
            
            for category_key, category_data in base_config['categories'].items():
                if category_data.get('is_dynamic', False):
                    dynamic_categories[category_key] = category_data
                else:
                    static_categories[category_key] = category_data
            
            # Add frontend-specific enhancements
            frontend_config = {
                **base_config,
                'static_categories': static_categories,
                'dynamic_categories': dynamic_categories,
                'resource_type_metadata': resource_type_metadata,
                'frontend_helpers': self._get_frontend_helpers(),
                'permission_dependencies': self._get_permission_dependencies(),
                'user_type_recommendations': self._get_user_type_recommendations(),
                'bulk_operation_templates': self._get_bulk_operation_templates(),
                'validation_schemas': self._get_validation_schemas(),
                'generated_at': timezone.now().isoformat()
            }
            
            return frontend_config
            
        except Exception as e:
            raise Exception(f"Failed to generate frontend matrix config: {str(e)}")
    
    def _get_resource_type_icon(self, resource_type: str) -> str:
        """Get icon name for resource type"""
        icon_mapping = {
            'pipeline': 'database',
            'workflow': 'workflow',
            'form': 'file-text',
            'report': 'bar-chart-3',
            'dashboard': 'layout-dashboard',
            'api_key': 'key',
            'unknown': 'circle'
        }
        return icon_mapping.get(resource_type, 'circle')
    
    def _get_frontend_helpers(self) -> Dict[str, Any]:
        """Generate UI helper data for the frontend"""
        return {
            'action_icons': {
                'create': 'plus',
                'read': 'eye',
                'update': 'edit',
                'delete': 'trash-2',
                'execute': 'play',
                'access': 'unlock',
                'full_access': 'crown',
                'export': 'download',
                'import': 'upload',
                'configure': 'settings',
                'send': 'send',
                'traverse': 'git-branch',
                'bulk_edit': 'grid-3x3',
                'impersonate': 'user-check',
                'assign_roles': 'user-plus',
                'clone': 'copy',
                'write': 'edit-3'
            },
            'category_colors': {
                'system': '#ef4444',
                'users': '#3b82f6',
                'user_types': '#8b5cf6',
                'pipelines': '#10b981',
                'records': '#06b6d4',
                'fields': '#84cc16',
                'relationships': '#f59e0b',
                'workflows': '#ec4899',
                'business_rules': '#6366f1',
                'communications': '#14b8a6',
                'settings': '#64748b',
                'monitoring': '#78716c',
                'ai_features': '#a855f7',
                'reports': '#0ea5e9',
                'api_access': '#22c55e'
            },
            'permission_levels': {
                'none': {'label': 'No Access', 'color': '#ef4444'},
                'read': {'label': 'Read Only', 'color': '#3b82f6'},
                'write': {'label': 'Read & Write', 'color': '#f59e0b'},
                'admin': {'label': 'Full Access', 'color': '#10b981'}
            },
            'category_descriptions': {
                category: data.get('description', '')
                for category, data in get_complete_permission_schema(self.tenant).items()
            }
        }
    
    def _get_permission_dependencies(self) -> Dict[str, List[str]]:
        """Get permission dependencies for validation"""
        return {
            'records.create': ['pipelines.access'],
            'records.update': ['pipelines.access'],
            'records.delete': ['pipelines.access'],
            'fields.create': ['pipelines.access'],
            'fields.update': ['pipelines.access'],
            'fields.delete': ['pipelines.access'],
            'workflows.execute': ['pipelines.access'],
            'user_types.create': ['users.read'],
            'user_types.update': ['users.read'],
            'user_types.delete': ['users.read']
        }
    
    def _get_user_type_recommendations(self) -> Dict[str, Dict[str, Any]]:
        """Get recommended permission sets for different user types"""
        return {
            'admin': {
                'name': 'System Administrator',
                'description': 'Full access to all system features and user management',
                'recommended_permissions': ['system.full_access'],
                'warning': 'This role has complete system access. Use carefully.'
            },
            'manager': {
                'name': 'Team Manager',
                'description': 'User management and advanced features without system admin',
                'recommended_permissions': [
                    'users.create', 'users.read', 'users.update', 'users.assign_roles',
                    'pipelines.create', 'pipelines.read', 'pipelines.update',
                    'workflows.execute', 'reports.create'
                ],
                'warning': 'Can manage users and create content.'
            },
            'user': {
                'name': 'Standard User',
                'description': 'Standard access for day-to-day operations',
                'recommended_permissions': [
                    'pipelines.read', 'records.create', 'records.read', 'records.update',
                    'workflows.read', 'workflows.execute', 'reports.read'
                ],
                'warning': 'Standard operational access.'
            },
            'viewer': {
                'name': 'Read Only',
                'description': 'Read-only access for viewing and reporting',
                'recommended_permissions': [
                    'pipelines.read', 'records.read', 'workflows.read',
                    'reports.read', 'reports.export'
                ],
                'warning': 'Cannot modify any data.'
            }
        }
    
    def _get_bulk_operation_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get templates for bulk permission operations"""
        return {
            'enable_pipeline_access': {
                'name': 'Enable Pipeline Access',
                'description': 'Grant basic pipeline access with read/write permissions',
                'permissions': ['pipelines.access', 'pipelines.read', 'records.read', 'records.update']
            },
            'enable_user_management': {
                'name': 'Enable User Management',
                'description': 'Grant user management capabilities',
                'permissions': ['users.read', 'users.create', 'users.update', 'users.assign_roles']
            },
            'enable_workflow_access': {
                'name': 'Enable Workflow Access',
                'description': 'Grant workflow execution and management access',
                'permissions': ['workflows.read', 'workflows.execute', 'workflows.create']
            },
            'enable_reporting': {
                'name': 'Enable Reporting',
                'description': 'Grant reporting and analytics access',
                'permissions': ['reports.read', 'reports.create', 'reports.export']
            },
            'disable_destructive_actions': {
                'name': 'Remove Destructive Permissions',
                'description': 'Remove delete permissions across all categories',
                'remove_permissions': [
                    'users.delete', 'user_types.delete', 'pipelines.delete',
                    'records.delete', 'fields.delete', 'workflows.delete'
                ]
            }
        }
    
    def _get_validation_schemas(self) -> Dict[str, Any]:
        """Get validation schemas for permission configurations"""
        return {
            'required_combinations': {
                'pipeline_access': {
                    'description': 'Pipeline access requires basic permissions',
                    'rules': [
                        {'if': 'records.*', 'then': ['pipelines.access']},
                        {'if': 'fields.*', 'then': ['pipelines.access']}
                    ]
                }
            },
            'forbidden_combinations': {
                'viewer_restrictions': {
                    'description': 'Viewers cannot have create/update/delete permissions',
                    'rules': [
                        {'if': 'user_type.viewer', 'forbid': ['*.create', '*.update', '*.delete']}
                    ]
                }
            },
            'permission_limits': {
                'max_dynamic_permissions': 100,
                'max_user_type_permissions': 50,
                'max_categories': 30
            }
        }
    
    def validate_permission_set(self, permissions: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Validate a permission set for consistency and completeness.
        
        Args:
            permissions: Dictionary of category -> actions
            
        Returns:
            Validation result with errors, warnings, and suggestions
        """
        # Use the registry validation as base
        base_validation = validate_permissions(permissions)
        
        # Add frontend-specific validation
        frontend_validation = {
            **base_validation,
            'frontend_warnings': [],
            'suggestions': [],
            'dependency_errors': []
        }
        
        # Check permission dependencies
        dependencies = self._get_permission_dependencies()
        for permission, required_perms in dependencies.items():
            category, action = permission.split('.')
            if category in permissions and action in permissions[category]:
                for required_perm in required_perms:
                    req_category, req_action = required_perm.split('.')
                    if req_category not in permissions or req_action not in permissions[req_category]:
                        frontend_validation['dependency_errors'].append(
                            f"Permission '{permission}' requires '{required_perm}'"
                        )
        
        # Add suggestions based on common patterns
        if 'users' in permissions and 'read' in permissions['users']:
            if 'user_types' not in permissions or 'read' not in permissions['user_types']:
                frontend_validation['suggestions'].append(
                    "Consider adding 'user_types.read' for better user management"
                )
        
        return frontend_validation
    
    def apply_bulk_operation(self, user_type_id: int, operation_name: str, 
                           custom_permissions: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Apply a bulk permission operation to a user type.
        
        Args:
            user_type_id: Target user type ID
            operation_name: Name of bulk operation template
            custom_permissions: Custom permission list (overrides template)
            
        Returns:
            Operation result with applied permissions and validation
        """
        if not self.user:
            raise ValueError("User context required for bulk operations")
        
        # Check permission to modify user types
        permission_manager = SyncPermissionManager(self.user)
        if not permission_manager.has_permission('action', 'user_types', 'update'):
            raise PermissionError("Insufficient permissions to modify user types")
        
        try:
            with transaction.atomic():
                user_type = UserType.objects.get(id=user_type_id)
                current_permissions = user_type.base_permissions.copy()
                
                # Get operation template or use custom permissions
                if custom_permissions:
                    operation_permissions = custom_permissions
                    remove_permissions = []
                else:
                    templates = self._get_bulk_operation_templates()
                    if operation_name not in templates:
                        raise ValueError(f"Unknown operation template: {operation_name}")
                    
                    template = templates[operation_name]
                    operation_permissions = template.get('permissions', [])
                    remove_permissions = template.get('remove_permissions', [])
                
                # Apply permissions
                changes_made = []
                
                # Add permissions
                for permission in operation_permissions:
                    category, action = permission.split('.')
                    if category not in current_permissions:
                        current_permissions[category] = []
                    if action not in current_permissions[category]:
                        current_permissions[category].append(action)
                        changes_made.append(f"Added {permission}")
                
                # Remove permissions
                for permission in remove_permissions:
                    category, action = permission.split('.')
                    if category in current_permissions and action in current_permissions[category]:
                        current_permissions[category].remove(action)
                        changes_made.append(f"Removed {permission}")
                        # Clean up empty categories
                        if not current_permissions[category]:
                            del current_permissions[category]
                
                # Validate the new permission set
                validation = self.validate_permission_set(current_permissions)
                
                if validation['valid']:
                    # Apply changes
                    user_type.base_permissions = current_permissions
                    user_type.save(update_fields=['base_permissions'])
                    
                    return {
                        'success': True,
                        'user_type_id': user_type_id,
                        'operation': operation_name,
                        'changes_made': changes_made,
                        'validation': validation,
                        'applied_at': timezone.now().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Validation failed',
                        'validation': validation,
                        'changes_made': changes_made
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user_type_comparison(self, user_type_ids: List[int]) -> Dict[str, Any]:
        """
        Compare permissions across multiple user types.
        
        Args:
            user_type_ids: List of user type IDs to compare
            
        Returns:
            Comparison matrix with differences highlighted
        """
        try:
            user_types = UserType.objects.filter(id__in=user_type_ids)
            comparison = {
                'user_types': {},
                'permission_matrix': {},
                'differences': [],
                'summary': {}
            }
            
            # Get all unique permissions across user types
            all_permissions = set()
            for user_type in user_types:
                comparison['user_types'][user_type.id] = {
                    'name': user_type.name,
                    'slug': user_type.slug,
                    'permissions': user_type.base_permissions
                }
                
                # Flatten permissions for comparison
                for category, actions in user_type.base_permissions.items():
                    for action in actions:
                        all_permissions.add(f"{category}.{action}")
            
            # Build comparison matrix
            for permission in sorted(all_permissions):
                comparison['permission_matrix'][permission] = {}
                has_permission = []
                
                for user_type in user_types:
                    category, action = permission.split('.')
                    has_perm = (
                        category in user_type.base_permissions and 
                        action in user_type.base_permissions[category]
                    )
                    comparison['permission_matrix'][permission][user_type.id] = has_perm
                    if has_perm:
                        has_permission.append(user_type.id)
                
                # Record differences
                if len(has_permission) > 0 and len(has_permission) < len(user_types):
                    comparison['differences'].append({
                        'permission': permission,
                        'has_access': has_permission,
                        'missing_access': [ut.id for ut in user_types if ut.id not in has_permission]
                    })
            
            # Generate summary
            comparison['summary'] = {
                'total_permissions': len(all_permissions),
                'total_differences': len(comparison['differences']),
                'user_type_count': len(user_types),
                'common_permissions': [
                    perm for perm, access in comparison['permission_matrix'].items()
                    if all(access.values())
                ]
            }
            
            return comparison
            
        except Exception as e:
            raise Exception(f"Failed to compare user types: {str(e)}")
    
    
    
    def get_permission_usage_analytics(self) -> Dict[str, Any]:
        """Get analytics about permission usage in the tenant"""
        try:
            user_types = UserType.objects.all()
            analytics = {
                'user_type_stats': {},
                'permission_popularity': {},
                'category_usage': {},
                'total_users': User.objects.count(),
                'total_user_types': user_types.count()
            }
            
            # Analyze user type usage
            for user_type in user_types:
                user_count = User.objects.filter(user_type=user_type).count()
                permission_count = sum(
                    len(actions) for actions in user_type.base_permissions.values()
                )
                
                analytics['user_type_stats'][user_type.id] = {
                    'name': user_type.name,
                    'user_count': user_count,
                    'permission_count': permission_count,
                    'is_system_default': user_type.is_system_default
                }
            
            # Analyze permission popularity
            permission_counts = {}
            category_counts = {}
            
            for user_type in user_types:
                user_count = User.objects.filter(user_type=user_type).count()
                
                for category, actions in user_type.base_permissions.items():
                    category_counts[category] = category_counts.get(category, 0) + user_count
                    
                    for action in actions:
                        permission_key = f"{category}.{action}"
                        permission_counts[permission_key] = permission_counts.get(permission_key, 0) + user_count
            
            analytics['permission_popularity'] = dict(
                sorted(permission_counts.items(), key=lambda x: x[1], reverse=True)[:20]
            )
            analytics['category_usage'] = dict(
                sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
            )
            
            return analytics
            
        except Exception as e:
            raise Exception(f"Failed to generate permission analytics: {str(e)}")