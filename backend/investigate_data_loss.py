#!/usr/bin/env python3
"""
URGENT: Investigate Data Loss in OneOTalent Tenant
Adding a field caused all record data to disappear
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
from core.models import AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()

def log_with_timestamp(message, level="INFO"):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    level_emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌", "URGENT": "🚨", "DATA": "📊"}
    emoji = level_emoji.get(level, "📋")
    print(f"{timestamp} {emoji} [{level}] {message}")

def investigate_oneotalent_data_loss():
    """Investigate the data loss in OneOTalent tenant"""
    log_with_timestamp("🚨 URGENT DATA LOSS INVESTIGATION - OneOTalent Tenant", "URGENT")
    log_with_timestamp("=" * 80, "INFO")
    
    try:
        # Check if oneotalent tenant exists
        try:
            tenant = Tenant.objects.get(schema_name='oneotalent')
            log_with_timestamp(f"✅ Found tenant: {tenant.name} ({tenant.schema_name})", "SUCCESS")
        except Tenant.DoesNotExist:
            log_with_timestamp("❌ OneOTalent tenant not found!", "ERROR")
            return False
        
        with schema_context('oneotalent'):
            # Get all pipelines
            pipelines = Pipeline.objects.all()
            log_with_timestamp(f"Found {pipelines.count()} pipelines", "INFO")
            
            for pipeline in pipelines:
                log_with_timestamp(f"\n🔍 PIPELINE: {pipeline.name} (ID: {pipeline.id})", "INFO")
                
                # Check fields
                fields = pipeline.fields.all().order_by('id')
                log_with_timestamp(f"Fields in pipeline ({fields.count()} total):", "DATA")
                
                for field in fields:
                    status = "DELETED" if getattr(field, 'is_deleted', False) else "ACTIVE"
                    log_with_timestamp(f"  ID:{field.id} | {field.slug} ({field.name}) | Type:{field.field_type} | Status:{status}", "DATA")
                
                # Check records and their data
                all_records = Record.objects.filter(pipeline=pipeline)
                active_records = all_records.filter(is_deleted=False)
                
                log_with_timestamp(f"Records: {active_records.count()} active, {all_records.count()} total", "DATA")
                
                if active_records.count() == 0:
                    log_with_timestamp("🚨 NO ACTIVE RECORDS FOUND!", "URGENT")
                else:
                    # Sample first few records to check data
                    log_with_timestamp("Record data analysis:", "DATA")
                    for record in active_records[:5]:
                        if record.data:
                            log_with_timestamp(f"  Record {record.id}: {len(record.data)} fields - {list(record.data.keys())}", "DATA")
                            
                            # Show actual data values (truncated)
                            for key, value in record.data.items():
                                if value:
                                    display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                                    log_with_timestamp(f"    {key}: {display_value}", "DATA")
                        else:
                            log_with_timestamp(f"  Record {record.id}: 🚨 EMPTY DATA FIELD!", "URGENT")
                
                # Check for recently deleted records
                deleted_records = all_records.filter(is_deleted=True).order_by('-deleted_at')[:5]
                if deleted_records.exists():
                    log_with_timestamp(f"Recently deleted records ({deleted_records.count()}):", "WARNING")
                    for record in deleted_records:
                        log_with_timestamp(f"  Record {record.id}: Deleted at {record.deleted_at}", "WARNING")
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"Investigation failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

def check_recent_audit_logs():
    """Check audit logs for recent activity that might explain data loss"""
    log_with_timestamp("\n🔍 CHECKING RECENT AUDIT LOGS", "INFO")
    log_with_timestamp("=" * 50, "INFO")
    
    try:
        with schema_context('oneotalent'):
            # Get recent audit logs (last hour)
            from datetime import timedelta
            from django.utils import timezone
            
            recent_logs = AuditLog.objects.filter(
                timestamp__gte=timezone.now() - timedelta(hours=2)
            ).order_by('-timestamp')[:20]
            
            log_with_timestamp(f"Found {recent_logs.count()} recent audit logs", "INFO")
            
            for log_entry in recent_logs:
                timestamp = log_entry.timestamp.strftime("%H:%M:%S")
                user = log_entry.user.username if log_entry.user else "System"
                log_with_timestamp(f"  {timestamp} | {user} | {log_entry.action} | {log_entry.model_name} | ID:{log_entry.object_id}", "DATA")
                
                # Show changes for important actions
                if log_entry.action in ['deleted', 'updated', 'created'] and log_entry.changes:
                    changes_summary = str(log_entry.changes)[:100] + "..." if len(str(log_entry.changes)) > 100 else str(log_entry.changes)
                    log_with_timestamp(f"    Changes: {changes_summary}", "DATA")
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"Audit log check failed: {e}", "ERROR")
        return False

def check_maintenance_mode_activity():
    """Check if there was recent maintenance mode activity"""
    log_with_timestamp("\n🔧 CHECKING MAINTENANCE MODE ACTIVITY", "INFO")
    log_with_timestamp("=" * 50, "INFO")
    
    try:
        tenant = Tenant.objects.get(schema_name='oneotalent')
        
        if hasattr(tenant, 'maintenance'):
            maintenance = tenant.maintenance
            log_with_timestamp("Maintenance mode status:", "INFO")
            log_with_timestamp(f"  Current status: {'ACTIVE' if maintenance.is_active else 'INACTIVE'}", "INFO")
            log_with_timestamp(f"  Last reason: {maintenance.reason}", "INFO")
            log_with_timestamp(f"  Started: {maintenance.started_at}", "INFO")
            log_with_timestamp(f"  Completed: {maintenance.completed_at}", "INFO")
            log_with_timestamp(f"  Progress: {maintenance.progress_percentage}%", "INFO")
            log_with_timestamp(f"  Message: {maintenance.status_message}", "INFO")
            
            # Check if maintenance was recently active
            if maintenance.completed_at:
                from datetime import timedelta
                from django.utils import timezone
                
                time_since_completion = timezone.now() - maintenance.completed_at
                if time_since_completion < timedelta(hours=1):
                    log_with_timestamp(f"🚨 RECENT MAINTENANCE: Completed {time_since_completion.total_seconds()/60:.1f} minutes ago!", "URGENT")
                    log_with_timestamp(f"Migration data: {maintenance.migration_data}", "DATA")
        else:
            log_with_timestamp("No maintenance record found", "INFO")
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"Maintenance check failed: {e}", "ERROR")
        return False

def check_celery_task_activity():
    """Check recent Celery task activity"""
    log_with_timestamp("\n🚀 CHECKING RECENT CELERY TASK ACTIVITY", "INFO")
    log_with_timestamp("=" * 50, "INFO")
    
    try:
        # Check if there are recent task results
        from django_celery_results.models import TaskResult
        from datetime import timedelta
        from django.utils import timezone
        
        recent_tasks = TaskResult.objects.filter(
            date_created__gte=timezone.now() - timedelta(hours=2),
            task_name__icontains='migrate'
        ).order_by('-date_created')[:10]
        
        log_with_timestamp(f"Found {recent_tasks.count()} recent migration tasks", "INFO")
        
        for task in recent_tasks:
            timestamp = task.date_created.strftime("%H:%M:%S")
            log_with_timestamp(f"  {timestamp} | {task.task_name} | Status: {task.status}", "DATA")
            
            if task.result:
                result_summary = str(task.result)[:200] + "..." if len(str(task.result)) > 200 else str(task.result)
                log_with_timestamp(f"    Result: {result_summary}", "DATA")
                
            if task.traceback:
                error_summary = str(task.traceback)[:200] + "..." if len(str(task.traceback)) > 200 else str(task.traceback)
                log_with_timestamp(f"    🚨 ERROR: {error_summary}", "ERROR")
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"Task check failed (might be expected if django-celery-results not configured): {e}", "WARNING")
        return False

if __name__ == "__main__":
    log_with_timestamp("🚨 URGENT: DATA LOSS INVESTIGATION", "URGENT")
    log_with_timestamp("User reported: Adding field to OneOTalent caused all record data to disappear", "URGENT")
    print()
    
    # Run all investigations
    investigations = [
        ("Data Loss Analysis", investigate_oneotalent_data_loss),
        ("Audit Log Check", check_recent_audit_logs),
        ("Maintenance Mode Check", check_maintenance_mode_activity),
        ("Celery Task Check", check_celery_task_activity)
    ]
    
    results = []
    for name, func in investigations:
        log_with_timestamp(f"Running: {name}", "INFO")
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            log_with_timestamp(f"Investigation '{name}' failed: {e}", "ERROR")
            results.append((name, False))
        print()
    
    # Summary
    log_with_timestamp("=" * 80, "INFO")
    log_with_timestamp("🚨 INVESTIGATION SUMMARY - DATA LOSS", "URGENT")
    log_with_timestamp("=" * 80, "INFO")
    
    for name, success in results:
        status = "✅ Completed" if success else "❌ Failed"
        log_with_timestamp(f"{name}: {status}", "INFO")
    
    log_with_timestamp("\n🎯 NEXT STEPS:", "URGENT")
    log_with_timestamp("1. Check investigation results above for data recovery options", "INFO")
    log_with_timestamp("2. Look for recent backups if data is completely lost", "WARNING")
    log_with_timestamp("3. Check if migration task corrupted data during field addition", "ERROR")
    log_with_timestamp("4. Identify and fix the root cause to prevent future data loss", "URGENT")