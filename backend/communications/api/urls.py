"""
URL patterns for communications API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountConnectionViewSet
from .account_views import (
    CommunicationConnectionViewSet, 
    request_hosted_auth, 
    hosted_auth_success_callback,
    hosted_auth_failure_callback,
    solve_checkpoint,
    resend_checkpoint,
    reconnect_account
)

router = DefaultRouter()
router.register(r'accounts', AccountConnectionViewSet, basename='account-connection')
router.register(r'connections', CommunicationConnectionViewSet, basename='communication-connection')

urlpatterns = [
    path('', include(router.urls)),
    
    # Account management endpoints for frontend (non-conflicting paths)
    path('request-hosted-auth/', request_hosted_auth, name='request-hosted-auth'),
    
    # Hosted authentication callbacks
    path('auth/callback/success/', hosted_auth_success_callback, name='hosted-auth-success'),
    path('auth/callback/failure/', hosted_auth_failure_callback, name='hosted-auth-failure'),
    
    # Checkpoint management
    path('connections/<uuid:connection_id>/checkpoint/solve/', solve_checkpoint, name='solve-checkpoint'),
    path('connections/<uuid:connection_id>/checkpoint/resend/', resend_checkpoint, name='resend-checkpoint'),
    path('connections/<uuid:connection_id>/reconnect/', reconnect_account, name='reconnect-account'),
]