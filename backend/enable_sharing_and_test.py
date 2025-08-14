#!/usr/bin/env python3
"""
Enable sharing for Sales Pipeline fields and test complete sharing workflow
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenants.models import Tenant
from pipelines.models import Pipeline, Field, SavedFilter
from sharing.models import SharedFilter
from django_tenants.utils import schema_context
from django.utils import timezone
from datetime import timedelta
import json

User = get_user_model()

def enable_sharing_and_test():
    """Enable sharing for some fields and test the complete workflow"""
    
    print("🔧 Enabling sharing for Sales Pipeline fields and testing...")
    
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
        
        # Get Sales Pipeline
        try:
            sales_pipeline = Pipeline.objects.get(name='Sales Pipeline')
            print(f"✅ Found Sales Pipeline: {sales_pipeline.name}")
        except Pipeline.DoesNotExist:
            print("❌ Sales Pipeline not found")
            return
        
        # Enable sharing for appropriate fields (non-sensitive ones)
        fields_to_share = [
            'company_name',
            'company_description', 
            'deal_value',
            'pipeline_stages',
            'interview_date',
            'company_website',
            'company_tags'
        ]
        
        print(f"🔧 Enabling sharing for selected fields...")
        enabled_count = 0
        for field_slug in fields_to_share:
            try:
                field = sales_pipeline.fields.get(slug=field_slug)
                if not field.is_visible_in_shared_list_and_detail_views:
                    field.is_visible_in_shared_list_and_detail_views = True
                    field.save(update_fields=['is_visible_in_shared_list_and_detail_views'])
                    enabled_count += 1
                    print(f"   ✅ Enabled sharing for: {field.name}")
                else:
                    print(f"   ℹ️ Already shareable: {field.name}")
            except Field.DoesNotExist:
                print(f"   ⚠️ Field not found: {field_slug}")
        
        print(f"✅ Enabled sharing for {enabled_count} additional fields")
        
        # Create or update a test saved filter
        test_filter_config = {
            "groups": [
                {
                    "id": "group-1",
                    "logic": "AND",
                    "filters": [
                        {
                            "field": "pipeline_stages",
                            "operator": "equals",
                            "value": "qualified",
                            "id": "filter-1"
                        }
                    ]
                }
            ],
            "groupLogic": "AND"
        }
        
        saved_filter, created = SavedFilter.objects.get_or_create(
            name='Qualified Sales Leads',
            pipeline=sales_pipeline,
            created_by=user,
            defaults={
                'description': 'All qualified sales leads ready for follow-up',
                'filter_config': test_filter_config,
                'view_mode': 'table',
                'visible_fields': ['company_name', 'deal_value', 'pipeline_stages', 'interview_date'],
                'is_shareable': True,
                'share_access_level': 'readonly'
            }
        )
        
        if created:
            print(f"✅ Created new saved filter: {saved_filter.name}")
        else:
            # Update existing filter to use shareable fields
            saved_filter.visible_fields = ['company_name', 'deal_value', 'pipeline_stages', 'interview_date']
            saved_filter.is_shareable = True
            saved_filter.save()
            print(f"✅ Updated existing saved filter: {saved_filter.name}")
        
        # Test sharing capabilities
        can_share, reason = saved_filter.can_be_shared()
        print(f"🔍 Can be shared: {can_share} - {reason}")
        
        # Get shareable fields
        shareable_fields = list(saved_filter.get_shareable_fields())
        print(f"📋 Shareable fields: {shareable_fields}")
        
        # Test creating a share link (simulate the API call)
        if can_share:
            expires_at = timezone.now() + timedelta(days=7)
            
            # Create a shared filter
            shared_filter = SharedFilter.objects.create(
                saved_filter=saved_filter,
                shared_by=user,
                intended_recipient_email='test@example.com',
                access_mode='readonly',
                expires_at=expires_at,
                shared_fields=shareable_fields,
                encrypted_token='test-token-12345'  # In real use, this would be properly encrypted
            )
            
            print(f"✅ Created share link!")
            print(f"   Token: {shared_filter.encrypted_token}")
            print(f"   Expires: {shared_filter.expires_at}")
            print(f"   Shared fields: {shared_filter.shared_fields}")
            print(f"   Access mode: {shared_filter.access_mode}")
            
            # Test API serialization
            from api.views.serializers import SavedFilterSerializer, SharedFilterSerializer
            
            # Serialize the saved filter
            filter_serializer = SavedFilterSerializer(saved_filter)
            serialized_data = filter_serializer.data
            
            print(f"\n🔄 Saved Filter API Data:")
            print(f"   Filter config present: {'filter_config' in serialized_data}")
            print(f"   Can share: {serialized_data.get('can_share', {})}")
            print(f"   Shareable fields count: {len(serialized_data.get('shareable_fields', []))}")
            
            # Serialize the shared filter
            share_serializer = SharedFilterSerializer(shared_filter)
            share_data = share_serializer.data
            
            print(f"\n🔗 Share Link API Data:")
            print(f"   Token: {share_data.get('encrypted_token', 'N/A')}")
            print(f"   Status: {share_data.get('status', 'N/A')}")
            print(f"   Time remaining: {share_data.get('time_remaining', 'N/A')} seconds")
            
            return {
                'tenant': talent_tenant.schema_name,
                'user_id': user.id,
                'pipeline_id': sales_pipeline.id,
                'filter_id': str(saved_filter.id),
                'share_id': shared_filter.id,
                'share_token': shared_filter.encrypted_token,
                'can_share': can_share,
                'shareable_fields': shareable_fields,
                'shareable_count': len(shareable_fields)
            }
        else:
            print(f"❌ Cannot create share link: {reason}")
            return None

if __name__ == '__main__':
    result = enable_sharing_and_test()
    if result:
        print(f"\n📊 Sharing Test Results:")
        for key, value in result.items():
            print(f"   {key}: {value}")
        
        print(f"\n🎯 Next steps:")
        print(f"   1. Test ShareFilterButton in frontend UI")
        print(f"   2. Test public access at: /shared/filter/{result['share_token']}")
        print(f"   3. Verify end-to-end workflow functionality")