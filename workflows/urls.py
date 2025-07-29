"""
URL patterns for workflow API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WorkflowViewSet, WorkflowExecutionViewSet, WorkflowApprovalViewSet,
    WorkflowScheduleViewSet, webhook_endpoint, workflow_status
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'executions', WorkflowExecutionViewSet, basename='execution')
router.register(r'approvals', WorkflowApprovalViewSet, basename='approval')
router.register(r'schedules', WorkflowScheduleViewSet, basename='schedule')

app_name = 'workflows'

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    
    # Content management routes
    path('api/content/', include('workflows.content.urls')),
    
    # Recovery system routes
    path('api/recovery/', include('workflows.recovery.urls')),
    
    # Webhook endpoints
    path('webhook/<uuid:workflow_id>/', webhook_endpoint, name='webhook'),
    
    # Status endpoints
    path('status/<uuid:execution_id>/', workflow_status, name='status'),
]