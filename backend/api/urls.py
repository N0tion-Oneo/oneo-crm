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

# Create nested routers for pipeline-specific endpoints
pipelines_router = routers.NestedDefaultRouter(router, r'pipelines', lookup='pipeline')
pipelines_router.register(r'fields', FieldViewSet, basename='pipeline-fields')
pipelines_router.register(r'records', RecordViewSet, basename='pipeline-records')

app_name = 'api'

# API URL patterns
api_patterns = [
    # Main API routes
    path('', include(router.urls)),
    path('', include(pipelines_router.urls)),
    
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
    # API v1 endpoints (for backward compatibility)
    path('api/v1/', include(api_patterns)),
    
    # Root API endpoints (for direct access)
    path('', include(api_patterns)),
]