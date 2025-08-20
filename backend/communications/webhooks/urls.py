"""
Webhook URL patterns for UniPile integration - Clean separation of concerns
"""
from django.urls import path
from . import views

urlpatterns = [
    # Main webhook endpoint - consolidates all provider and tracking webhooks
    path('unipile/', views.unipile_webhook, name='unipile_webhook'),
    path('health/', views.webhook_health, name='webhook_health'),
    
    # UniPile hosted auth callbacks (accessible via webhook domain)
    path('api/v1/communications/auth/callback/success/', views.hosted_auth_success_callback, name='webhook-hosted-auth-success'),
    path('api/v1/communications/auth/callback/failure/', views.hosted_auth_failure_callback, name='webhook-hosted-auth-failure'),
    
    # Provider-specific webhook aliases (all route to main handler with proper dispatch)
    path('whatsapp/', views.unipile_webhook, name='whatsapp-webhook'),
    path('email/', views.unipile_webhook, name='email-webhook'), 
    path('gmail/', views.unipile_webhook, name='gmail-webhook'),
    path('linkedin/', views.unipile_webhook, name='linkedin-webhook'),
    path('tracking/', views.unipile_webhook, name='tracking-webhook'),
]