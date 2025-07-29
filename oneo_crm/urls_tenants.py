"""
Tenant schema URL configuration for Oneo CRM.
This handles requests within tenant schemas.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


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
    
    # Phase 05 - Comprehensive API Layer
    path('', include('api.urls')),
    
    # Phase 06 - Real-time Collaboration
    path('realtime/', include('realtime.urls')),
    
    # Phase 07 - Workflow Automation
    path('workflows/', include('workflows.urls')),
    
    # Phase 08 - Communication Layer
    path('communications/', include('communications.urls')),
    
    # Legacy endpoints (may be deprecated)
    path('auth/', include('authentication.urls')),
    path('pipelines/', include('pipelines.urls')),
    path('relationships/', include('relationships.urls')),
]