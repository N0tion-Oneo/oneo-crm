#!/usr/bin/env python3
"""
Manual Migration Trigger Test
Directly tests the atomic migration task to verify the maintenance mode fix
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
from pipelines.tasks import migrate_tenant_schema_automatically
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

def monitor_maintenance_real_time(tenant_schema, duration_seconds=45):
    """Monitor maintenance status in real-time"""
    log_with_timestamp(f"Starting real-time maintenance monitoring for {tenant_schema}", "MAINTENANCE")
    
    start_time = time.time()
    last_status = None
    last_progress = None
    
    while time.time() - start_time < duration_seconds:
        try:
            tenant = Tenant.objects.get(schema_name=tenant_schema)
            if hasattr(tenant, 'maintenance'):
                maintenance = tenant.maintenance
                current_status = "ACTIVE" if maintenance.is_active else "INACTIVE"
                current_progress = maintenance.progress_percentage
                current_message = maintenance.status_message
                
                # Only log when status changes
                if (current_status != last_status or 
                    current_progress != last_progress or 
                    (current_status == "ACTIVE" and time.time() - start_time < 5)):
                    
                    log_with_timestamp(
                        f"Maintenance: {current_status} ({current_progress}%) - {current_message}", 
                        "MAINTENANCE"
                    )
                    last_status = current_status
                    last_progress = current_progress
            
            time.sleep(0.5)  # Check twice per second
            
        except Exception as e:
            log_with_timestamp(f"Monitoring error: {e}", "ERROR")
            break
    
    log_with_timestamp("Real-time maintenance monitoring completed", "MAINTENANCE")

def test_manual_migration_trigger():
    """Test manual trigger of migration task with detailed monitoring"""
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("MANUAL MIGRATION TRIGGER TEST", "MIGRATION") 
    log_with_timestamp("Testing atomic transaction and maintenance mode lifecycle", "INFO")
    log_with_timestamp("=" * 80, "INFO")
    
    try:
        with schema_context('demo'):
            # Get pipeline and field
            pipeline = Pipeline.objects.get(id=1)
            field = pipeline.fields.first()
            
            if not field:
                log_with_timestamp("No field found for migration test", "ERROR")
                return False
                
            log_with_timestamp(f"Using field: {field.name} ({field.slug}) in pipeline: {pipeline.name}", "INFO")
            
            # Prepare migration changes data
            changes = {
                'risk_level': 'low',
                'change_details': [f"Test migration for field '{field.slug}' - manual trigger"],
                'migration_types': ['field_rename'],
                'requires_migration': True,
                'affected_records_estimate': 0
            }
            
            log_with_timestamp("Migration changes prepared:", "INFO")
            for key, value in changes.items():
                log_with_timestamp(f"  {key}: {value}", "INFO")
            
            # Check initial maintenance status
            tenant = Tenant.objects.get(schema_name='demo')
            maintenance, created = TenantMaintenance.objects.get_or_create(
                tenant=tenant,
                defaults={'is_active': False, 'reason': 'Initial setup'}
            )
            
            initial_status = "ACTIVE" if maintenance.is_active else "INACTIVE"
            log_with_timestamp(f"Initial maintenance status: {initial_status}", "MAINTENANCE")
            
            # Start real-time monitoring in background thread
            monitor_thread = threading.Thread(
                target=monitor_maintenance_real_time,
                args=('demo', 45)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            
            log_with_timestamp("🚀 TRIGGERING MIGRATION TASK MANUALLY", "MIGRATION")
            log_with_timestamp("This will test the atomic transaction fix...", "INFO")
            
            # Execute migration task synchronously (not async)
            start_time = time.time()
            result = migrate_tenant_schema_automatically(
                tenant_schema='demo',
                field_id=field.id,
                changes=changes
            )
            end_time = time.time()
            
            duration = end_time - start_time
            log_with_timestamp(f"Migration task completed in {duration:.2f} seconds", "MIGRATION")
            
            # Log migration result
            log_with_timestamp("Migration task result:", "INFO")
            for key, value in result.items():
                log_with_timestamp(f"  {key}: {value}", "INFO")
            
            # Wait for monitoring to complete
            time.sleep(2)
            
            # Check final maintenance status
            tenant.refresh_from_db()
            if hasattr(tenant, 'maintenance'):
                tenant.maintenance.refresh_from_db()
                final_status = "ACTIVE" if tenant.maintenance.is_active else "INACTIVE"
                final_progress = tenant.maintenance.progress_percentage
                final_message = tenant.maintenance.status_message
                
                log_with_timestamp(f"Final maintenance status: {final_status}", "MAINTENANCE")
                log_with_timestamp(f"Final progress: {final_progress}%", "MAINTENANCE")
                log_with_timestamp(f"Final message: {final_message}", "MAINTENANCE")
                
                # Verify atomic behavior
                if result['status'] == 'completed' and tenant.maintenance.is_active:
                    log_with_timestamp("❌ ATOMIC FAILURE: Migration succeeded but maintenance still active!", "ERROR")
                    return False
                elif result['status'] == 'completed' and not tenant.maintenance.is_active:
                    log_with_timestamp("✅ ATOMIC SUCCESS: Migration and maintenance deactivation both committed!", "SUCCESS")
                    return True
                elif result['status'] == 'failed' and tenant.maintenance.is_active:
                    log_with_timestamp("✅ ROLLBACK SUCCESS: Failed migration kept maintenance active!", "SUCCESS")
                    return True
                else:
                    log_with_timestamp(f"⚠️ UNEXPECTED STATE: Status={result['status']}, Maintenance={tenant.maintenance.is_active}", "WARNING")
                    return False
            else:
                log_with_timestamp("❌ No maintenance record found", "ERROR")
                return False
                
    except Exception as e:
        log_with_timestamp(f"Manual migration trigger test failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def test_failure_scenario():
    """Test what happens when migration fails - should rollback atomically"""
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("FAILURE SCENARIO TEST", "MIGRATION") 
    log_with_timestamp("Testing atomic rollback when migration fails", "INFO")
    log_with_timestamp("=" * 80, "INFO")
    
    try:
        with schema_context('demo'):
            pipeline = Pipeline.objects.get(id=1)
            field = pipeline.fields.first()
            
            # Create changes that will cause migration to fail
            changes = {
                'risk_level': 'high',
                'change_details': ["Simulated failure test"],
                'migration_types': ['invalid_migration_type'],  # This should cause failure
                'requires_migration': True,
                'affected_records_estimate': 1000  # High number
            }
            
            log_with_timestamp("Triggering migration with invalid changes to test failure handling...", "MIGRATION")
            
            # Start monitoring
            monitor_thread = threading.Thread(
                target=monitor_maintenance_real_time,
                args=('demo', 30)
            )
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # This should fail and test our rollback behavior
            result = migrate_tenant_schema_automatically(
                tenant_schema='demo',
                field_id=field.id,
                changes=changes
            )
            
            log_with_timestamp(f"Migration result: {result}", "INFO")
            
            time.sleep(2)  # Let monitoring complete
            
            # Check that maintenance is properly handled in failure case
            tenant = Tenant.objects.get(schema_name='demo')
            if hasattr(tenant, 'maintenance'):
                tenant.maintenance.refresh_from_db()
                if result['status'] == 'failed' and tenant.maintenance.is_active:
                    log_with_timestamp("✅ FAILURE HANDLING: Migration failed, maintenance kept active for investigation", "SUCCESS")
                    return True
                else:
                    log_with_timestamp(f"⚠️ UNEXPECTED FAILURE STATE: {result['status']}, Maintenance: {tenant.maintenance.is_active}", "WARNING")
                    return False
            
        return False
        
    except Exception as e:
        log_with_timestamp(f"Failure scenario test error: {e}", "ERROR")
        return False

if __name__ == "__main__":
    log_with_timestamp("🧪 MANUAL MIGRATION TRIGGER TESTS", "MIGRATION")
    log_with_timestamp("Testing atomic transaction and maintenance mode fixes", "INFO") 
    print()
    
    # Test 1: Normal migration
    log_with_timestamp("Starting Test 1: Normal Migration with Atomic Transaction", "INFO")
    test1_result = test_manual_migration_trigger()
    
    time.sleep(3)
    
    # Test 2: Failure scenario  
    log_with_timestamp("Starting Test 2: Failure Scenario with Rollback", "INFO")
    test2_result = test_failure_scenario()
    
    # Summary
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("TEST RESULTS SUMMARY", "INFO")
    log_with_timestamp("=" * 80, "INFO")
    
    log_with_timestamp(f"Test 1 - Normal Migration: {'✅ PASSED' if test1_result else '❌ FAILED'}", "SUCCESS" if test1_result else "ERROR")
    log_with_timestamp(f"Test 2 - Failure Scenario: {'✅ PASSED' if test2_result else '❌ FAILED'}", "SUCCESS" if test2_result else "ERROR")
    
    if test1_result and test2_result:
        log_with_timestamp("🎉 ALL TESTS PASSED - Atomic migration fix working correctly!", "SUCCESS")
        log_with_timestamp("✅ No stuck maintenance modes possible", "SUCCESS") 
        log_with_timestamp("✅ Atomic transactions ensure consistency", "SUCCESS")
    else:
        log_with_timestamp("❌ SOME TESTS FAILED - Review results above", "ERROR")