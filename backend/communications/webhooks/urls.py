"""
Webhook URL patterns for UniPile integration
"""
from django.urls import path, include
from . import views
from .global_webhook_router import (
    unipile_global_webhook,
    global_webhook_router,
    webhook_health_check
)

urlpatterns = [
    # Legacy webhook endpoints
    path('unipile/', views.unipile_webhook, name='unipile_webhook'),
    path('health/', views.webhook_health, name='webhook_health'),
    
    # New global webhook router endpoints
    path('global/unipile/', unipile_global_webhook, name='global-unipile-webhook'),
    path('global/router/', global_webhook_router, name='global-webhook-router'),
    path('global/health/', webhook_health_check, name='global-webhook-health'),
    
    # UniPile hosted auth callbacks (accessible via webhook domain)
    path('api/v1/communications/auth/callback/success/', views.hosted_auth_success_callback, name='webhook-hosted-auth-success'),
    path('api/v1/communications/auth/callback/failure/', views.hosted_auth_failure_callback, name='webhook-hosted-auth-failure'),
]