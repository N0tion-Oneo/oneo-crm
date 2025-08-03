"""
API URL configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from .views.pipelines import PipelineViewSet, FieldViewSet
from .views.records import RecordViewSet, GlobalSearchViewSet
from .views.relationships import RelationshipViewSet, RelationshipTypeViewSet
from .views.auth import AuthViewSet
from .views.field_types import FieldTypeViewSet
from .views.global_options import GlobalOptionsViewSet
from .views.forms import (
    ValidationRuleViewSet, FormTemplateViewSet, FormFieldConfigurationViewSet
)
from .views.duplicates import (
    DuplicateRuleViewSet, DuplicateMatchViewSet, DuplicateAnalyticsViewSet,
    DuplicateExclusionViewSet
)
from .views.dynamic_forms import DynamicFormViewSet, PublicFormViewSet, SharedRecordViewSet
from relationships.views import AssignmentViewSet

# Import new API modules
from .views.workflows import (
    WorkflowViewSet, WorkflowExecutionViewSet, 
    WorkflowApprovalViewSet, WorkflowScheduleViewSet,
    webhook_endpoint, workflow_status
)
# Import workflow sub-module ViewSets directly to avoid namespace conflicts
from workflows.recovery.views import (
    WorkflowCheckpointViewSet, RecoveryStrategyViewSet,
    WorkflowRecoveryLogViewSet, WorkflowReplaySessionViewSet,
    RecoveryConfigurationViewSet, RecoveryAnalyticsViewSet
)
from workflows.content.views import (
    ContentLibraryViewSet, ContentAssetViewSet, ContentTagViewSet,
    ContentUsageViewSet, ContentApprovalViewSet
)
from .views.communications import (
    ChannelViewSet, ConversationViewSet, 
    MessageViewSet, CommunicationAnalyticsViewSet
)
from .views.tracking import (
    CommunicationTrackingViewSet, DeliveryTrackingViewSet,
    ReadTrackingViewSet, ResponseTrackingViewSet,
    CampaignTrackingViewSet, PerformanceMetricsViewSet,
    PerformanceTrendsView, ChannelComparisonView,
    TimingAnalysisView, AudienceEngagementView,
    PerformanceReportView, TrackingPixelView,
    DeliveryWebhookView, UniPileWebhookView,
    ChannelDashboardView, CampaignDashboardView,
    OverviewDashboardView
)
from .views.realtime import (
    notifications_stream, activity_stream,
    dashboard_stream, pipeline_stream
)

# Create main router
router = DefaultRouter()

# Register main viewsets
router.register(r'pipelines', PipelineViewSet, basename='pipeline')
router.register(r'search', GlobalSearchViewSet, basename='global-search')
router.register(r'relationship-types', RelationshipTypeViewSet, basename='relationshiptype')
router.register(r'relationships', RelationshipViewSet, basename='relationship')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'field-types', FieldTypeViewSet, basename='field-types')
router.register(r'global-options', GlobalOptionsViewSet, basename='global-options')

# Forms and validation endpoints (simplified)
router.register(r'validation-rules', ValidationRuleViewSet, basename='validation-rule')
router.register(r'forms', FormTemplateViewSet, basename='form')
router.register(r'form-fields', FormFieldConfigurationViewSet, basename='form-field')

# Duplicates endpoints
router.register(r'duplicate-rules', DuplicateRuleViewSet, basename='duplicate-rule')
router.register(r'duplicate-matches', DuplicateMatchViewSet, basename='duplicate-match')
router.register(r'duplicate-analytics', DuplicateAnalyticsViewSet, basename='duplicate-analytics')
router.register(r'duplicate-exclusions', DuplicateExclusionViewSet, basename='duplicate-exclusion')

# Dynamic forms endpoints (separate from main pipelines)
router.register(r'public-forms', PublicFormViewSet, basename='public-forms')
router.register(r'shared-records', SharedRecordViewSet, basename='shared-records')

# Workflow endpoints
router.register(r'workflows', WorkflowViewSet, basename='workflow')
router.register(r'executions', WorkflowExecutionViewSet, basename='execution')
router.register(r'approvals', WorkflowApprovalViewSet, basename='approval')
router.register(r'schedules', WorkflowScheduleViewSet, basename='schedule')

# Workflow recovery endpoints
router.register(r'workflow-checkpoints', WorkflowCheckpointViewSet, basename='workflow-checkpoint')
router.register(r'recovery-strategies', RecoveryStrategyViewSet, basename='recovery-strategy')
router.register(r'workflow-recovery-logs', WorkflowRecoveryLogViewSet, basename='workflow-recovery-log')
router.register(r'workflow-replay-sessions', WorkflowReplaySessionViewSet, basename='workflow-replay-session')
router.register(r'recovery-configurations', RecoveryConfigurationViewSet, basename='recovery-configuration')
router.register(r'recovery-analytics', RecoveryAnalyticsViewSet, basename='recovery-analytics')

# Workflow content management endpoints
router.register(r'content-libraries', ContentLibraryViewSet, basename='content-library')
router.register(r'content-assets', ContentAssetViewSet, basename='content-asset')
router.register(r'content-tags', ContentTagViewSet, basename='content-tag')
router.register(r'content-usage', ContentUsageViewSet, basename='content-usage')
router.register(r'content-approvals', ContentApprovalViewSet, basename='content-approval')

# Communication endpoints
router.register(r'channels', ChannelViewSet, basename='channel')
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'communication-analytics', CommunicationAnalyticsViewSet, basename='communication-analytics')

# Communication tracking endpoints
router.register(r'communication-tracking', CommunicationTrackingViewSet, basename='communication-tracking')
router.register(r'delivery-tracking', DeliveryTrackingViewSet, basename='delivery-tracking')
router.register(r'read-tracking', ReadTrackingViewSet, basename='read-tracking')
router.register(r'response-tracking', ResponseTrackingViewSet, basename='response-tracking')
router.register(r'campaign-tracking', CampaignTrackingViewSet, basename='campaign-tracking')
router.register(r'performance-metrics', PerformanceMetricsViewSet, basename='performance-metrics')

# Create nested routers for pipeline-specific endpoints
pipelines_router = routers.NestedDefaultRouter(router, r'pipelines', lookup='pipeline')
pipelines_router.register(r'fields', FieldViewSet, basename='pipeline-fields')
pipelines_router.register(r'records', RecordViewSet, basename='pipeline-records')
pipelines_router.register(r'forms', DynamicFormViewSet, basename='pipeline-forms')

app_name = 'api'

# API URL patterns
api_patterns = [
    # Main API routes
    path('', include(router.urls)),
    path('', include(pipelines_router.urls)),
    
    # Workflow endpoints (non-ViewSet)
    path('workflows/webhook/<uuid:workflow_id>/', webhook_endpoint, name='workflow-webhook'),
    path('workflows/status/<uuid:execution_id>/', workflow_status, name='workflow-status'),
    
    # Workflow content management and recovery routes now registered as ViewSets above
    
    # Communication tracking analytics endpoints
    path('tracking/analytics/trends/', PerformanceTrendsView.as_view(), name='tracking-performance-trends'),
    path('tracking/analytics/channel-comparison/', ChannelComparisonView.as_view(), name='tracking-channel-comparison'),
    path('tracking/analytics/timing-analysis/', TimingAnalysisView.as_view(), name='tracking-timing-analysis'),
    path('tracking/analytics/audience-engagement/', AudienceEngagementView.as_view(), name='tracking-audience-engagement'),
    path('tracking/analytics/performance-report/', PerformanceReportView.as_view(), name='tracking-performance-report'),
    
    # Real-time tracking endpoints
    path('tracking/pixel/<uuid:message_id>/', TrackingPixelView.as_view(), name='tracking-pixel'),
    path('tracking/webhook/delivery/', DeliveryWebhookView.as_view(), name='tracking-delivery-webhook'),
    path('tracking/webhook/unipile/', UniPileWebhookView.as_view(), name='tracking-unipile-webhook'),
    
    # Dashboard endpoints
    path('tracking/dashboard/channel/<uuid:channel_id>/', ChannelDashboardView.as_view(), name='tracking-channel-dashboard'),
    path('tracking/dashboard/campaign/<uuid:campaign_id>/', CampaignDashboardView.as_view(), name='tracking-campaign-dashboard'),
    path('tracking/dashboard/overview/', OverviewDashboardView.as_view(), name='tracking-overview-dashboard'),
    
    # Real-time SSE endpoints
    path('realtime/notifications/', notifications_stream, name='realtime-notifications'),
    path('realtime/activity/', activity_stream, name='realtime-activity'),
    path('realtime/dashboard/<str:dashboard_id>/', dashboard_stream, name='realtime-dashboard'),
    path('realtime/pipeline/<str:pipeline_id>/', pipeline_stream, name='realtime-pipeline'),
    
    # API documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]

# Main URL patterns  
urlpatterns = [
    # API v1 endpoints (tenant URLs already include 'api/' prefix)
    path('v1/', include(api_patterns)),
    
    # Root API endpoints (for direct access without v1)
    path('', include(api_patterns)),
]