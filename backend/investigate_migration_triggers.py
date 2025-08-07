#!/usr/bin/env python3
"""
Investigation: Why aren't migrations being triggered automatically?
And what happened to the schema changes?
"""
import os
import sys
import django
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field, Record
from tenants.models import Tenant, TenantMaintenance
from django.contrib.auth import get_user_model

User = get_user_model()

def log_with_timestamp(message, level="INFO"):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    level_emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "SCHEMA": "🗄️"}
    emoji = level_emoji.get(level, "📋")
    print(f"{timestamp} {emoji} [{level}] {message}")

def investigate_schema_changes():
    """Check what actually happened to the schema during our tests"""
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("SCHEMA CHANGE INVESTIGATION", "SCHEMA")
    log_with_timestamp("=" * 80, "INFO")
    
    try:
        with schema_context('demo'):
            pipeline = Pipeline.objects.get(id=1)
            log_with_timestamp(f"Pipeline: {pipeline.name}", "INFO")
            
            # Get all fields including soft-deleted ones
            all_fields = Field.objects.filter(pipeline=pipeline).order_by('id')
            active_fields = all_fields.filter(is_deleted=False)
            
            log_with_timestamp(f"Total fields: {all_fields.count()}", "SCHEMA")
            log_with_timestamp(f"Active fields: {active_fields.count()}", "SCHEMA")
            
            log_with_timestamp("Field inventory:", "SCHEMA")
            for field in all_fields:
                status = "DELETED" if getattr(field, 'is_deleted', False) else "ACTIVE"
                log_with_timestamp(f"  ID:{field.id} | {field.slug} ({field.name}) | Type:{field.field_type} | Status:{status}", "SCHEMA")
            
            # Check for specific fields we expected from tests
            expected_fields = ['test-phone-number', 'primary-email-address-modified']
            found_fields = []
            
            for field in all_fields:
                if any(expected in field.slug for expected in expected_fields):
                    found_fields.append(field.slug)
                    log_with_timestamp(f"Found expected field: {field.slug}", "SUCCESS")
            
            if not found_fields:
                log_with_timestamp("⚠️ No expected test fields found in schema", "WARNING")
            
            # Check record data consistency
            log_with_timestamp("Record data analysis:", "SCHEMA")
            records = Record.objects.filter(pipeline=pipeline, is_deleted=False)
            
            active_field_slugs = set(active_fields.values_list('slug', flat=True))
            
            for record in records[:3]:  # Check first 3 records
                record_field_slugs = set(record.data.keys())
                orphaned = record_field_slugs - active_field_slugs
                missing = active_field_slugs - record_field_slugs
                
                log_with_timestamp(f"Record {record.id}: {len(record.data)} fields", "SCHEMA")
                log_with_timestamp(f"  Fields: {list(record.data.keys())}", "SCHEMA")
                
                if orphaned:
                    log_with_timestamp(f"  ⚠️ Orphaned data: {orphaned}", "WARNING")
                if missing:
                    log_with_timestamp(f"  ⚠️ Missing data: {missing}", "WARNING")
                if not orphaned and not missing:
                    log_with_timestamp(f"  ✅ Data consistent with schema", "SUCCESS")
            
            return True
            
    except Exception as e:
        log_with_timestamp(f"Schema investigation failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def investigate_migration_triggers():
    """Check why migrations aren't being triggered automatically"""
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("MIGRATION TRIGGER INVESTIGATION", "INFO")
    log_with_timestamp("=" * 80, "INFO")
    
    try:
        # Check if signal handlers are properly connected
        from django.db.models.signals import post_save, pre_save
        from pipelines.models import Field
        
        log_with_timestamp("Checking Django signal connections for Field model:", "INFO")
        
        # Get signal receivers for Field model
        post_save_receivers = post_save._live_receivers(sender=Field)
        pre_save_receivers = pre_save._live_receivers(sender=Field)
        
        log_with_timestamp(f"post_save receivers for Field: {len(post_save_receivers)}", "INFO")
        for i, receiver in enumerate(post_save_receivers):
            try:
                if hasattr(receiver, '__name__'):
                    name = receiver.__name__
                    module = getattr(receiver, '__module__', 'unknown')
                    log_with_timestamp(f"  {i+1}. {name} from {module}", "INFO")
                else:
                    log_with_timestamp(f"  {i+1}. {type(receiver)} (no __name__)", "INFO")
            except Exception as e:
                log_with_timestamp(f"  {i+1}. Error getting receiver info: {e}", "ERROR")
        
        log_with_timestamp(f"pre_save receivers for Field: {len(pre_save_receivers)}", "INFO")  
        for i, receiver in enumerate(pre_save_receivers):
            try:
                if hasattr(receiver, '__name__'):
                    name = receiver.__name__
                    module = getattr(receiver, '__module__', 'unknown')
                    log_with_timestamp(f"  {i+1}. {name} from {module}", "INFO")
                else:
                    log_with_timestamp(f"  {i+1}. {type(receiver)} (no __name__)", "INFO")
            except Exception as e:
                log_with_timestamp(f"  {i+1}. Error getting receiver info: {e}", "ERROR")
        
        # Check for field operation manager
        try:
            from pipelines.field_operations import get_field_operation_manager
            with schema_context('demo'):
                pipeline = Pipeline.objects.get(id=1)
                manager = get_field_operation_manager(pipeline)
                log_with_timestamp(f"✅ Field operation manager available: {type(manager).__name__}", "SUCCESS")
        except ImportError as e:
            log_with_timestamp(f"❌ Field operation manager import failed: {e}", "ERROR")
        except Exception as e:
            log_with_timestamp(f"❌ Field operation manager error: {e}", "ERROR")
        
        # Check what triggers migrations
        log_with_timestamp("Checking migration trigger conditions:", "INFO")
        
        # Look for migration trigger logic
        try:
            from pipelines import signals
            log_with_timestamp("✅ Pipeline signals module found", "SUCCESS")
            
            # Check what functions exist in signals
            signal_functions = [name for name in dir(signals) if not name.startswith('_')]
            log_with_timestamp(f"Signal functions: {signal_functions}", "INFO")
            
        except ImportError as e:
            log_with_timestamp(f"❌ Pipeline signals import failed: {e}", "ERROR")
        
        # Check if migrations are triggered by specific field changes
        log_with_timestamp("Migration trigger analysis:", "INFO")
        log_with_timestamp("  Field creation: May not require data migration (new field, no existing data to migrate)", "INFO")
        log_with_timestamp("  Field rename: Should trigger migration to rename data keys in records", "WARNING")
        log_with_timestamp("  Field type change: Should trigger migration to convert existing data", "WARNING")
        log_with_timestamp("  Field deletion: May not require migration (soft delete leaves data intact)", "INFO")
        
        # Check maintenance mode history
        try:
            with schema_context('demo'):
                tenant = Tenant.objects.get(schema_name='demo')
                if hasattr(tenant, 'maintenance'):
                    maintenance = tenant.maintenance
                    log_with_timestamp("Recent maintenance history:", "INFO")
                    log_with_timestamp(f"  Current status: {'ACTIVE' if maintenance.is_active else 'INACTIVE'}", "INFO")
                    log_with_timestamp(f"  Last reason: {maintenance.reason}", "INFO")
                    log_with_timestamp(f"  Last started: {maintenance.started_at}", "INFO")
                    log_with_timestamp(f"  Last completed: {maintenance.completed_at}", "INFO")
        except Exception as e:
            log_with_timestamp(f"Maintenance history check failed: {e}", "ERROR")
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"Migration trigger investigation failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def check_migration_requirements():
    """Check what changes actually require migrations"""
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("MIGRATION REQUIREMENT ANALYSIS", "INFO")
    log_with_timestamp("=" * 80, "INFO")
    
    migration_scenarios = [
        {
            "change": "New field added",
            "requires_migration": False,
            "reason": "New fields have no existing data to migrate"
        },
        {
            "change": "Field renamed (slug changed)", 
            "requires_migration": True,
            "reason": "Existing record data keys need to be renamed"
        },
        {
            "change": "Field type changed",
            "requires_migration": True, 
            "reason": "Existing data may need format conversion"
        },
        {
            "change": "Field soft deleted",
            "requires_migration": False,
            "reason": "Soft delete leaves data intact for recovery"
        },
        {
            "change": "Field configuration changed",
            "requires_migration": "Maybe",
            "reason": "Depends on whether change affects existing data"
        }
    ]
    
    for scenario in migration_scenarios:
        status = "🔴 REQUIRED" if scenario["requires_migration"] is True else "🟡 MAYBE" if scenario["requires_migration"] == "Maybe" else "🟢 NOT REQUIRED"
        log_with_timestamp(f"{scenario['change']}: {status}", "INFO")
        log_with_timestamp(f"  Reason: {scenario['reason']}", "INFO")
    
    log_with_timestamp("Our test results analysis:", "INFO")
    log_with_timestamp("  ✅ Field creation: No migration triggered (expected - no data to migrate)", "SUCCESS")
    log_with_timestamp("  ⚠️ Field rename: Migration should have been triggered but wasn't", "WARNING")
    log_with_timestamp("  ❌ Field deletion: Failed due to API issue, but may not need migration anyway", "ERROR")
    
    return True

if __name__ == "__main__":
    log_with_timestamp("🔍 MIGRATION SYSTEM INVESTIGATION", "INFO")
    log_with_timestamp("Why weren't migrations triggered? What happened to schema changes?", "INFO")
    print()
    
    # Run investigations
    results = []
    
    log_with_timestamp("Investigation 1: Schema Changes", "INFO")
    results.append(investigate_schema_changes())
    
    print()
    log_with_timestamp("Investigation 2: Migration Triggers", "INFO")  
    results.append(investigate_migration_triggers())
    
    print()
    log_with_timestamp("Investigation 3: Migration Requirements", "INFO")
    results.append(check_migration_requirements())
    
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("INVESTIGATION SUMMARY", "INFO")
    log_with_timestamp("=" * 80, "INFO")
    
    if all(results):
        log_with_timestamp("🔍 Investigation completed successfully", "SUCCESS")
        log_with_timestamp("📋 Check findings above for migration trigger analysis", "INFO")
    else:
        log_with_timestamp("❌ Some investigations failed - review errors above", "ERROR")