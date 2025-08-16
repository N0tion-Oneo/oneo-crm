"""
Webhook URL patterns for UniPile integration
"""
from django.urls import path, include
from . import views

urlpatterns = [
    path('unipile/', views.unipile_webhook, name='unipile_webhook'),
    path('health/', views.webhook_health, name='webhook_health'),
    
    # UniPile hosted auth callbacks (accessible via webhook domain)
    path('api/v1/communications/auth/callback/success/', views.hosted_auth_success_callback, name='webhook-hosted-auth-success'),
    path('api/v1/communications/auth/callback/failure/', views.hosted_auth_failure_callback, name='webhook-hosted-auth-failure'),
]