#!/usr/bin/env python3
"""
Fix Consent Given Field Migration
Manually add the consent_given field to all existing records
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
from django.db import transaction

def fix_consent_migration():
    """Manually migrate consent_given field to all records"""
    
    print("🔧 Fixing 'Consent Given' Field Migration")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        # Get the Sales Pipeline
        pipeline = Pipeline.objects.filter(name='Sales Pipeline').first()
        if not pipeline:
            print("❌ Sales Pipeline not found")
            return
        
        # Get the consent field
        consent_field = pipeline.fields.filter(name='Consent Given').first()
        if not consent_field:
            print("❌ Consent Given field not found")
            return
        
        print(f"📊 Pipeline: {pipeline.name}")
        print(f"🔍 Field: '{consent_field.name}' (slug: '{consent_field.slug}')")
        
        # Get all records that don't have the consent field
        records_without_consent = pipeline.records.filter(
            is_deleted=False
        ).exclude(
            data__has_key=consent_field.slug
        )
        
        total_records = pipeline.records.filter(is_deleted=False).count()
        missing_count = records_without_consent.count()
        
        print(f"📊 Migration Status:")
        print(f"   Total records: {total_records}")
        print(f"   Records missing field: {missing_count}")
        
        if missing_count == 0:
            print("✅ All records already have the consent field!")
            return
        
        # Determine default value based on field type
        default_value = False  # Boolean field default
        
        print(f"🚀 Starting migration...")
        print(f"   Adding '{consent_field.slug}' = {default_value} to {missing_count} records")
        
        migrated_count = 0
        failed_count = 0
        
        with transaction.atomic():
            for record in records_without_consent:
                try:
                    # Initialize data dict if None
                    if record.data is None:
                        record.data = {}
                    
                    # Add the consent field
                    record.data[consent_field.slug] = default_value
                    
                    # Skip broadcasting during migration
                    record._skip_broadcast = True
                    record.save(update_fields=['data'])
                    
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Failed to migrate record {record.id}: {e}")
                    failed_count += 1
        
        print(f"\n📊 Migration Results:")
        print(f"   ✅ Successfully migrated: {migrated_count}")
        print(f"   ❌ Failed: {failed_count}")
        
        # Verify migration
        final_records_with_consent = pipeline.records.filter(
            is_deleted=False,
            data__has_key=consent_field.slug
        ).count()
        
        coverage = (final_records_with_consent / total_records) * 100 if total_records > 0 else 0
        
        print(f"\n🔍 Verification:")
        print(f"   Records with consent field: {final_records_with_consent}/{total_records}")
        print(f"   Coverage: {coverage:.1f}%")
        
        if final_records_with_consent == total_records:
            print(f"\n🎉 SUCCESS: All records now have the consent field!")
        else:
            print(f"\n⚠️  Some records still missing the field")
        
        # Show sample records
        print(f"\n📋 Sample Records (after migration):")
        sample_records = pipeline.records.filter(is_deleted=False)[:3]
        
        for i, record in enumerate(sample_records, 1):
            has_field = consent_field.slug in (record.data or {})
            field_value = record.data.get(consent_field.slug) if record.data and has_field else None
            
            print(f"   Record {i} (ID: {record.id}):")
            print(f"      Has consent field: {'✅ YES' if has_field else '❌ NO'}")
            if has_field:
                print(f"      Value: {repr(field_value)}")

if __name__ == '__main__':
    try:
        fix_consent_migration()
    except Exception as e:
        print(f"❌ Migration fix failed: {e}")
        import traceback
        traceback.print_exc()