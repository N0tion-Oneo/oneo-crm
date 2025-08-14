#!/usr/bin/env python3
"""
Make ALL saved filters shareable by default and ensure proper field configuration
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenants.models import Tenant
from pipelines.models import SavedFilter, Field, Pipeline
from django_tenants.utils import schema_context

User = get_user_model()

def make_all_filters_shareable():
    """Make ALL saved filters shareable and ensure fields are configured for sharing"""
    
    print("🔧 Making ALL saved filters shareable...")
    
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
        
        # First, let's enable sharing for ALL pipeline fields that are appropriate for sharing
        print("\n🔧 Enabling sharing for pipeline fields...")
        
        all_pipelines = Pipeline.objects.all()
        for pipeline in all_pipelines:
            print(f"\n📋 Pipeline: {pipeline.name} ({pipeline.fields.count()} fields)")
            
            # Enable sharing for non-sensitive fields
            non_sensitive_field_types = [
                'text', 'textarea', 'number', 'decimal', 'date', 'datetime',
                'select', 'boolean', 'url', 'tags', 'ai_generated'
            ]
            
            fields_to_enable = pipeline.fields.filter(
                field_type__in=non_sensitive_field_types,
                is_visible_in_shared_list_and_detail_views=False
            )
            
            enabled_count = 0
            for field in fields_to_enable:
                # Skip sensitive fields based on name
                sensitive_keywords = ['password', 'secret', 'private', 'confidential', 'ssn', 'social']
                field_name_lower = field.name.lower()
                
                if not any(keyword in field_name_lower for keyword in sensitive_keywords):
                    field.is_visible_in_shared_list_and_detail_views = True
                    field.save(update_fields=['is_visible_in_shared_list_and_detail_views'])
                    enabled_count += 1
                    print(f"   ✅ Enabled sharing: {field.name} ({field.field_type})")
            
            print(f"   📊 Enabled sharing for {enabled_count} fields in {pipeline.name}")
        
        # Now make ALL saved filters shareable
        print("\n🔧 Making all saved filters shareable...")
        
        all_filters = SavedFilter.objects.filter(created_by=user)
        print(f"📋 Found {all_filters.count()} saved filters")
        
        updated_count = 0
        for filter_obj in all_filters:
            print(f"\n🔍 Processing filter: {filter_obj.name}")
            print(f"   Pipeline: {filter_obj.pipeline.name}")
            
            # Always make it shareable
            if not filter_obj.is_shareable:
                filter_obj.is_shareable = True
                filter_obj.save(update_fields=['is_shareable'])
                updated_count += 1
                print(f"   ✅ Made shareable!")
            else:
                print(f"   ✅ Already shareable!")
            
            # Test sharing capability
            can_share, reason = filter_obj.can_be_shared()
            shareable_fields = list(filter_obj.get_shareable_fields())
            
            print(f"   Can be shared: {can_share} - {reason}")
            print(f"   Shareable fields ({len(shareable_fields)}): {shareable_fields[:5]}{'...' if len(shareable_fields) > 5 else ''}")
            
            # If it still can't be shared, update visible fields to include only shareable ones
            if not can_share:
                pipeline_shareable_fields = list(filter_obj.pipeline.fields.filter(
                    is_visible_in_shared_list_and_detail_views=True
                ).values_list('slug', flat=True))
                
                if pipeline_shareable_fields:
                    filter_obj.visible_fields = pipeline_shareable_fields[:10]  # Take first 10
                    filter_obj.save(update_fields=['visible_fields'])
                    print(f"   🔄 Updated visible fields to: {filter_obj.visible_fields}")
                    
                    # Re-check
                    can_share, reason = filter_obj.can_be_shared()
                    print(f"   Updated status: {can_share} - {reason}")
        
        print(f"\n📊 Summary:")
        print(f"   - Updated {updated_count} filters to be shareable")
        print(f"   - All {all_filters.count()} filters are now marked as shareable")
        
        # Final verification
        print(f"\n🔍 Final verification:")
        shareable_filters = all_filters.filter(is_shareable=True)
        actually_shareable = []
        
        for filter_obj in shareable_filters:
            can_share, reason = filter_obj.can_be_shared()
            if can_share:
                actually_shareable.append(filter_obj)
                print(f"   ✅ {filter_obj.name}: Ready for sharing")
            else:
                print(f"   ⚠️ {filter_obj.name}: {reason}")
        
        print(f"\n🎯 Result: {len(actually_shareable)}/{all_filters.count()} filters are fully ready for sharing!")

if __name__ == '__main__':
    make_all_filters_shareable()