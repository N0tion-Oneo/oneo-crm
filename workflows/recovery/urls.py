"""
URL patterns for workflow recovery system
RESTful endpoints for recovery management and analytics
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    WorkflowCheckpointViewSet, RecoveryStrategyViewSet,
    WorkflowRecoveryLogViewSet, WorkflowReplaySessionViewSet,
    RecoveryConfigurationViewSet, RecoveryAnalyticsViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'checkpoints', WorkflowCheckpointViewSet, basename='checkpoint')
router.register(r'strategies', RecoveryStrategyViewSet, basename='strategy')
router.register(r'recovery-logs', WorkflowRecoveryLogViewSet, basename='recovery-log')
router.register(r'replay-sessions', WorkflowReplaySessionViewSet, basename='replay-session')
router.register(r'configurations', RecoveryConfigurationViewSet, basename='configuration')
router.register(r'analytics', RecoveryAnalyticsViewSet, basename='analytics')

app_name = 'recovery'

urlpatterns = [
    path('', include(router.urls)),
]