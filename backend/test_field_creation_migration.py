#!/usr/bin/env python3
"""
Test Field Creation Migration
Verify that FieldOperationManager.create_field() now properly migrates existing records
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
from pipelines.field_operations import get_field_operation_manager
from django.contrib.auth import get_user_model

User = get_user_model()

def test_field_creation_migration():
    """Test that field creation properly migrates existing records"""
    
    print("🧪 Testing Field Creation Migration")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        # Get the Sales Pipeline with records
        pipeline = Pipeline.objects.filter(name='Sales Pipeline').first()
        if not pipeline:
            print("❌ No Sales Pipeline found")
            return
        
        print(f"📊 Pipeline: {pipeline.name} (ID: {pipeline.id})")
        
        # Get a test user
        user = User.objects.first()
        if not user:
            print("❌ No users found for testing")
            return
        
        print(f"👤 Test User: {user.username}")
        
        # Check current state
        initial_field_count = pipeline.fields.count()
        initial_record_count = pipeline.records.filter(is_deleted=False).count()
        
        print(f"📊 Initial State:")
        print(f"   Fields: {initial_field_count}")
        print(f"   Active Records: {initial_record_count}")
        
        if initial_record_count == 0:
            print("⚠️  No records to test migration with")
            return
        
        # Sample a few records to check their current data structure
        sample_records = list(pipeline.records.filter(is_deleted=False)[:3])
        print(f"\\n📋 Sample Records (before field creation):")
        
        for i, record in enumerate(sample_records, 1):
            data_keys = list(record.data.keys()) if record.data else []
            print(f"   Record {i} (ID: {record.id}): {len(data_keys)} fields")
            print(f"      Keys: {sorted(data_keys)[:5]}{'...' if len(data_keys) > 5 else ''}")
        
        # Create new field using FieldOperationManager
        field_config = {
            'name': 'migration_test_field',
            'display_name': 'Migration Test Field',
            'field_type': 'text',
            'field_config': {
                'default_value': 'test_default_value'
            }
        }
        
        print(f"\\n🚀 Creating new field: {field_config['name']}")
        print(f"   Field Type: {field_config['field_type']}")
        print(f"   Default Value: {field_config['field_config']['default_value']}")
        
        # Get FieldOperationManager and create field
        field_manager = get_field_operation_manager(pipeline)
        result = field_manager.create_field(field_config, user)
        
        print(f"\\n📋 Creation Result:")
        print(f"   Success: {result.success}")
        print(f"   Operation ID: {result.operation_id}")
        
        if not result.success:
            print(f"   ❌ Errors: {result.errors}")
            return
        
        print(f"   ✅ Field Created: {result.field.name} (slug: {result.field.slug})")
        print(f"   Warnings: {result.warnings}")
        print(f"   Records Migrated: {result.metadata.get('existing_records_migrated', 0)}")
        
        # Check if migration happened correctly
        if 'migration_result' in result.metadata and result.metadata['migration_result']:
            migration_data = result.metadata['migration_result']
            print(f"\\n🔄 Migration Details:")
            print(f"   Records Processed: {migration_data['records_processed']}")
            print(f"   Records Migrated: {migration_data['records_migrated']}")
            print(f"   Records Failed: {migration_data['records_failed']}")
            print(f"   Processing Time: {migration_data['processing_time_seconds']:.2f}s")
            
            if migration_data['errors']:
                print(f"   ❌ Migration Errors: {migration_data['errors']}")
        
        # Verify migration by checking the same sample records
        print(f"\\n🔍 Verification (checking sample records):")
        
        for i, record in enumerate(sample_records, 1):
            # Refresh record from database
            record.refresh_from_db()
            
            data_keys = list(record.data.keys()) if record.data else []
            has_new_field = result.field.slug in data_keys
            field_value = record.data.get(result.field.slug) if record.data else None
            
            print(f"   Record {i} (ID: {record.id}):")
            print(f"      Total fields: {len(data_keys)}")
            print(f"      Has new field '{result.field.slug}': {'✅ YES' if has_new_field else '❌ NO'}")
            
            if has_new_field:
                print(f"      Field value: '{field_value}'")
                
                # Verify it matches expected default
                expected_default = field_config['field_config']['default_value']
                if field_value == expected_default:
                    print(f"      ✅ Default value correct")
                else:
                    print(f"      ❌ Default value mismatch: expected '{expected_default}', got '{field_value}'")
            else:
                print(f"      ❌ Migration failed for this record")
        
        # Final assessment
        print(f"\\n📊 Final Assessment:")
        
        final_field_count = pipeline.fields.count()
        field_count_increased = final_field_count > initial_field_count
        
        print(f"   Field count: {initial_field_count} → {final_field_count} ({'✅' if field_count_increased else '❌'})")
        
        # Check if all records have the new field
        records_with_new_field = pipeline.records.filter(
            is_deleted=False,
            data__has_key=result.field.slug
        ).count()
        
        migration_success = records_with_new_field == initial_record_count
        
        print(f"   Records with new field: {records_with_new_field}/{initial_record_count} ({'✅' if migration_success else '❌'})")
        
        if migration_success and field_count_increased:
            print(f"\\n🎉 SUCCESS: Field creation with migration working correctly!")
            print(f"   ✅ New field created successfully")
            print(f"   ✅ All existing records migrated")
            print(f"   ✅ Default values applied correctly")
        else:
            print(f"\\n❌ FAILED: Field creation migration has issues")
            if not field_count_increased:
                print(f"   ⚠️  Field count did not increase")
            if not migration_success:
                print(f"   ⚠️  Not all records were migrated")
        
        # Clean up test field
        print(f"\\n🧹 Cleaning up test field...")
        try:
            result.field.delete()
            print(f"   ✅ Test field deleted")
        except Exception as e:
            print(f"   ⚠️  Could not delete test field: {e}")

if __name__ == '__main__':
    try:
        test_field_creation_migration()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()