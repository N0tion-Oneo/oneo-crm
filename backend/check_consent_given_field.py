#!/usr/bin/env python3
"""
Check Consent Given Field Migration
Verify that the newly created "consent given" field is present in all Sales Pipeline records
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django environment  
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = '1'

import django
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record

def check_consent_field_migration():
    """Check if consent given field was migrated to all records"""
    
    print("🔍 Checking 'Consent Given' Field Migration")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        # Get the Sales Pipeline
        pipeline = Pipeline.objects.filter(name='Sales Pipeline').first()
        if not pipeline:
            print("❌ Sales Pipeline not found")
            return
        
        print(f"📊 Pipeline: {pipeline.name} (ID: {pipeline.id})")
        
        # Look for the consent given field
        consent_field = None
        possible_names = ['consent given', 'consent_given', 'Consent Given']
        
        for name in possible_names:
            field = pipeline.fields.filter(name__icontains=name.replace('_', ' ')).first()
            if field:
                consent_field = field
                break
        
        if not consent_field:
            print("\n❌ 'Consent Given' field not found in pipeline")
            print("\n📋 Available fields in pipeline:")
            for field in pipeline.fields.order_by('created_at'):
                print(f"   - '{field.name}' (slug: '{field.slug}') - {field.field_type}")
            return
        
        print(f"\n✅ Found consent field:")
        print(f"   Name: '{consent_field.name}'")
        print(f"   Slug: '{consent_field.slug}'")  
        print(f"   Type: {consent_field.field_type}")
        print(f"   Created: {consent_field.created_at}")
        
        # Check if field slug uses underscores (our fix)
        has_hyphens = '-' in consent_field.slug
        has_underscores = '_' in consent_field.slug
        
        print(f"   Slug Format: {'❌ HYPHENS' if has_hyphens else '✅ UNDERSCORES' if has_underscores else '⚠️ SINGLE WORD'}")
        
        # Get all active records
        records = pipeline.records.filter(is_deleted=False)
        total_records = records.count()
        
        print(f"\n📊 Records Analysis:")
        print(f"   Total active records: {total_records}")
        
        if total_records == 0:
            print("   ⚠️  No records to check")
            return
        
        # Check how many records have the consent field
        records_with_consent = records.filter(data__has_key=consent_field.slug).count()
        
        print(f"   Records with consent field: {records_with_consent}")
        print(f"   Migration coverage: {records_with_consent}/{total_records} ({100 * records_with_consent / total_records:.1f}%)")
        
        # Sample individual records
        print(f"\n🔍 Individual Record Check:")
        
        for i, record in enumerate(records[:5], 1):  # Check first 5 records
            has_field = consent_field.slug in (record.data or {})
            field_value = record.data.get(consent_field.slug) if record.data and has_field else None
            
            print(f"   Record {i} (ID: {record.id}):")
            print(f"      Has consent field: {'✅ YES' if has_field else '❌ NO'}")
            
            if has_field:
                print(f"      Value: {repr(field_value)}")
            
            # Show total field count
            total_fields = len(record.data.keys()) if record.data else 0
            print(f"      Total fields: {total_fields}")
        
        # Final assessment
        print(f"\n📊 Final Assessment:")
        
        if records_with_consent == total_records:
            print(f"   🎉 SUCCESS: All records have the consent field!")
            print(f"   ✅ Migration system worked correctly")
            print(f"   ✅ Field creation triggered automatic record migration")
        elif records_with_consent > 0:
            print(f"   ⚠️  PARTIAL: Only {records_with_consent}/{total_records} records have the field")
            print(f"   🔧 Some records may need manual migration")
        else:
            print(f"   ❌ FAILED: No records have the consent field")
            print(f"   🚨 Migration system did not work as expected")
        
        # Check if this was a recent field (created after our fix)
        from django.utils import timezone
        from datetime import timedelta
        
        recent_threshold = timezone.now() - timedelta(hours=1)
        is_recent = consent_field.created_at > recent_threshold
        
        print(f"\n📅 Field Creation Timing:")
        print(f"   Created: {consent_field.created_at}")
        print(f"   Recent (last hour): {'✅ YES' if is_recent else '❌ NO'}")
        
        if is_recent and records_with_consent == total_records:
            print(f"   🎉 PERFECT: Recent field creation with full migration!")
        elif not is_recent and records_with_consent == total_records:
            print(f"   ℹ️  Field created before our fix, but migration is complete")

if __name__ == '__main__':
    try:
        check_consent_field_migration()
    except Exception as e:
        print(f"❌ Check failed with error: {e}")
        import traceback
        traceback.print_exc()