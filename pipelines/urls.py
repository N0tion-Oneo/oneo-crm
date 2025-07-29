"""
URL patterns for pipelines app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PipelineViewSet, FieldViewSet, RecordViewSet,
    PipelineTemplateViewSet, PipelineStatsViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'pipelines', PipelineViewSet)
router.register(r'fields', FieldViewSet)  
router.register(r'records', RecordViewSet)
router.register(r'templates', PipelineTemplateViewSet)
router.register(r'stats', PipelineStatsViewSet, basename='pipeline-stats')

# URL patterns
urlpatterns = [
    path('api/v1/', include(router.urls)),
]

# Named URL patterns for easier reference
app_name = 'pipelines'