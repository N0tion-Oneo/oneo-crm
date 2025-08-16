"""
Public schema URL configuration for Oneo CRM.
This handles requests to the public schema (tenant management, etc.)
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({"status": "ok", "schema": "public"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    
    # Tenant registration (public schema only)
    path('api/tenants/', include('tenants.urls')),
    
    # Global webhook endpoints (accessible from webhook subdomain)
    path('webhooks/', include('communications.webhooks.urls')),
]