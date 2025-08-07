#!/usr/bin/env python3
"""
Real-time Monitoring: New Field Creation Test
Monitor the creation of "new field" in Sales Pipeline to verify slug consistency
"""

import os
import sys
import time
import json

# Add the parent directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django environment  
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = '1'

import django
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record, field_slugify

def monitor_field_creation():
    """Monitor field creation and verify slug consistency"""
    
    print("🔍 Monitoring New Field Creation")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        # Get Sales Pipeline
        pipeline = Pipeline.objects.filter(name__icontains='sales').first()
        if not pipeline:
            print("❌ No Sales Pipeline found")
            return
        
        print(f"📊 Pipeline: {pipeline.name} (ID: {pipeline.id})")
        print(f"🕐 Waiting for 'new field' to be created...")
        print()
        
        # Get initial state
        initial_field_count = pipeline.fields.count()
        print(f"📊 Initial field count: {initial_field_count}")
        
        # Check if the field already exists
        existing_new_field = pipeline.fields.filter(name__icontains='new field').first()
        if existing_new_field:
            print(f"⚠️  'new field' already exists: {existing_new_field.name} (slug: {existing_new_field.slug})")
            return
        
        # Monitor for new field creation
        max_wait_seconds = 300  # 5 minutes
        check_interval = 2      # Check every 2 seconds
        checks_made = 0
        
        while checks_made < (max_wait_seconds / check_interval):
            time.sleep(check_interval)
            checks_made += 1
            
            # Refresh pipeline and check for new fields
            current_field_count = pipeline.fields.count()
            
            if current_field_count > initial_field_count:
                print(f"🎉 New field detected! Field count: {initial_field_count} → {current_field_count}")
                
                # Find the new field(s)
                new_fields = pipeline.fields.order_by('-created_at')[:current_field_count - initial_field_count]
                
                for new_field in new_fields:
                    print(f"\n🔍 Analyzing new field:")
                    print(f"   Field Name: '{new_field.name}'")
                    print(f"   Field Slug: '{new_field.slug}'")
                    print(f"   Created At: {new_field.created_at}")
                    print(f"   Field Type: {new_field.field_type}")
                    
                    # Check if this is our target field
                    if 'new field' in new_field.name.lower():
                        print(f"\n✅ Found target field: '{new_field.name}'")
                        
                        # Verify slug format
                        expected_slug = field_slugify(new_field.name)
                        actual_slug = new_field.slug
                        
                        print(f"   Expected slug: '{expected_slug}'")
                        print(f"   Actual slug: '{actual_slug}'")
                        print(f"   Match: {'✅ YES' if expected_slug == actual_slug else '❌ NO'}")
                        
                        # Check slug format
                        has_hyphens = '-' in actual_slug
                        has_underscores = '_' in actual_slug
                        
                        if has_hyphens:
                            print("   Format: ❌ USES HYPHENS (PROBLEM!)")
                        elif has_underscores:
                            print("   Format: ✅ USES UNDERSCORES (CORRECT)")
                        else:
                            print("   Format: ⚠️  SINGLE WORD (NO SEPARATORS)")
                        
                        # Test record data consistency
                        print(f"\n🧪 Testing Record Data Consistency:")
                        sample_records = pipeline.records.filter(is_deleted=False)[:3]
                        
                        if sample_records.exists():
                            print(f"   Testing with {sample_records.count()} sample records:")
                            
                            for i, record in enumerate(sample_records, 1):
                                data_keys = list(record.data.keys()) if record.data else []
                                has_new_field_data = actual_slug in data_keys
                                
                                print(f"     Record {i} (ID: {record.id}):")
                                print(f"       Data keys: {len(data_keys)} total")
                                print(f"       Has '{actual_slug}' key: {'✅ YES' if has_new_field_data else '❌ NO'}")
                                
                                if has_new_field_data:
                                    value = record.data.get(actual_slug)
                                    print(f"       Value: {value}")
                        else:
                            print("   ❓ No sample records found for testing")
                        
                        # Overall assessment
                        print(f"\n📊 ASSESSMENT:")
                        if expected_slug == actual_slug and not has_hyphens:
                            print("   🎉 SUCCESS: Field slug uses underscores as expected!")
                            print("   ✅ Our fix is working correctly")
                        else:
                            print("   ❌ FAILED: Field slug format is incorrect")
                            print("   ⚠️  Our fix may not be working properly")
                        
                        return  # Found our target field, exit monitoring
                
            # Show progress
            if checks_made % 15 == 0:  # Every 30 seconds
                print(f"   Still monitoring... ({checks_made * check_interval}s elapsed)")
        
        print(f"\n⏰ Monitoring timeout ({max_wait_seconds}s)")
        print("   No new field named 'new field' was detected")
        print("   Please ensure the field is being created in the correct pipeline")

if __name__ == '__main__':
    try:
        monitor_field_creation()
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Monitoring stopped by user")
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        import traceback
        traceback.print_exc()