"""
DRF Router-based URLs for Authentication
Clean RESTful routing using DRF routers and ViewSets
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import jwt_views, viewsets, simple_test_view

app_name = 'auth_drf'

# DRF Router for ViewSets
router = DefaultRouter()
router.register(r'users', viewsets.UserViewSet)
router.register(r'user-types', viewsets.UserTypeViewSet)
router.register(r'sessions', viewsets.UserSessionViewSet, basename='session')

# Enhanced Permission ViewSets
router.register(r'user-type-pipeline-permissions', viewsets.UserTypePipelinePermissionViewSet, basename='user-type-pipeline-permission')
router.register(r'user-type-field-permissions', viewsets.UserTypeFieldPermissionViewSet, basename='user-type-field-permission')
router.register(r'user-pipeline-overrides', viewsets.UserPipelinePermissionOverrideViewSet, basename='user-pipeline-override')

# Combine JWT auth endpoints with DRF ViewSets
urlpatterns = [
    # JWT Authentication endpoints
    path('login/', jwt_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', jwt_views.CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', jwt_views.logout_view, name='logout'),
    
    # User info endpoints (also available via ViewSet)  
    path('me/', jwt_views.current_user_view, name='current_user'),
    
    # Health check
    path('health/', jwt_views.health_check_view, name='health_check'),
    
    # Simple JWT test
    path('test-jwt/', simple_test_view.SimpleJWTTestView.as_view(), name='test_jwt'),
    
    # DRF ViewSet routes
    path('', include(router.urls)),
]