"""
Workflow views module
"""
# Import main workflow views from original file
from ..views_original import (
    WorkflowViewSet,
    WorkflowExecutionViewSet,
    WorkflowApprovalViewSet,
    WorkflowScheduleViewSet,
    webhook_endpoint,
    workflow_status
)

# Import trigger event views
from .trigger_events import (
    FormSubmissionTriggerView,
    WebhookTriggerView,
    RecordEventTriggerView,
    EmailReceivedTriggerView
)

__all__ = [
    # Main workflow views
    'WorkflowViewSet',
    'WorkflowExecutionViewSet',
    'WorkflowApprovalViewSet',
    'WorkflowScheduleViewSet',
    'webhook_endpoint',
    'workflow_status',
    # Trigger event views
    'FormSubmissionTriggerView',
    'WebhookTriggerView',
    'RecordEventTriggerView',
    'EmailReceivedTriggerView'
]