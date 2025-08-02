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
    
    # Dynamic form generation endpoints will be added later
    
    # Authentication endpoints (removed to fix namespace conflict)
    # path('auth/', include('rest_framework.urls')),
    
    # GraphQL endpoint removed - using DRF only
    
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