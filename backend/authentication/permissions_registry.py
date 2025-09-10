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
    # ==========================================
    # SYSTEM & ADMINISTRATION
    # ==========================================
    'system': {
        'actions': ['full_access'],
        'description': 'System-wide administrative access and platform management',
        'category_display': 'System Administration'
    },
    'monitoring': {
        'actions': ['read', 'update'],
        'description': 'System monitoring and analytics',
        'category_display': 'System Monitoring'
    },
    'api_access': {
        'actions': ['read', 'write', 'full_access'],
        'description': 'API access control and management',
        'category_display': 'API Access'
    },
    
    # ==========================================
    # USER & ACCESS MANAGEMENT
    # ==========================================
    'users': {
        'actions': ['create', 'read', 'update', 'delete', 'impersonate', 'assign_roles', 'read_all'],
        'description': 'User account management and role assignment',
        'category_display': 'User Management'
    },
    'user_types': {
        'actions': ['create', 'read', 'update', 'delete'],
        'description': 'User type and role management',
        'category_display': 'User Type Management'
    },
    'permissions': {
        'actions': ['read', 'manage'],
        'description': 'Permission management and role assignment',
        'category_display': 'Permission Management'
    },
    'staff_profiles': {
        'actions': ['create', 'read', 'update', 'delete', 'read_all', 'update_all', 'read_sensitive', 'update_sensitive', 'read_admin', 'update_admin'],
        'description': 'Staff profile management and HR information',
        'category_display': 'Staff Profiles'
    },
    
    # ==========================================
    # CORE DATA MANAGEMENT
    # ==========================================
    'pipelines': {
        'actions': ['access', 'create', 'read', 'update', 'delete', 'clone', 'export', 'import', 'read_all'],
        'description': 'Pipeline management and configuration',
        'category_display': 'Pipeline Management'
    },
    'records': {
        'actions': ['create', 'read', 'update', 'delete', 'export', 'import', 'read_all'],
        'description': 'Record data management and operations',
        'category_display': 'Record Management'
    },
    'fields': {
        'actions': ['read', 'manage', 'delete'],
        'description': 'Field viewing and configuration management',
        'category_display': 'Field Management'
    },
    'relationships': {
        'actions': ['create', 'read', 'update', 'delete', 'traverse'],
        'description': 'Relationship management and traversal',
        'category_display': 'Relationship Management'
    },
    'business_rules': {
        'actions': ['create', 'read', 'update', 'delete', 'execute'],
        'description': 'Business rules configuration and management',
        'category_display': 'Business Rules'
    },
    'duplicates': {
        'actions': ['create', 'read', 'update', 'delete', 'resolve', 'detect'],
        'description': 'Duplicate detection and resolution',
        'category_display': 'Duplicate Management'
    },
    
    # ==========================================
    # AUTOMATION & WORKFLOWS
    # ==========================================
    'workflows': {
        'actions': ['create', 'read', 'update', 'delete', 'execute', 'clone', 'export'],
        'description': 'Workflow automation and execution',
        'category_display': 'Workflow Management'
    },
    'ai_features': {
        'actions': ['create', 'read', 'update', 'delete', 'configure', 'read_all'],
        'description': 'AI features and configuration management',
        'category_display': 'AI Features'
    },
    
    # ==========================================
    # COMMUNICATION & COLLABORATION
    # ==========================================
    'communications': {
        'actions': ['create', 'read', 'update', 'delete', 'send'],
        'description': 'Communication management and messaging',
        'category_display': 'Communication Management'
    },
    'participants': {
        'actions': ['create', 'read', 'update', 'delete', 'link', 'batch'],
        'description': 'Communication participant management operations',
        'category_display': 'Participant Management'
    },
    'sharing': {
        'actions': ['create_shared_views', 'create_shared_forms', 'configure_shared_views_forms', 'revoke_shared_views_forms'],
        'description': 'External sharing and collaboration features',
        'category_display': 'Sharing & Collaboration'
    },
    
    # ==========================================
    # CONTENT & REPORTS
    # ==========================================
    'forms': {
        'actions': ['create', 'read', 'update', 'delete', 'submit', 'configure'],
        'description': 'Form creation and management system',
        'category_display': 'Forms Management'
    },
    'reports': {
        'actions': ['create', 'read', 'update', 'delete', 'export'],
        'description': 'Report generation and management',
        'category_display': 'Reports & Analytics'
    },
    'filters': {
        'actions': ['create_filters', 'edit_filters', 'delete_filters'],
        'description': 'Saved filter creation and management',
        'category_display': 'Filter Management'
    },
    
    # ==========================================
    # SETTINGS PAGES (Page-level access)
    # ==========================================
    'settings': {
        'actions': [
            # Page-based permissions - if you have access, you can view and edit
            'organization',      # /settings page
            'users',             # /settings/users page
            'permissions',       # /settings/permissions page
            'branding',          # /settings/branding page
            'localization',      # /settings/localization page
            'security',          # /settings/security page
            'data_policies',     # /settings/data-policies page
            'usage',             # /settings/usage page
            'communications',    # /settings/communications main page
            'ai',                # /settings/ai page
            'celery'             # /settings/celery page - task management
        ],
        'description': 'Settings pages access - having permission grants both view and edit',
        'category_display': 'Settings'
    },
    'communication_settings': {
        'actions': [
            # Communication sub-settings pages
            'general',           # /settings/communications/general page
            'accounts',          # /settings/communications/accounts page
            'providers',         # /settings/communications/providers page
            'participants',      # /settings/communications/participants page
            'scheduling',        # /settings/communications/scheduling page
            'scheduling_all',    # Admin: manage all users' scheduling
            'advanced'           # /settings/communications/advanced page
        ],
        'description': 'Communication settings sub-pages access',
        'category_display': 'Communication Settings'
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
    'impersonate': 'Act on behalf of other users',
    'assign_roles': 'Assign roles to users',
    'access': 'Basic access to resources',
    'full_access': 'Complete administrative access',
    'write': 'Create and modify content',
    'recover': 'Restore deleted or archived items',
    'migrate': 'Migrate data structure and schema',
    'resolve': 'Resolve conflicts and duplicates',
    'detect': 'Detect patterns and anomalies',
    # Administrative permissions
    'access': 'Access and view specific resources',
    'read_all': 'Read all items regardless of ownership or restrictions',
    'submit': 'Submit forms and applications',
    # Staff profile permissions
    'update_all': 'Update all staff profiles',
    'read_sensitive': 'View sensitive personal information',
    'update_sensitive': 'Edit sensitive personal information', 
    'read_admin': 'View administrative notes',
    'update_admin': 'Edit administrative notes',
    # Filter permissions
    'create_filters': 'Create and save new filters',
    'edit_filters': 'Modify existing filters',
    'delete_filters': 'Remove filters permanently',
    # Sharing permissions
    'create_shared_views': 'Create external shared views',
    'create_shared_forms': 'Create external shared forms',
    'configure_shared_views_forms': 'Configure sharing settings and permissions',
    'revoke_shared_views_forms': 'Revoke and manage external shares',
    # Permission management actions
    'manage': 'Manage permissions and role assignments (grant, revoke, update)',
    # Participant management actions
    'link': 'Link participants to records',
    'batch': 'Run batch participant processing',
    
    # Nested settings permissions
    'read_organization': 'View organization settings',
    'update_organization': 'Modify organization settings',
    'read_branding': 'View branding settings',
    'update_branding': 'Modify branding settings',
    'read_localization': 'View localization settings',
    'update_localization': 'Modify localization settings',
    'read_security': 'View security settings',
    'update_security': 'Modify security settings',
    'read_data_policies': 'View data policy settings',
    'update_data_policies': 'Modify data policy settings',
    'read_billing': 'View billing and usage settings',
    'update_billing': 'Modify billing and usage settings',
    'read_communication_general': 'View general communication settings',
    'update_communication_general': 'Modify general communication settings',
    'read_communication_provider': 'View communication provider settings',
    'update_communication_provider': 'Modify communication provider settings',
    'read_communication_advanced': 'View advanced communication settings',
    'update_communication_advanced': 'Modify advanced communication settings',
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
            'users': ['create', 'read', 'update', 'assign_roles', 'read_all'],
            'user_types': ['read'],
            'pipelines': ['access', 'create', 'read', 'update', 'clone', 'export', 'read_all'],
            'records': ['create', 'read', 'update', 'export', 'read_all'],
            'fields': ['create', 'read', 'update', 'recover'],
            'relationships': ['create', 'read', 'update', 'traverse'],
            'workflows': ['create', 'read', 'update', 'execute', 'clone', 'export'],
            'business_rules': ['create', 'read', 'update'],
            'communications': ['create', 'read', 'update', 'send'],
            'settings': ['read'],
            'organization_settings': ['read', 'update'],
            'branding_settings': ['read', 'update'],
            'localization_settings': ['read'],
            'security_settings': ['read'],
            'data_policies_settings': ['read'],
            'billing_settings': ['read'],
            'communication_general_settings': ['read', 'update'],
            'communication_provider_settings': ['read'],
            'communication_participants_settings': ['read', 'update'],
            'communication_advanced_settings': ['read'],
            'monitoring': ['read'],
            'ai_features': ['create', 'read', 'update', 'configure', 'read_all'],
            'reports': ['create', 'read', 'update', 'export'],
            'api_access': ['read', 'write'],
            'duplicates': ['create', 'read', 'update', 'resolve', 'detect'],
            'filters': ['create_filters', 'edit_filters', 'delete_filters'],
            'sharing': ['create_shared_views', 'create_shared_forms', 'configure_shared_views_forms', 'revoke_shared_views_forms'],
            'forms': ['create', 'read', 'update', 'delete', 'configure'],
            'permissions': ['read', 'manage'],
            'staff_profiles': ['create', 'read', 'update', 'read_all', 'update_all', 'read_sensitive', 'update_sensitive'],
            'participants': ['create', 'read', 'update', 'link', 'batch']
        }
    
    elif role_level == 'user':
        # User gets standard permissions
        return {
            'users': ['read'],
            'user_types': ['read'],
            'pipelines': ['access', 'read', 'update'],
            'records': ['create', 'read', 'update', 'export'],
            'fields': ['read', 'update'],
            'relationships': ['create', 'read', 'update', 'traverse'],
            'workflows': ['read', 'execute'],
            'business_rules': ['read'],
            'communications': ['create', 'read', 'update', 'send'],
            'settings': ['read'],
            'organization_settings': ['read'],
            'branding_settings': ['read'],
            'localization_settings': ['read'],
            'security_settings': [],
            'data_policies_settings': [],
            'billing_settings': [],
            'communication_general_settings': ['read'],
            'communication_provider_settings': [],
            'communication_participants_settings': ['read'],
            'communication_advanced_settings': [],
            'ai_features': ['read', 'update'],
            'reports': ['read', 'export'],
            'api_access': ['read', 'write'],
            'duplicates': ['read', 'detect'],
            'filters': ['create_filters', 'edit_filters'],
            'sharing': ['create_shared_views'],
            'forms': ['read', 'submit'],
            'permissions': ['read'],
            'staff_profiles': ['read', 'update'],  # Users can view and update their own profile
            'participants': ['read', 'link']
        }
    
    elif role_level == 'viewer':
        # Viewer gets read-only permissions
        return {
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
            'organization_settings': ['read'],
            'branding_settings': ['read'],
            'localization_settings': [],
            'security_settings': [],
            'data_policies_settings': [],
            'billing_settings': [],
            'communication_general_settings': [],
            'communication_provider_settings': [],
            'communication_advanced_settings': [],
            'ai_features': ['read'],
            'reports': ['read', 'export'],
            'api_access': ['read'],
            'duplicates': ['read'],
            'filters': [],  # Viewers cannot create or edit filters
            'sharing': [],  # Viewers cannot share
            'forms': ['read'],  # Viewers can only read forms
            'permissions': ['read'],
            'staff_profiles': ['read'],  # Viewers can only view staff profiles
            'participants': ['read']
        }
    
    else:
        # Custom role - minimal default permissions
        return {
            'users': ['read'],
            'pipelines': ['access', 'read'],
            'records': ['read'],
            'business_rules': ['read'],
            'api_access': ['read'],
            'duplicates': ['read'],
            'filters': [],
            'sharing': [],
            'forms': ['read'],
            'permissions': ['read']
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
    potential_resource_types = ['pipelines', 'workflows', 'reports', 'dashboards']
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
                'workflows': ['pipelines.access']
            },
            'dynamic_resource_limits': {
                'max_pipeline_permissions': 50,
                'max_workflow_permissions': 25
            }
        }
    }


