#!/usr/bin/env python3
"""
Test the saved filters sharing API directly
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
from pipelines.models import SavedFilter
from django_tenants.utils import schema_context
from api.views.saved_filters import SavedFilterViewSet
from datetime import datetime, timedelta
import json

User = get_user_model()

def test_sharing_api():
    """Test the sharing API directly to debug the 400 error"""
    
    print("🔍 Testing saved filters sharing API...")
    
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
        
        # Get a shareable filter
        shareable_filters = SavedFilter.objects.filter(
            created_by=user,
            is_shareable=True
        )
        
        if not shareable_filters.exists():
            print("❌ No shareable filters found")
            return
        
        test_filter = shareable_filters.first()
        print(f"✅ Found shareable filter: {test_filter.name}")
        
        # Check if it can be shared
        can_share, reason = test_filter.can_be_shared()
        print(f"🔍 Can be shared: {can_share} - {reason}")
        
        if not can_share:
            print("❌ Filter cannot be shared, aborting test")
            return
        
        # Create test payload (similar to frontend)
        expires_at = datetime.now() + timedelta(days=7)
        shareable_fields = list(test_filter.get_shareable_fields())
        
        test_payload = {
            'intended_recipient_email': 'test@example.com',
            'access_mode': 'readonly',
            'expires_at': expires_at.isoformat(),
            'shared_fields': shareable_fields[:3]  # Take first 3 fields
        }
        
        print(f"🔍 Test payload:")
        print(json.dumps(test_payload, indent=2, default=str))
        
        # Test the serializer directly with proper context
        print(f"\n🔍 Testing serializer directly...")
        
        from api.views.serializers import SharedFilterCreateSerializer
        
        # Create a mock request for the serializer
        factory = RequestFactory()
        request = factory.post('/', data=json.dumps(test_payload), content_type='application/json')
        request.user = user
        
        serializer = SharedFilterCreateSerializer(
            data=test_payload,
            context={'request': request, 'saved_filter': test_filter}
        )
        
        print(f"   Serializer valid: {serializer.is_valid()}")
        if not serializer.is_valid():
            print(f"   Errors: {serializer.errors}")
        else:
            print(f"   Validated data: {serializer.validated_data}")
            
            # Test creating the shared filter
            try:
                from utils.encryption import ShareLinkEncryption
                
                encryption = ShareLinkEncryption()
                expires_timestamp = int(serializer.validated_data['expires_at'].timestamp())
                
                encrypted_token = encryption.encrypt_share_data(
                    record_id=str(test_filter.id),
                    user_id=user.id,
                    expires_timestamp=expires_timestamp,
                    access_mode=serializer.validated_data['access_mode']
                )
                
                print(f"✅ Encryption successful!")
                print(f"   Encrypted token length: {len(encrypted_token)}")
                print(f"   First 50 chars: {encrypted_token[:50]}...")
                
                # Test the actual creation
                shared_filter = serializer.save(
                    saved_filter=test_filter,
                    shared_by=user,
                    encrypted_token=encrypted_token
                )
                
                print(f"✅ Shared filter created successfully!")
                print(f"   ID: {shared_filter.id}")
                print(f"   Token: {shared_filter.encrypted_token[:50]}...")
                print(f"   Expires at: {shared_filter.expires_at}")
                
            except Exception as e:
                print(f"❌ Failed to create shared filter: {e}")

if __name__ == '__main__':
    test_sharing_api()