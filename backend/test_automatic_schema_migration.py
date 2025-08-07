"""
Comprehensive Test for Automatic Schema Migration System
Tests the complete flow from field creation through automatic migration
"""
import os
import django
import sys
import time
import json
from datetime import timedelta
from unittest.mock import patch, MagicMock

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django_tenants.utils import schema_context, tenant_context
from django.db import transaction
from django.contrib.auth import get_user_model
from celery import current_app

# Import project models and utilities
from tenants.models import Tenant, Domain, TenantMaintenance
from authentication.models import CustomUser
from pipelines.models import Pipeline, Field, Record
from pipelines.signals import analyze_field_changes, activate_maintenance_and_migrate
from pipelines.tasks import migrate_tenant_schema_automatically
from core.middleware import MaintenanceModeMiddleware
from django.test.client import RequestFactory

# User model already imported as CustomUser


class AutomaticSchemaMigrationTest(TransactionTestCase):
    """
    Test the complete automatic schema migration flow:
    1. Create tenant and pipeline
    2. Create field using field system
    3. Create records with that field
    4. Modify field to trigger migration
    5. Verify automatic migration occurs
    6. Verify all records are updated
    7. Verify AI system compatibility
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        print("\n" + "="*80)
        print("🧪 AUTOMATIC SCHEMA MIGRATION SYSTEM TEST")
        print("="*80)
    
    def setUp(self):
        """Setup test tenant and basic data"""
        print(f"\n📋 Setting up test environment...")
        
        # Create test tenant with timestamp to avoid conflicts
        import time
        timestamp = str(int(time.time()))
        self.tenant = Tenant.objects.create(
            schema_name=f'test_migration_{timestamp}',
            name=f'Test Migration Tenant {timestamp}'
        )
        
        # Create domain for tenant
        self.domain = Domain.objects.create(
            domain=f'test-migration-{timestamp}.localhost',
            tenant=self.tenant,
            is_primary=True
        )
        
        # Switch to tenant schema
        with schema_context(self.tenant.schema_name):
            # Create test user
            self.user = CustomUser.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            
            # Create test pipeline
            self.pipeline = Pipeline.objects.create(
                name='Test Migration Pipeline',
                description='Pipeline for testing automatic schema migration',
                created_by=self.user
            )
            
            print(f"✅ Created tenant: {self.tenant.name} ({self.tenant.schema_name})")
            print(f"✅ Created pipeline: {self.pipeline.name}")
    
    def test_complete_automatic_migration_flow(self):
        """Test the complete automatic schema migration flow"""
        
        with schema_context(self.tenant.schema_name):
            # Step 1: Create initial field using the field system
            print(f"\n🏗️  STEP 1: Creating initial field...")
            
            original_field = Field.objects.create(
                pipeline=self.pipeline,
                name='company_name',
                display_name='Company Name',
                field_type='text',
                field_config={
                    'case_sensitive': True,
                    'auto_format': False
                },
                storage_constraints={
                    'allow_null': True,
                    'max_storage_length': 200
                },
                business_rules={
                    'stage_requirements': {},
                    'conditional_requirements': []
                },
                created_by=self.user
            )
            
            print(f"✅ Created field: {original_field.name} (slug: {original_field.slug})")
            print(f"   Type: {original_field.field_type}")
            print(f"   Config: {original_field.field_config}")
            
            # Step 2: Create test records with the field
            print(f"\n📝 STEP 2: Creating test records...")
            
            test_records = []
            test_companies = [
                'Acme Corporation',
                'TechStart Inc',
                'Global Solutions Ltd',
                'Innovation Labs',
                'Future Systems'
            ]
            
            for i, company in enumerate(test_companies):
                record = Record.objects.create(
                    pipeline=self.pipeline,
                    title=f'Record {i+1}',
                    data={
                        original_field.slug: company,
                        'email': f'contact@{company.lower().replace(" ", "")}.com'
                    },
                    created_by=self.user,
                    updated_by=self.user
                )
                test_records.append(record)
                print(f"   ✅ Created record {record.id}: {company}")
            
            print(f"✅ Created {len(test_records)} test records")
            
            # Step 3: Verify initial state
            print(f"\n🔍 STEP 3: Verifying initial state...")
            
            # Check records have the field
            records_with_field = Record.objects.filter(
                pipeline=self.pipeline,
                data__has_key=original_field.slug
            ).count()
            
            print(f"✅ {records_with_field}/{len(test_records)} records have field '{original_field.slug}'")
            
            # Verify no maintenance mode initially
            maintenance_exists = TenantMaintenance.objects.filter(
                tenant=self.tenant,
                is_active=True
            ).exists()
            
            print(f"✅ Maintenance mode active: {maintenance_exists}")
            
            # Step 4: Test middleware blocking (should not block initially)
            print(f"\n🚪 STEP 4: Testing maintenance mode middleware...")
            
            middleware = MaintenanceModeMiddleware(lambda r: None)
            factory = RequestFactory()
            request = factory.get('/')
            request.tenant = self.tenant
            request.user = self.user
            
            should_block = middleware._should_block_request(request)
            print(f"✅ Middleware blocking: {should_block} (should be False)")
            
            # Step 5: Modify field to trigger automatic migration
            print(f"\n🔄 STEP 5: Modifying field to trigger automatic migration...")
            
            # We'll rename the field which should trigger a migration
            print(f"   Original slug: '{original_field.slug}'")
            print(f"   Changing name from '{original_field.name}' to 'organization_name'")
            
            # Mock the Celery task to prevent actual async execution in tests
            with patch('pipelines.tasks.migrate_tenant_schema_automatically.delay') as mock_task:
                # Modify the field - this should trigger the signals
                original_field.name = 'organization_name'  # This will change the slug
                original_field.display_name = 'Organization Name'
                original_field.save()
                
                # Verify the task was called
                print(f"✅ Migration task queued: {mock_task.called}")
                if mock_task.called:
                    call_args = mock_task.call_args[1]  # Get keyword arguments
                    print(f"   Tenant schema: {call_args.get('tenant_schema')}")
                    print(f"   Field ID: {call_args.get('field_id')}")
                    print(f"   Changes: {call_args.get('changes', {}).get('migration_types', [])}")
            
            # Step 6: Verify maintenance mode was activated
            print(f"\n🔒 STEP 6: Verifying maintenance mode activation...")
            
            try:
                maintenance = TenantMaintenance.objects.get(tenant=self.tenant)
                print(f"✅ Maintenance record created:")
                print(f"   Active: {maintenance.is_active}")
                print(f"   Reason: {maintenance.reason}")
                print(f"   Migration type: {maintenance.migration_type}")
                print(f"   Progress: {maintenance.progress_percentage}%")
                
                # Test middleware now blocks access
                should_block_now = middleware._should_block_request(request)
                print(f"✅ Middleware now blocking: {should_block_now}")
                
            except TenantMaintenance.DoesNotExist:
                print(f"❌ No maintenance record found!")
                return False
            
            # Step 7: Simulate the migration task execution
            print(f"\n⚙️  STEP 7: Simulating migration task execution...")
            
            # Get the change analysis that would have been generated
            field_refreshed = Field.objects.get(id=original_field.id)
            
            # The signal should have captured the original config
            if hasattr(field_refreshed, '_original_config'):
                print(f"✅ Original config captured in signals")
            else:
                print(f"ℹ️  Simulating original config for test")
                # Simulate what the original config would have been
                original_config = {
                    'name': 'company_name',
                    'slug': 'company_name',  # Original slug
                    'field_type': 'text',
                    'field_config': original_field.field_config,
                    'storage_constraints': original_field.storage_constraints,
                    'business_rules': original_field.business_rules,
                    'display_name': 'Company Name',
                    'is_deleted': False
                }
                field_refreshed._original_config = original_config
            
            # Analyze the changes
            changes = analyze_field_changes(field_refreshed._original_config, field_refreshed)
            print(f"✅ Change analysis:")
            print(f"   Requires migration: {changes['requires_migration']}")
            print(f"   Migration types: {changes['migration_types']}")
            print(f"   Risk level: {changes['risk_level']}")
            print(f"   Affected records: {changes['affected_records_estimate']}")
            
            # Step 8: Execute the actual migration (synchronously for testing)
            print(f"\n🚀 STEP 8: Executing schema migration...")
            
            # Mock Celery task execution
            result = migrate_tenant_schema_automatically(
                tenant_schema=self.tenant.schema_name,
                field_id=field_refreshed.id,
                changes=changes
            )
            
            print(f"✅ Migration result:")
            print(f"   Status: {result.get('status')}")
            if result.get('status') == 'completed':
                print(f"   Records migrated: {result.get('records_migrated', 0)}")
                print(f"   Processing time: {result.get('processing_time_minutes', 0)} minutes")
            elif result.get('status') in ['failed', 'critical_error']:
                print(f"   Error: {result.get('error')}")
            
            # Step 9: Verify migration results
            print(f"\n✅ STEP 9: Verifying migration results...")
            
            # Check that records now use the new field name
            old_field_count = Record.objects.filter(
                pipeline=self.pipeline,
                data__has_key='company_name'  # Old slug
            ).count()
            
            new_field_count = Record.objects.filter(
                pipeline=self.pipeline,
                data__has_key='organization_name'  # New slug
            ).count()
            
            print(f"✅ Records with old field name: {old_field_count}")
            print(f"✅ Records with new field name: {new_field_count}")
            print(f"✅ Migration success: {new_field_count == len(test_records) and old_field_count == 0}")
            
            # Verify data preservation
            migrated_records = Record.objects.filter(
                pipeline=self.pipeline,
                data__has_key='organization_name'
            )
            
            print(f"\n📊 Data preservation verification:")
            for record in migrated_records:
                original_company = None
                for company in test_companies:
                    if record.data.get('organization_name') == company:
                        original_company = company
                        break
                
                if original_company:
                    print(f"   ✅ Record {record.id}: '{original_company}' preserved")
                else:
                    print(f"   ❌ Record {record.id}: Data not preserved correctly")
            
            # Step 10: Test AI system compatibility
            print(f"\n🤖 STEP 10: Testing AI system compatibility...")
            
            # Simulate AI job trying to save to the field
            test_ai_job = {
                'field_name': 'organization_name',  # Should match new field name
                'generated_content': 'AI Generated Company Name'
            }
            
            # Test field name resolution (from ai/tasks.py logic)
            field_found = False
            target_field_name = None
            
            test_record = migrated_records.first()
            if test_record:
                # Test exact match (should work now)
                if test_ai_job['field_name'] in test_record.data:
                    target_field_name = test_ai_job['field_name']
                    field_found = True
                
                print(f"✅ AI field resolution:")
                print(f"   Field name: '{test_ai_job['field_name']}'")
                print(f"   Found in record: {field_found}")
                print(f"   Target field: '{target_field_name}'")
                
                if field_found:
                    print(f"✅ AI field save would succeed!")
                else:
                    print(f"❌ AI field save would fail!")
            
            # Step 11: Verify maintenance mode deactivation
            print(f"\n🔓 STEP 11: Verifying maintenance mode deactivation...")
            
            maintenance.refresh_from_db()
            print(f"✅ Maintenance mode active: {maintenance.is_active}")
            print(f"✅ Completion status: {maintenance.status_message}")
            print(f"✅ Final progress: {maintenance.progress_percentage}%")
            
            if maintenance.completed_at:
                duration = (maintenance.completed_at - maintenance.started_at).total_seconds()
                print(f"✅ Migration duration: {duration} seconds")
            
            # Final verification - middleware should not block anymore
            should_block_final = middleware._should_block_request(request)
            print(f"✅ Middleware blocking after migration: {should_block_final}")
            
            # Step 12: Summary
            print(f"\n📊 MIGRATION TEST SUMMARY:")
            print(f"="*50)
            
            success_criteria = [
                (changes['requires_migration'], "Migration was triggered"),
                (result.get('status') == 'completed', "Migration completed successfully"),
                (new_field_count == len(test_records), "All records migrated"),
                (old_field_count == 0, "No old field names remain"),
                (field_found, "AI system compatibility restored"),
                (not maintenance.is_active, "Maintenance mode deactivated"),
            ]
            
            passed = 0
            for condition, description in success_criteria:
                status = "✅ PASS" if condition else "❌ FAIL"
                print(f"   {status}: {description}")
                if condition:
                    passed += 1
            
            overall_success = passed == len(success_criteria)
            print(f"\n🎯 OVERALL RESULT: {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")
            print(f"   Passed: {passed}/{len(success_criteria)} criteria")
            
            return overall_success
    
    def tearDown(self):
        """Clean up test data"""
        try:
            # Clean up tenant
            self.tenant.delete()
            print(f"✅ Cleaned up test tenant")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


def run_test():
    """Run the automatic schema migration test"""
    print(f"🚀 Starting Automatic Schema Migration Test...")
    print(f"Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create and run the test
    test = AutomaticSchemaMigrationTest()
    test.setUp()
    
    try:
        success = test.test_complete_automatic_migration_flow()
        
        print(f"\n" + "="*80)
        if success:
            print(f"🎉 AUTOMATIC SCHEMA MIGRATION TEST: PASSED")
            print(f"   ✅ All components working correctly")
            print(f"   ✅ AI field save issue resolved")
            print(f"   ✅ System ready for production")
        else:
            print(f"❌ AUTOMATIC SCHEMA MIGRATION TEST: FAILED")
            print(f"   ⚠️  Some components need attention")
        print(f"="*80)
        
        return success
        
    finally:
        test.tearDown()


if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)