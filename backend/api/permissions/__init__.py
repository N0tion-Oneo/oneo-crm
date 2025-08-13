"""
API Permission Classes

Centralized permission system for all API endpoints.
All permissions are connected to the authentication registry.
"""

# Base permissions
from .base import (
    AdminOnlyPermission,
    TenantMemberPermission,
    ReadOnlyPermission,
)

# Pipeline permissions
from .pipelines import (
    PipelinePermission,
    RecordPermission,
)

# Relationship permissions
from .relationships import (
    RelationshipPermission,
)

# Duplicate permissions
from .duplicates import (
    DuplicatePermission,
)

# Sharing permissions
from .sharing import (
    SharedRecordPermission,
    RecordSharingPermission,
)

# Workflow permissions
from .workflows import (
    WorkflowPermission,
    WorkflowExecutionPermission,
    WorkflowApprovalPermission,
    WorkflowTemplatePermission,
)

# Communication permissions
from .communications import (
    CommunicationPermission,
    MessagePermission,
    ChannelPermission,
    CommunicationTrackingPermission,
)

# Monitoring permissions
from .monitoring import (
    MonitoringPermission,
    AnalyticsPermission,
    AlertPermission,
    SystemMetricsPermission,
)

# AI permissions
from .ai import (
    AIPermission,
    ProcessorPermission,
    AIModelPermission,
    AIPromptTemplatePermission,
)

# Permission utilities
from .utils import (
    check_bulk_permissions,
    get_accessible_resource_ids,
    validate_resource_access,
    has_any_permission,
    has_all_permissions,
    get_user_permission_summary,
)

__all__ = [
    # Base permissions
    'AdminOnlyPermission',
    'TenantMemberPermission',
    'ReadOnlyPermission',
    
    # Pipeline permissions
    'PipelinePermission',
    'RecordPermission',
    
    # Relationship permissions
    'RelationshipPermission',
    
    # Duplicate permissions
    'DuplicatePermission',
    
    # Sharing permissions
    'SharedRecordPermission',
    'RecordSharingPermission',
    
    # Workflow permissions
    'WorkflowPermission',
    'WorkflowExecutionPermission',
    'WorkflowApprovalPermission',
    'WorkflowTemplatePermission',
    
    # Communication permissions
    'CommunicationPermission',
    'MessagePermission',
    'ChannelPermission',
    'CommunicationTrackingPermission',
    
    # Monitoring permissions
    'MonitoringPermission',
    'AnalyticsPermission',
    'AlertPermission',
    'SystemMetricsPermission',
    
    # AI permissions
    'AIPermission',
    'ProcessorPermission',
    'AIModelPermission',
    'AIPromptTemplatePermission',
    
    # Utilities
    'check_bulk_permissions',
    'get_accessible_resource_ids',
    'validate_resource_access',
    'has_any_permission',
    'has_all_permissions',
    'get_user_permission_summary',
]