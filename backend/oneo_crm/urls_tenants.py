"""
Tenant schema URL configuration for Oneo CRM.
This handles requests within tenant schemas.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from core.media_views import serve_media


def tenant_health_check(request):
    """Tenant-specific health check endpoint"""
    print(f"🔍 TENANT HEALTH CHECK CALLED! Request: {request.path}")
    print(f"🔍 Host: {request.META.get('HTTP_HOST', 'No host')}")  
    print(f"🔍 Tenant: {getattr(request, 'tenant', 'No tenant')}")
    
    from django_tenants.utils import get_tenant_model
    tenant = get_tenant_model().objects.get(schema_name=request.tenant.schema_name)
    return JsonResponse({
        "status": "ok", 
        "schema": "tenant",
        "tenant_id": tenant.id,
        "tenant_name": tenant.name
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', tenant_health_check, name='tenant_health_check'),
    
    # JWT Authentication (clean DRF approach)
    path('auth/', include('authentication.urls_drf')),
    
    # DRF API endpoints - using nested structure from api app
    path('api/', include('api.urls')),
    
    # Note: Real-time SSE endpoints now available at /api/v1/realtime/
    # WebSocket routing handled separately in asgi.py
]

# Serve media files in development for tenant schemas
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_media, name='tenant_media'),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)