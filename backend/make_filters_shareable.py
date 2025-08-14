#!/usr/bin/env python3
"""
Make existing saved filters shareable
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenants.models import Tenant
from pipelines.models import SavedFilter
from django_tenants.utils import schema_context

User = get_user_model()

def make_filters_shareable():
    """Make existing filters shareable and check their status"""
    
    print("🔧 Making saved filters shareable...")
    
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
        
        # Get all saved filters for this user
        filters = SavedFilter.objects.filter(created_by=user)
        print(f"📋 Found {filters.count()} saved filters")
        
        for filter_obj in filters:
            print(f"\n🔍 Processing filter: {filter_obj.name}")
            print(f"   Pipeline: {filter_obj.pipeline.name}")
            print(f"   Currently shareable: {filter_obj.is_shareable}")
            
            # Update filter to be shareable if it has shareable fields
            shareable_fields = list(filter_obj.get_shareable_fields())
            
            if shareable_fields:
                if not filter_obj.is_shareable:
                    filter_obj.is_shareable = True
                    filter_obj.save(update_fields=['is_shareable'])
                    print(f"   ✅ Made shareable!")
                else:
                    print(f"   ✅ Already shareable!")
                
                # Test sharing capability
                can_share, reason = filter_obj.can_be_shared()
                print(f"   Can be shared: {can_share} - {reason}")
                print(f"   Shareable fields ({len(shareable_fields)}): {shareable_fields}")
                
                # Show visible fields for debugging
                print(f"   Visible fields: {filter_obj.visible_fields}")
                
            else:
                print(f"   ⚠️ No shareable fields available")
                print(f"   Visible fields: {filter_obj.visible_fields}")
                
                # Check if visible fields are in pipeline
                pipeline_field_slugs = list(filter_obj.pipeline.fields.values_list('slug', flat=True))
                print(f"   Available pipeline fields: {pipeline_field_slugs[:10]}")  # Show first 10

if __name__ == '__main__':
    make_filters_shareable()