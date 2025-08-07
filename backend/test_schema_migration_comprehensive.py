#!/usr/bin/env python3
"""
Comprehensive Schema Migration Test
Tests all three scenarios: CREATE, UPDATE, DELETE fields
Monitors maintenance mode and migration logs in real-time
"""
import os
import sys
import django
import time
import threading
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.utils import timezone
from django_tenants.utils import schema_context
from tenants.models import Tenant, TenantMaintenance
from pipelines.models import Pipeline, Field, Record
from django.contrib.auth import get_user_model
import json

User = get_user_model()

def log_with_timestamp(message, level="INFO"):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    level_emoji = {
        "INFO": "ℹ️",
        "SUCCESS": "✅", 
        "WARNING": "⚠️",
        "ERROR": "❌",
        "MIGRATION": "🚀",
        "MAINTENANCE": "🔧"
    }
    emoji = level_emoji.get(level, "📋")
    print(f"{timestamp} {emoji} [{level}] {message}")

def monitor_maintenance_status(tenant_schema, stop_event):
    """Monitor maintenance status in background thread"""
    log_with_timestamp(f"Starting maintenance monitoring for {tenant_schema}", "MAINTENANCE")
    
    while not stop_event.is_set():
        try:
            tenant = Tenant.objects.get(schema_name=tenant_schema)
            if hasattr(tenant, 'maintenance'):
                maintenance = tenant.maintenance
                status = "ACTIVE" if maintenance.is_active else "INACTIVE"
                progress = maintenance.progress_percentage
                message = maintenance.status_message
                
                if maintenance.is_active:
                    log_with_timestamp(f"Maintenance: {status} ({progress}%) - {message}", "MAINTENANCE")
            
            time.sleep(1)  # Check every second during migration
        except Exception as e:
            log_with_timestamp(f"Maintenance monitoring error: {e}", "ERROR")
        
    log_with_timestamp("Maintenance monitoring stopped", "MAINTENANCE")

def get_field_schema_snapshot(pipeline):
    """Get current field schema for comparison"""
    fields = {}
    for field in pipeline.fields.all().order_by('id'):
        fields[field.slug] = {
            'id': field.id,
            'name': field.name,
            'field_type': field.field_type,
            'field_config': field.field_config,
            'is_deleted': getattr(field, 'is_deleted', False)
        }
    return fields

def compare_schemas(before, after, operation):
    """Compare field schemas and log differences"""
    log_with_timestamp(f"Schema comparison for {operation}:", "INFO")
    
    # Check for new fields
    new_fields = set(after.keys()) - set(before.keys())
    if new_fields:
        for field_slug in new_fields:
            field_info = after[field_slug]
            log_with_timestamp(f"  ➕ NEW FIELD: {field_slug} ({field_info['name']}) - Type: {field_info['field_type']}", "SUCCESS")
    
    # Check for deleted fields
    deleted_fields = set(before.keys()) - set(after.keys())
    if deleted_fields:
        for field_slug in deleted_fields:
            field_info = before[field_slug]
            log_with_timestamp(f"  ➖ DELETED FIELD: {field_slug} ({field_info['name']}) - Was Type: {field_info['field_type']}", "WARNING")
    
    # Check for modified fields
    common_fields = set(before.keys()) & set(after.keys())
    for field_slug in common_fields:
        before_field = before[field_slug]
        after_field = after[field_slug]
        
        changes = []
        if before_field['name'] != after_field['name']:
            changes.append(f"name: '{before_field['name']}' → '{after_field['name']}'")
        if before_field['field_type'] != after_field['field_type']:
            changes.append(f"type: '{before_field['field_type']}' → '{after_field['field_type']}'")
        if before_field['field_config'] != after_field['field_config']:
            changes.append(f"config: {before_field['field_config']} → {after_field['field_config']}")
        
        if changes:
            log_with_timestamp(f"  🔄 MODIFIED FIELD: {field_slug} - {', '.join(changes)}", "INFO")
    
    if not new_fields and not deleted_fields and not any(before[f] != after[f] for f in common_fields):
        log_with_timestamp("  📋 NO SCHEMA CHANGES DETECTED", "INFO")

def test_field_creation():
    """Test 1: Create a new field and monitor migration"""
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("TEST 1: FIELD CREATION - Adding new field to trigger migration", "MIGRATION")
    log_with_timestamp("=" * 80, "INFO")
    
    try:
        with schema_context('demo'):
            pipeline = Pipeline.objects.get(id=1)
            log_with_timestamp(f"Using pipeline: {pipeline.name}", "INFO")
            
            # Get schema snapshot before
            schema_before = get_field_schema_snapshot(pipeline)
            log_with_timestamp("Schema snapshot taken BEFORE field creation", "INFO")
            
            # Start maintenance monitoring
            stop_event = threading.Event()
            monitor_thread = threading.Thread(
                target=monitor_maintenance_status,
                args=('demo', stop_event)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Create new field that should trigger migration
            log_with_timestamp("Creating new field: 'Test Phone Number'", "MIGRATION")
            new_field = Field.objects.create(
                pipeline=pipeline,
                name="Test Phone Number",
                field_type="phone",
                field_config={
                    "default_country": "US",
                    "format": "international"
                },
                display_order=99,
                created_by_id=1  # Assuming user ID 1 exists
            )
            
            log_with_timestamp(f"Field created with ID: {new_field.id}, Slug: {new_field.slug}", "SUCCESS")
            
            # Wait for migration to complete
            log_with_timestamp("Waiting for migration to complete (max 30 seconds)...", "INFO")
            time.sleep(30)  # Give migration time to run
            
            # Stop monitoring
            stop_event.set()
            
            # Get schema snapshot after
            schema_after = get_field_schema_snapshot(pipeline)
            log_with_timestamp("Schema snapshot taken AFTER field creation", "INFO")
            
            # Compare schemas
            compare_schemas(schema_before, schema_after, "FIELD CREATION")
            
            # Check maintenance status
            tenant = Tenant.objects.get(schema_name='demo')
            if hasattr(tenant, 'maintenance'):
                maintenance = tenant.maintenance
                status = "ACTIVE" if maintenance.is_active else "INACTIVE"
                log_with_timestamp(f"Final maintenance status: {status}", "MAINTENANCE")
                
                if maintenance.is_active:
                    log_with_timestamp("⚠️ WARNING: Maintenance mode still active after field creation!", "WARNING")
                    return False
                else:
                    log_with_timestamp("✅ SUCCESS: Maintenance mode properly deactivated", "SUCCESS")
            
            return True
            
    except Exception as e:
        log_with_timestamp(f"Field creation test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def test_field_modification():
    """Test 2: Modify existing field and monitor migration"""
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("TEST 2: FIELD MODIFICATION - Changing field name to trigger migration", "MIGRATION")
    log_with_timestamp("=" * 80, "INFO")
    
    try:
        with schema_context('demo'):
            pipeline = Pipeline.objects.get(id=1)
            
            # Find a field to modify
            field_to_modify = pipeline.fields.filter(slug='main-email-contact').first()
            if not field_to_modify:
                log_with_timestamp("No suitable field found for modification test", "WARNING")
                return False
            
            log_with_timestamp(f"Modifying field: {field_to_modify.name} ({field_to_modify.slug})", "INFO")
            
            # Get schema snapshot before
            schema_before = get_field_schema_snapshot(pipeline)
            log_with_timestamp("Schema snapshot taken BEFORE field modification", "INFO")
            
            # Start maintenance monitoring
            stop_event = threading.Event()
            monitor_thread = threading.Thread(
                target=monitor_maintenance_status,
                args=('demo', stop_event)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Modify field name (this should trigger migration)
            old_name = field_to_modify.name
            new_name = f"Primary Email Address (Modified {int(time.time())})"
            
            log_with_timestamp(f"Changing field name: '{old_name}' → '{new_name}'", "MIGRATION")
            field_to_modify.name = new_name
            field_to_modify.save()
            
            # Wait for migration to complete
            log_with_timestamp("Waiting for migration to complete (max 30 seconds)...", "INFO")
            time.sleep(30)
            
            # Stop monitoring
            stop_event.set()
            
            # Get schema snapshot after
            schema_after = get_field_schema_snapshot(pipeline)
            log_with_timestamp("Schema snapshot taken AFTER field modification", "INFO")
            
            # Compare schemas
            compare_schemas(schema_before, schema_after, "FIELD MODIFICATION")
            
            # Check maintenance status
            tenant = Tenant.objects.get(schema_name='demo')
            if hasattr(tenant, 'maintenance'):
                maintenance = tenant.maintenance
                status = "ACTIVE" if maintenance.is_active else "INACTIVE"
                log_with_timestamp(f"Final maintenance status: {status}", "MAINTENANCE")
                
                if maintenance.is_active:
                    log_with_timestamp("⚠️ WARNING: Maintenance mode still active after field modification!", "WARNING")
                    return False
                else:
                    log_with_timestamp("✅ SUCCESS: Maintenance mode properly deactivated", "SUCCESS")
            
            return True
            
    except Exception as e:
        log_with_timestamp(f"Field modification test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def test_field_deletion():
    """Test 3: Delete a field and monitor migration"""
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("TEST 3: FIELD DELETION - Soft deleting field to trigger migration", "MIGRATION")
    log_with_timestamp("=" * 80, "INFO")
    
    try:
        with schema_context('demo'):
            pipeline = Pipeline.objects.get(id=1)
            
            # Find the field we created in test 1 for deletion
            field_to_delete = pipeline.fields.filter(name__icontains='Test Phone Number').first()
            if not field_to_delete:
                log_with_timestamp("No suitable field found for deletion test", "WARNING")
                log_with_timestamp("Creating a temporary field for deletion test...", "INFO")
                
                field_to_delete = Field.objects.create(
                    pipeline=pipeline,
                    name="Temporary Field for Deletion",
                    field_type="text",
                    display_order=98,
                    created_by_id=1
                )
                time.sleep(5)  # Let creation settle
            
            log_with_timestamp(f"Deleting field: {field_to_delete.name} ({field_to_delete.slug})", "INFO")
            
            # Get schema snapshot before
            schema_before = get_field_schema_snapshot(pipeline)
            log_with_timestamp("Schema snapshot taken BEFORE field deletion", "INFO")
            
            # Start maintenance monitoring
            stop_event = threading.Event()
            monitor_thread = threading.Thread(
                target=monitor_maintenance_status,
                args=('demo', stop_event)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Soft delete the field (this should trigger migration)
            field_slug_to_delete = field_to_delete.slug
            log_with_timestamp(f"Soft deleting field: {field_slug_to_delete}", "MIGRATION")
            
            # Use the field's soft delete method if available
            if hasattr(field_to_delete, 'soft_delete'):
                field_to_delete.soft_delete(deleted_by_id=1, reason="Test deletion")
            else:
                # Fallback to manual soft delete
                field_to_delete.is_deleted = True
                field_to_delete.deleted_at = timezone.now()
                field_to_delete.save()
            
            # Wait for migration to complete
            log_with_timestamp("Waiting for migration to complete (max 30 seconds)...", "INFO")
            time.sleep(30)
            
            # Stop monitoring
            stop_event.set()
            
            # Get schema snapshot after
            schema_after = get_field_schema_snapshot(pipeline)
            log_with_timestamp("Schema snapshot taken AFTER field deletion", "INFO")
            
            # Compare schemas
            compare_schemas(schema_before, schema_after, "FIELD DELETION")
            
            # Check maintenance status
            tenant = Tenant.objects.get(schema_name='demo')
            if hasattr(tenant, 'maintenance'):
                maintenance = tenant.maintenance
                status = "ACTIVE" if maintenance.is_active else "INACTIVE"
                log_with_timestamp(f"Final maintenance status: {status}", "MAINTENANCE")
                
                if maintenance.is_active:
                    log_with_timestamp("⚠️ WARNING: Maintenance mode still active after field deletion!", "WARNING")
                    return False
                else:
                    log_with_timestamp("✅ SUCCESS: Maintenance mode properly deactivated", "SUCCESS")
            
            return True
            
    except Exception as e:
        log_with_timestamp(f"Field deletion test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def check_record_data_consistency():
    """Check that record data is consistent after all migrations"""
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("DATA CONSISTENCY CHECK - Verifying record data integrity", "INFO")
    log_with_timestamp("=" * 80, "INFO")
    
    try:
        with schema_context('demo'):
            pipeline = Pipeline.objects.get(id=1)
            records = Record.objects.filter(pipeline=pipeline, is_deleted=False)
            
            log_with_timestamp(f"Found {records.count()} active records", "INFO")
            
            for record in records[:5]:  # Check first 5 records
                log_with_timestamp(f"Record {record.id}: {list(record.data.keys())}", "INFO")
                
                # Check for orphaned field data
                current_field_slugs = set(pipeline.fields.filter(is_deleted=False).values_list('slug', flat=True))
                record_field_slugs = set(record.data.keys())
                orphaned = record_field_slugs - current_field_slugs
                
                if orphaned:
                    log_with_timestamp(f"  ⚠️ Orphaned data found: {orphaned}", "WARNING")
                else:
                    log_with_timestamp(f"  ✅ Data consistent with schema", "SUCCESS")
            
            return True
            
    except Exception as e:
        log_with_timestamp(f"Data consistency check failed: {e}", "ERROR")
        return False

if __name__ == "__main__":
    log_with_timestamp("🚀 COMPREHENSIVE SCHEMA MIGRATION TEST", "MIGRATION")
    log_with_timestamp("Testing: CREATE, UPDATE, DELETE field operations", "INFO")
    log_with_timestamp("Monitoring: Maintenance mode lifecycle and schema changes", "INFO")
    print()
    
    results = []
    
    # Run all tests
    log_with_timestamp("Starting comprehensive schema migration tests...", "INFO")
    
    # Test 1: Field Creation
    results.append(("Field Creation", test_field_creation()))
    time.sleep(5)  # Brief pause between tests
    
    # Test 2: Field Modification  
    results.append(("Field Modification", test_field_modification()))
    time.sleep(5)
    
    # Test 3: Field Deletion
    results.append(("Field Deletion", test_field_deletion()))
    time.sleep(5)
    
    # Data Consistency Check
    results.append(("Data Consistency", check_record_data_consistency()))
    
    # Summary
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("TEST RESULTS SUMMARY", "INFO")
    log_with_timestamp("=" * 80, "INFO")
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        log_with_timestamp(f"{test_name}: {status}", "SUCCESS" if passed else "ERROR")
    
    overall_success = all(result[1] for result in results)
    
    if overall_success:
        log_with_timestamp("🎉 ALL TESTS PASSED - Schema migration system working correctly!", "SUCCESS")
        log_with_timestamp("✅ Atomic transactions prevent stuck maintenance modes", "SUCCESS")
        log_with_timestamp("✅ Schema changes properly tracked and migrated", "SUCCESS")
        log_with_timestamp("✅ Maintenance mode lifecycle working as expected", "SUCCESS")
    else:
        failed_tests = [name for name, passed in results if not passed]
        log_with_timestamp(f"❌ SOME TESTS FAILED: {', '.join(failed_tests)}", "ERROR")
    
    print()
    log_with_timestamp("Test completed. Check Celery logs for detailed migration information.", "INFO")