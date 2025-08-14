#!/usr/bin/env python3
"""
Test script for saved filter sharing workflow
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenants.models import Tenant
from pipelines.models import Pipeline, SavedFilter
from django_tenants.utils import schema_context
import json

User = get_user_model()

def test_sharing_workflow():
    """Test the complete sharing workflow"""
    
    print("🧪 Starting sharing workflow test...")
    
    # Get oneotalent tenant
    try:
        talent_tenant = Tenant.objects.get(schema_name='oneotalent')
        print(f"✅ Found oneotalent tenant: {talent_tenant.name}")
    except Tenant.DoesNotExist:
        print("❌ Oneotalent tenant not found")
        return
    
    with schema_context('oneotalent'):
        # Get or create a user
        user, created = User.objects.get_or_create(
            email='josh@oneodigital.com',
            defaults={
                'first_name': 'Josh',
                'last_name': 'Cowan',
                'username': 'josh@oneodigital.com'
            }
        )
        if created:
            user.set_password('admin123')
            user.save()
        print(f"✅ User ready: {user.email}")
        
        # Look for existing pipelines first (Talent/Sales)
        pipeline = None
        pipelines = Pipeline.objects.all()
        print(f"📋 Available pipelines ({pipelines.count()}):")
        for p in pipelines:
            print(f"   - {p.name} (ID: {p.id}, slug: {p.slug})")
        
        # Try to find talent-related pipeline with fields
        for pipeline_name in ['Job Applications', 'Sales CRM', 'Sales Pipeline', 'Content Calendar']:
            try:
                pipeline = Pipeline.objects.filter(name__icontains=pipeline_name.split()[0]).first()
                if pipeline:
                    fields_count = pipeline.fields.count()
                    print(f"✅ Found existing pipeline: {pipeline.name} ({fields_count} fields)")
                    if fields_count > 0:
                        break
                    pipeline = None  # Reset if no fields
            except Pipeline.DoesNotExist:
                continue
        
        if not pipeline:
            # Create a test pipeline with proper fields
            pipeline, created = Pipeline.objects.get_or_create(
                name='Test Pipeline',
                defaults={
                    'description': 'Test pipeline for sharing workflow',
                    'slug': 'test-pipeline',
                    'created_by': user
                }
            )
            print(f"✅ Created test pipeline: {pipeline.name}")
            
            # Create test fields with sharing permissions
            from pipelines.models import Field
            test_fields_data = [
                {
                    'name': 'Name',
                    'slug': 'name',
                    'field_type': 'text',
                    'is_visible_in_shared_list_and_detail_views': True
                },
                {
                    'name': 'Email',
                    'slug': 'email',
                    'field_type': 'email',
                    'is_visible_in_shared_list_and_detail_views': True
                },
                {
                    'name': 'Phone',
                    'slug': 'phone',
                    'field_type': 'phone',
                    'is_visible_in_shared_list_and_detail_views': False
                }
            ]
            
            for field_data in test_fields_data:
                field, created = Field.objects.get_or_create(
                    pipeline=pipeline,
                    slug=field_data['slug'],
                    defaults={
                        'name': field_data['name'],
                        'field_type': field_data['field_type'],
                        'is_visible_in_shared_list_and_detail_views': field_data['is_visible_in_shared_list_and_detail_views'],
                        'created_by': user
                    }
                )
                if created:
                    print(f"   ✅ Created field: {field.name} (shareable: {field.is_visible_in_shared_list_and_detail_views})")
        else:
            # Check existing fields and their sharing permissions
            fields = pipeline.fields.all()
            print(f"📋 Pipeline has {fields.count()} fields:")
            for field in fields[:5]:  # Show first 5 fields
                print(f"   - {field.name} ({field.slug}): shareable={field.is_visible_in_shared_list_and_detail_views}")
            
            # Enable sharing for some fields to test sharing functionality
            fields_to_enable = fields[:3]  # Enable first 3 fields for sharing
            for field in fields_to_enable:
                if not field.is_visible_in_shared_list_and_detail_views:
                    field.is_visible_in_shared_list_and_detail_views = True
                    field.save(update_fields=['is_visible_in_shared_list_and_detail_views'])
                    print(f"   ✅ Enabled sharing for: {field.name}")
            
        print(f"✅ Pipeline ready: {pipeline.name}")
        
        # Create a test filter
        test_filter_config = {
            "groups": [
                {
                    "id": "group-1",
                    "logic": "AND",
                    "filters": [
                        {
                            "field": "name",
                            "operator": "contains",
                            "value": "test",
                            "id": "filter-1"
                        }
                    ]
                }
            ],
            "groupLogic": "AND"
        }
        
        saved_filter, created = SavedFilter.objects.get_or_create(
            name='Test Shared Filter',
            pipeline=pipeline,
            created_by=user,
            defaults={
                'description': 'A test filter for sharing functionality',
                'filter_config': test_filter_config,
                'view_mode': 'table',
                'visible_fields': ['name', 'email'],
                'is_shareable': True,
                'share_access_level': 'readonly'
            }
        )
        
        if created:
            print(f"✅ Created new saved filter: {saved_filter.name}")
        else:
            print(f"✅ Using existing saved filter: {saved_filter.name}")
        
        # Test the sharing capabilities
        can_share, reason = saved_filter.can_be_shared()
        print(f"🔍 Can be shared: {can_share} - {reason}")
        
        # Get shareable fields
        shareable_fields = list(saved_filter.get_shareable_fields())
        print(f"📋 Shareable fields: {shareable_fields}")
        
        # Test API serialization
        from api.views.serializers import SavedFilterSerializer
        serializer = SavedFilterSerializer(saved_filter)
        serialized_data = serializer.data
        
        print(f"🔄 Serialized data keys: {list(serialized_data.keys())}")
        print(f"🔍 Filter config present: {'filter_config' in serialized_data}")
        print(f"🔍 Can share data: {serialized_data.get('can_share', {})}")
        
        # Test creating a share (without actually generating token)
        print(f"✅ Sharing workflow test completed successfully!")
        
        return {
            'tenant': talent_tenant.schema_name,
            'user_id': user.id,
            'pipeline_id': pipeline.id,
            'filter_id': str(saved_filter.id),
            'can_share': can_share,
            'shareable_fields': shareable_fields
        }

if __name__ == '__main__':
    result = test_sharing_workflow()
    if result:
        print(f"\n📊 Test Results:")
        for key, value in result.items():
            print(f"   {key}: {value}")