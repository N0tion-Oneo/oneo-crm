#!/usr/bin/env python3
"""
Debug Script: Field Slug vs Data Key Timeline Investigation
Investigates when and how field slugs became inconsistent with data keys
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = '1'

import django
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record
from django.utils.text import slugify

def analyze_slug_timeline():
    """Analyze when the field slug vs data key mismatch was introduced"""
    
    print("🔍 Field Slug vs Data Key Timeline Investigation")
    print("=" * 60)
    
    # Switch to OneOTalent tenant schema
    with schema_context('oneotalent'):
        # Get Sales Pipeline
        pipeline = Pipeline.objects.filter(name__icontains='sales').first()
        if not pipeline:
            print("❌ No Sales Pipeline found in OneOTalent tenant")
            return
            
        print(f"📊 Pipeline: {pipeline.name} (ID: {pipeline.id})")
        print(f"   Created: {pipeline.created_at}")
        print()
        
        # Get all fields ordered by creation time
        fields = pipeline.fields.all().order_by('created_at')
        print(f"🔧 Field Analysis ({fields.count()} fields):")
        print("   Creation Time | Field Name | Slug (Django) | Expected Data Key")
        print("   " + "-" * 80)
        
        field_analysis = []
        for field in fields:
            expected_data_key = field.name.lower().replace(' ', '_')  # How data keys should be
            actual_slug = field.slug  # What Django creates with slugify()
            
            field_analysis.append({
                'field': field,
                'expected_data_key': expected_data_key,
                'actual_slug': actual_slug,
                'matches': expected_data_key == actual_slug
            })
            
            print(f"   {field.created_at} | {field.name:12} | {actual_slug:13} | {expected_data_key}")
        
        print()
        
        # Check record data keys
        records = pipeline.records.filter(is_deleted=False).order_by('created_at')
        print(f"📝 Record Data Analysis ({records.count()} records):")
        
        if records.exists():
            # Sample first few records to understand data key format
            sample_records = records[:5]
            
            print("   Creation Time | Record ID | Data Keys Found")
            print("   " + "-" * 60)
            
            data_key_patterns = set()
            
            for record in sample_records:
                data_keys = list(record.data.keys()) if record.data else []
                data_key_patterns.update(data_keys)
                keys_str = ', '.join(data_keys) if data_keys else 'None'
                print(f"   {record.created_at} | {record.id:9} | {keys_str}")
            
            print()
            print("🔍 Analysis Results:")
            print("   " + "-" * 40)
            
            # Check if any field slugs match data keys
            matches_found = 0
            mismatches_found = 0
            
            print("   Field Slug vs Data Key Comparison:")
            for analysis in field_analysis:
                field_slug = analysis['actual_slug']
                expected_key = analysis['expected_data_key']
                
                # Check if any records have data for this field using either format
                slug_records = records.filter(data__has_key=field_slug).count()
                key_records = records.filter(data__has_key=expected_key).count()
                
                status = "❌"
                details = ""
                
                if slug_records > 0 and key_records == 0:
                    status = "✅ SLUG"
                    details = f"{slug_records} records use slug format"
                    matches_found += 1
                elif key_records > 0 and slug_records == 0:
                    status = "✅ KEY"  
                    details = f"{key_records} records use underscore format"
                    matches_found += 1
                elif slug_records > 0 and key_records > 0:
                    status = "⚠️ BOTH"
                    details = f"{slug_records} slug, {key_records} underscore"
                    mismatches_found += 1
                else:
                    status = "❌ NONE"
                    details = "No data found"
                    mismatches_found += 1
                
                print(f"     {analysis['field'].name:15} | {field_slug:15} vs {expected_key:15} | {status} {details}")
            
            print()
            print("📊 Summary:")
            print(f"   • Total fields: {len(field_analysis)}")
            print(f"   • Fields with matching data: {matches_found}")
            print(f"   • Fields with mismatched/no data: {mismatches_found}")
            
            # Show data key patterns found
            print()
            print("🔑 Data Key Patterns Found in Records:")
            for pattern in sorted(data_key_patterns):
                uses_hyphens = '-' in pattern
                uses_underscores = '_' in pattern
                format_type = "hyphens" if uses_hyphens else "underscores" if uses_underscores else "neither"
                print(f"   • '{pattern}' ({format_type})")
            
            # Conclusion
            print()
            print("🎯 Conclusion:")
            hyphen_keys = [k for k in data_key_patterns if '-' in k]
            underscore_keys = [k for k in data_key_patterns if '_' in k]
            
            if len(hyphen_keys) > 0 and len(underscore_keys) > 0:
                print("   ⚠️  Mixed format: Both hyphens and underscores found!")
                print("   🔧 This confirms the field slug vs data key mismatch")
            elif len(hyphen_keys) > 0:
                print("   🔧 Data keys use HYPHENS (match Django slugs)")  
                print("   ✅ No mismatch - data keys match field slugs")
            elif len(underscore_keys) > 0:
                print("   🔧 Data keys use UNDERSCORES (do NOT match Django slugs)")
                print("   ❌ MISMATCH CONFIRMED: Field slugs use hyphens, data uses underscores")
            else:
                print("   ❓ No clear pattern identified")
            
        else:
            print("   ❌ No records found to analyze")

if __name__ == '__main__':
    try:
        analyze_slug_timeline()
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()