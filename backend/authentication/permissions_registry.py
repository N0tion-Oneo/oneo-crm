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
from django_tenants.utils import schema_context


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
        'actions': ['create', 'read', 'update', 'delete', 'execute', 'clone', 'export'],
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
    },
    'forms': {
        'actions': ['create', 'read', 'update', 'delete', 'submit', 'configure'],
        'description': 'Form management and submission',
        'category_display': 'Form Management'
    },
    'validation_rules': {
        'actions': ['create', 'read', 'update', 'delete', 'test'],
        'description': 'Validation rule management and testing',
        'category_display': 'Validation Rules'
    },
    'duplicates': {
        'actions': ['create', 'read', 'update', 'delete', 'resolve', 'detect'],
        'description': 'Duplicate detection and resolution',
        'category_display': 'Duplicate Management'
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
    'write': 'Create and modify content',
    'submit': 'Submit forms and data',
    'resolve': 'Resolve conflicts and duplicates',
    'detect': 'Detect patterns and anomalies',
    'test': 'Test configurations and rules'
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
            'workflows': ['create', 'read', 'update', 'execute', 'clone', 'export'],
            'business_rules': ['create', 'read', 'update'],
            'communications': ['create', 'read', 'update', 'send'],
            'settings': ['read'],
            'monitoring': ['read'],
            'ai_features': ['create', 'read', 'update', 'configure'],
            'reports': ['create', 'read', 'update', 'export'],
            'api_access': ['read', 'write'],
            'forms': ['create', 'read', 'update', 'submit', 'configure'],
            'validation_rules': ['create', 'read', 'update', 'test'],
            'duplicates': ['create', 'read', 'update', 'resolve', 'detect']
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
            'communications': ['create', 'read', 'update', 'send'],
            'settings': ['read'],
            'ai_features': ['read', 'update'],
            'reports': ['read', 'export'],
            'api_access': ['read', 'write'],
            'forms': ['read', 'submit'],
            'validation_rules': ['read'],
            'duplicates': ['read', 'detect']
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
            'api_access': ['read'],
            'forms': ['read'],
            'validation_rules': ['read'],
            'duplicates': ['read']
        }
    
    else:
        # Custom role - minimal default permissions
        return {
            'users': ['read'],
            'pipelines': ['read'],
            'records': ['read'],
            'business_rules': ['read'],
            'api_access': ['read'],
            'forms': ['read'],
            'validation_rules': ['read'],
            'duplicates': ['read']
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


def get_dynamic_tenant_permissions(tenant) -> Dict[str, Any]:
    """
    Generate dynamic permissions based on tenant-specific resources.
    
    Args:
        tenant: Tenant instance
        
    Returns:
        Dict containing dynamic permission categories for tenant resources
    """
    dynamic_permissions = {}
    
    try:
        with schema_context(tenant.schema_name):
            # Import models within tenant context to avoid import issues
            from pipelines.models import Pipeline
            from workflows.models import Workflow
            from forms.models import FormTemplate
            
            # Add pipeline-specific permissions
            try:
                pipelines = Pipeline.objects.filter(is_active=True).select_related('created_by')
                for pipeline in pipelines:
                    permission_key = f'pipeline_{pipeline.id}'
                    dynamic_permissions[permission_key] = {
                        'actions': ['access', 'read', 'create', 'update', 'delete', 'export', 'import'],
                        'description': f'Permissions for {pipeline.name} pipeline',
                        'category_display': f'Pipeline: {pipeline.name}',
                        'resource_type': 'pipeline',
                        'resource_id': pipeline.id,
                        'is_dynamic': True,
                        'parent_category': 'pipelines',
                        'metadata': {
                            'pipeline_name': pipeline.name,
                            'pipeline_type': pipeline.pipeline_type,
                            'access_level': pipeline.access_level,
                            'created_by': pipeline.created_by.email if pipeline.created_by else None,
                            'created_at': pipeline.created_at.isoformat() if pipeline.created_at else None,
                            'record_count': pipeline.record_count,
                        }
                    }
            except Exception:
                # Pipeline model might not exist in some tenants
                pass
            
            # Add workflow-specific permissions
            try:
                workflows = Workflow.objects.filter(status='active').select_related('created_by')
                for workflow in workflows:
                    permission_key = f'workflow_{workflow.id}'
                    dynamic_permissions[permission_key] = {
                        'actions': ['read', 'execute', 'update', 'clone', 'delete', 'export'],
                        'description': f'Permissions for {workflow.name} workflow',
                        'category_display': f'Workflow: {workflow.name}',
                        'resource_type': 'workflow',
                        'resource_id': str(workflow.id),  # UUID field
                        'is_dynamic': True,
                        'parent_category': 'workflows',
                        'metadata': {
                            'workflow_name': workflow.name,
                            'workflow_category': workflow.category,
                            'workflow_status': workflow.status,
                            'created_by': workflow.created_by.email if workflow.created_by else None,
                            'created_at': workflow.created_at.isoformat() if workflow.created_at else None,
                            'version': workflow.version,
                        }
                    }
            except Exception:
                # Workflow model might not exist in some tenants
                pass
            
            # Add form-specific permissions
            try:
                forms = FormTemplate.objects.filter(is_active=True).select_related('created_by')
                for form in forms:
                    permission_key = f'form_{form.id}'
                    dynamic_permissions[permission_key] = {
                        'actions': ['read', 'submit', 'update', 'delete', 'configure'],
                        'description': f'Permissions for {form.name} form',
                        'category_display': f'Form: {form.name}',
                        'resource_type': 'form',
                        'resource_id': form.id,
                        'is_dynamic': True,
                        'parent_category': 'forms',
                        'metadata': {
                            'form_name': form.name,
                            'form_type': getattr(form, 'form_type', 'standard'),
                            'is_public': getattr(form, 'is_public', False),
                            'created_by': form.created_by.email if form.created_by else None,
                            'created_at': form.created_at.isoformat() if form.created_at else None,
                        }
                    }
            except Exception:
                # Form model might not exist in some tenants
                pass
                
    except Exception as e:
        # Log error but continue - tenant might not be properly set up
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to generate dynamic permissions for tenant {tenant.schema_name}: {e}")
    
    return dynamic_permissions


def get_complete_permission_schema(tenant) -> Dict[str, Any]:
    """
    Get complete permission schema including static and dynamic permissions.
    
    Args:
        tenant: Tenant instance
        
    Returns:
        Dict containing complete permission schema for the tenant
    """
    # Start with base static permissions
    complete_schema = PERMISSION_CATEGORIES.copy()
    
    # Add tenant-specific dynamic permissions
    dynamic_permissions = get_dynamic_tenant_permissions(tenant)
    complete_schema.update(dynamic_permissions)
    
    return complete_schema


def get_permission_matrix_configuration(tenant) -> Dict[str, Any]:
    """
    Get complete permission matrix configuration for frontend.
    
    Args:
        tenant: Tenant instance
        
    Returns:
        Dict containing permission matrix configuration for UI
    """
    complete_schema = get_complete_permission_schema(tenant)
    
    # Group permissions by parent category for UI organization
    grouped_categories = {}
    
    # Always include potential resource types for auto-generated tabs
    potential_resource_types = ['pipelines', 'workflows', 'forms', 'reports', 'dashboards']
    for resource_type in potential_resource_types:
        grouped_categories[resource_type] = {
            'items': [],
            'is_expandable': True,
            'total_resources': 0,
            'resource_type': resource_type
        }
    
    for category_key, category_data in complete_schema.items():
        parent_category = category_data.get('parent_category', category_key)
        
        if parent_category not in grouped_categories:
            grouped_categories[parent_category] = {
                'items': [],
                'is_expandable': False,
                'total_resources': 0
            }
        
        if category_data.get('is_dynamic', False):
            grouped_categories[parent_category]['items'].append({
                'key': category_key,
                'data': category_data
            })
            grouped_categories[parent_category]['is_expandable'] = True
            grouped_categories[parent_category]['total_resources'] += 1
        else:
            # Static categories go directly in the root
            if parent_category == category_key:
                grouped_categories[category_key] = {
                    'items': [{'key': category_key, 'data': category_data}],
                    'is_expandable': False,
                    'total_resources': 1
                }
    
    return {
        'categories': complete_schema,
        'grouped_categories': grouped_categories,
        'action_descriptions': ACTION_DESCRIPTIONS,
        'tenant_info': {
            'schema_name': tenant.schema_name,
            'name': tenant.name,
            'max_users': tenant.max_users,
            'features_enabled': tenant.features_enabled
        },
        'ui_config': {
            'collapsible_categories': True,
            'bulk_operations': True,
            'search_enabled': True,
            'export_enabled': True,
            'real_time_updates': True,
            'resource_grouping': True
        },
        'validation_rules': {
            'required_admin_permissions': ['system.full_access'],
            'protected_permissions': [
                'system.full_access',
                'users.delete',
                'user_types.delete'
            ],
            'category_dependencies': {
                'records': ['pipelines.access'],
                'fields': ['pipelines.access'],
                'workflows': ['pipelines.access'],
                'forms': ['pipelines.access']
            },
            'dynamic_resource_limits': {
                'max_pipeline_permissions': 50,
                'max_workflow_permissions': 25,
                'max_form_permissions': 25
            }
        }
    }


