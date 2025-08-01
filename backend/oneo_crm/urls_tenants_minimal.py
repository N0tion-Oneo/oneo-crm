"""
Minimal tenant URLs for testing basic functionality
"""

from django.contrib import admin
from django.urls import path
from django.http import JsonResponse


def tenant_health_check(request):
    """Tenant-specific health check endpoint"""
    from django_tenants.utils import get_tenant_model
    tenant = get_tenant_model().objects.get(schema_name=request.tenant.schema_name)
    return JsonResponse({
        "status": "ok", 
        "schema": "tenant",
        "tenant_id": tenant.id,
        "tenant_name": tenant.name
    })


def test_endpoint(request):
    """Simple test endpoint"""
    return JsonResponse({"message": "Test endpoint working", "path": request.path})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', tenant_health_check, name='tenant_health_check'),
    path('test/', test_endpoint, name='test_endpoint'),
]