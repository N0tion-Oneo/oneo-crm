#!/usr/bin/env python3
"""
Verification Script: Test Field Slug Fix
Verify that field slugs now match data keys and data is visible
"""

import os
import sys
import json

# Add the parent directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django environment  
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = '1'

import django
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record

def verify_field_slug_fix():
    """Verify that the field slug fix worked"""
    
    print("🔍 Verifying Field Slug Fix")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        # Get Sales Pipeline
        pipeline = Pipeline.objects.filter(name__icontains='sales').first()
        if not pipeline:
            print("❌ No Sales Pipeline found")
            return
        
        print(f"📊 Pipeline: {pipeline.name} (ID: {pipeline.id})")
        
        # Get all fields and a sample record
        fields = pipeline.fields.all().order_by('display_order')
        sample_record = pipeline.records.filter(is_deleted=False).first()
        
        if not sample_record:
            print("❌ No sample record found for testing")
            return
        
        print(f"🧪 Testing with Record ID: {sample_record.id}")
        print(f"📦 Record data keys: {list(sample_record.data.keys()) if sample_record.data else []}")
        print()
        
        # Test each field
        visible_fields = 0
        total_fields = fields.count()
        
        print("🔍 Field Slug → Data Key Matching Test:")
        print("   Field Name           | Field Slug           | Has Data | Status")
        print("   " + "-" * 70)
        
        for field in fields:
            field_slug = field.slug
            has_data = field_slug in (sample_record.data or {})
            data_value = sample_record.data.get(field_slug) if sample_record.data else None
            
            if has_data:
                visible_fields += 1
                status = "✅ VISIBLE"
                # Truncate long values for display
                if isinstance(data_value, str) and len(data_value) > 20:
                    display_value = data_value[:17] + "..."
                else:
                    display_value = str(data_value)
            else:
                status = "❌ NO DATA"
                display_value = "None"
            
            print(f"   {field.name:20} | {field_slug:20} | {display_value:8} | {status}")
        
        print()
        print("📊 RESULTS SUMMARY:")
        print(f"   Total Fields: {total_fields}")
        print(f"   Visible Fields: {visible_fields}")
        print(f"   Hidden Fields: {total_fields - visible_fields}")
        print(f"   Success Rate: {(visible_fields / total_fields * 100):.1f}%")
        
        if visible_fields >= total_fields * 0.8:  # 80% success rate
            print("🎉 SUCCESS: Field slug fix is working! Data is now visible.")
        elif visible_fields >= total_fields * 0.5:  # 50% success rate
            print("⚠️  PARTIAL SUCCESS: Some fields are now visible, but issues remain.")
        else:
            print("❌ FAILED: Most fields are still not visible.")
        
        # Additional diagnostics
        print()
        print("🔧 DIAGNOSTICS:")
        
        # Check if any field slugs still have hyphens
        hyphen_fields = fields.filter(slug__contains='-')
        if hyphen_fields.exists():
            print(f"   ⚠️  {hyphen_fields.count()} fields still have hyphens in slugs:")
            for field in hyphen_fields:
                print(f"      - {field.name}: '{field.slug}'")
        else:
            print("   ✅ All field slugs use underscores (no hyphens found)")
        
        # Check data key formats
        data_keys = list(sample_record.data.keys()) if sample_record.data else []
        hyphen_data_keys = [key for key in data_keys if '-' in key]
        underscore_data_keys = [key for key in data_keys if '_' in key]
        
        print(f"   Data keys with hyphens: {len(hyphen_data_keys)} ({hyphen_data_keys[:3]}...)")
        print(f"   Data keys with underscores: {len(underscore_data_keys)} ({underscore_data_keys[:3]}...)")
        
        # Show improvement
        print()
        print("📈 IMPROVEMENT METRICS:")
        print("   Before fix: 6/17 fields visible (35.3%)")
        print(f"   After fix:  {visible_fields}/{total_fields} fields visible ({(visible_fields / total_fields * 100):.1f}%)")
        improvement = (visible_fields / total_fields * 100) - 35.3
        print(f"   Improvement: {improvement:+.1f} percentage points")

if __name__ == '__main__':
    try:
        verify_field_slug_fix()
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()