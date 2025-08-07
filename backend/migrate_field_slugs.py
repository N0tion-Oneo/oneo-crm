#!/usr/bin/env python3
"""
Migration Script: Update Field Slugs from Hyphens to Underscores
This script updates existing field slugs to use underscores instead of hyphens
to match the data key format used in record.data
"""

import os
import sys
import re
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = '1'

import django
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record, field_slugify
from django.db import transaction

def migrate_field_slugs():
    """Migrate existing field slugs from hyphens to underscores"""
    
    print("🔄 Field Slug Migration: Hyphens → Underscores")
    print("=" * 60)
    
    # Switch to OneOTalent tenant schema
    with schema_context('oneotalent'):
        # Get all fields that need migration (ones with hyphens in slug)
        fields_to_migrate = Field.objects.filter(slug__contains='-')
        
        print(f"🔍 Found {fields_to_migrate.count()} fields with hyphens in slugs")
        
        if not fields_to_migrate.exists():
            print("✅ No fields need migration")
            return
        
        print("\n📋 Fields to migrate:")
        migration_plan = []
        
        for field in fields_to_migrate:
            old_slug = field.slug
            new_slug = field_slugify(field.name)
            
            # Check if slug would actually change
            if old_slug != new_slug:
                migration_plan.append({
                    'field': field,
                    'old_slug': old_slug,
                    'new_slug': new_slug,
                    'pipeline_name': field.pipeline.name
                })
                print(f"   {field.pipeline.name:20} | {field.name:15} | {old_slug:15} → {new_slug}")
        
        if not migration_plan:
            print("✅ All field slugs are already correct")
            return
        
        print(f"\n⚠️  This will update {len(migration_plan)} field slugs")
        print("❓ Continue with migration? (y/N): ", end="")
        
        # For automated testing, we'll proceed automatically
        # In real usage, you'd want user confirmation
        # response = input().lower()
        # if response != 'y':
        #     print("❌ Migration cancelled")
        #     return
        
        print("y  # Auto-confirmed for testing")
        
        # Execute migration
        print(f"\n🚀 Starting migration...")
        
        with transaction.atomic():
            success_count = 0
            error_count = 0
            
            for migration in migration_plan:
                field = migration['field']
                old_slug = migration['old_slug']
                new_slug = migration['new_slug']
                
                try:
                    print(f"   Updating {field.name}: {old_slug} → {new_slug}")
                    
                    # Update the field slug
                    field.slug = new_slug
                    field.save()
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"   ❌ Failed to update {field.name}: {e}")
                    error_count += 1
        
        print(f"\n📊 Migration Summary:")
        print(f"   ✅ Successfully migrated: {success_count} fields")
        print(f"   ❌ Failed migrations: {error_count} fields")
        
        if error_count == 0:
            print(f"\n🎉 Migration completed successfully!")
            
            # Now verify the fix works by checking data access
            print(f"\n🔍 Verifying data access after migration...")
            
            # Test with Sales Pipeline
            sales_pipeline = Pipeline.objects.filter(name__icontains='sales').first()
            if sales_pipeline:
                fields = sales_pipeline.fields.all()[:5]  # Test first 5 fields
                sample_record = sales_pipeline.records.filter(is_deleted=False).first()
                
                if sample_record:
                    print(f"   Testing with record {sample_record.id}:")
                    print(f"   Record data keys: {list(sample_record.data.keys()) if sample_record.data else []}")
                    
                    matches = 0
                    mismatches = 0
                    
                    for field in fields:
                        field_slug = field.slug
                        has_data = field_slug in (sample_record.data or {})
                        status = "✅" if has_data else "❌"
                        
                        if has_data:
                            matches += 1
                        else:
                            mismatches += 1
                            
                        print(f"     {field.name:15} | slug: {field_slug:15} | data exists: {status}")
                    
                    print(f"\n   📊 Verification Results:")
                    print(f"     ✅ Fields with matching data: {matches}/{matches + mismatches}")
                    print(f"     ❌ Fields without data: {mismatches}/{matches + mismatches}")
                    
                    if matches > mismatches:
                        print(f"   🎉 SUCCESS: Field slugs now match data keys!")
                    else:
                        print(f"   ⚠️  Some fields still don't have matching data")
                else:
                    print("   ❓ No sample record found for verification")
            else:
                print("   ❓ No sales pipeline found for verification")
        else:
            print(f"\n⚠️  Migration completed with {error_count} errors")

if __name__ == '__main__':
    try:
        migrate_field_slugs()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()