"""
URL patterns for tenant management and registration
"""

from django.urls import path
from . import views

app_name = 'tenants'

urlpatterns = [
    # Tenant registration endpoints (public schema)
    path('register/', views.register_tenant, name='register_tenant'),
    path('check-subdomain/', views.check_subdomain_availability, name='check_subdomain'),
]