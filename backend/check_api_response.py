#!/usr/bin/env python3
"""
Check what the saved filters API is actually returning
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from tenants.models import Tenant
from django_tenants.utils import schema_context
from api.views.saved_filters import SavedFilterViewSet
from django.contrib.auth.models import AnonymousUser

User = get_user_model()

def check_api_response():
    """Check what the API returns for saved filters"""
    
    print("🔍 Checking saved filters API response...")
    
    # Get oneotalent tenant
    try:
        talent_tenant = Tenant.objects.get(schema_name='oneotalent')
        print(f"✅ Found oneotalent tenant: {talent_tenant.name}")
    except Tenant.DoesNotExist:
        print("❌ Oneotalent tenant not found")
        return
    
    with schema_context('oneotalent'):
        # Get user
        try:
            user = User.objects.get(email='josh@oneodigital.com')
            print(f"✅ Found user: {user.email}")
        except User.DoesNotExist:
            print("❌ User not found")
            return
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/api/v1/saved-filters/')
        request.user = user
        
        # Create the viewset and get the queryset
        viewset = SavedFilterViewSet()
        viewset.setup(request)
        
        # Get the filters
        filters = viewset.get_queryset()
        print(f"📋 Found {filters.count()} saved filters for user")
        
        for filter_obj in filters:
            print(f"\n🔍 Filter: {filter_obj.name}")
            print(f"   ID: {filter_obj.id}")
            print(f"   Pipeline: {filter_obj.pipeline.name}")
            print(f"   Is shareable: {filter_obj.is_shareable}")
            
            # Check sharing capability
            can_share, reason = filter_obj.can_be_shared()
            print(f"   Can be shared: {can_share} - {reason}")
            
            # Get shareable fields
            shareable_fields = list(filter_obj.get_shareable_fields())
            print(f"   Shareable fields: {shareable_fields}")
            
            # Test serialization
            serializer = viewset.get_serializer(filter_obj)
            data = serializer.data
            
            print(f"   Serialized data:")
            print(f"     - filter_config present: {'filter_config' in data}")
            print(f"     - can_share: {data.get('can_share', 'Missing!')}")
            print(f"     - shareable_fields: {data.get('shareable_fields', 'Missing!')}")
            print(f"     - visible_fields: {data.get('visible_fields', 'Missing!')}")

if __name__ == '__main__':
    check_api_response()