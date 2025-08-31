#!/usr/bin/env python
"""
Trigger a real Celery sync for record 66
"""
import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from communications.record_communications.tasks.sync_tasks import sync_record_communications
from django.contrib.auth import get_user_model

User = get_user_model()
from pipelines.models import Record

def trigger_sync(record_id=66, schema_name='oneotalent'):
    """Trigger a real sync via Celery"""
    
    print(f"\n{'='*60}")
    print(f"Starting real sync for record {record_id} in tenant {schema_name}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # Get the user and record details
    with schema_context(schema_name):
        try:
            record = Record.objects.get(id=record_id)
            print(f"✅ Found record: {record}")
            print(f"   Pipeline: {record.pipeline.name}")
        except Record.DoesNotExist:
            print(f"❌ Record {record_id} not found in tenant {schema_name}")
            return
        
        # Get first admin user
        user = User.objects.filter(user_type__name='Admin').first()
        if user:
            print(f"✅ Using admin user: {user.username}")
        else:
            print("⚠️  No admin user found, proceeding without user context")
    
    # Trigger the Celery task
    print(f"\n📤 Sending sync task to Celery...")
    result = sync_record_communications.delay(
        record_id,
        tenant_schema=schema_name,
        triggered_by_id=user.id if user else None,
        trigger_reason='Manual sync with field population monitoring'
    )
    
    print(f"✅ Task ID: {result.id}")
    print(f"   Status: Task queued successfully")
    print(f"\n📊 Monitoring sync progress...")
    print(f"   Check logs: tail -f celery_worker.log")
    print(f"\n{'='*60}\n")
    
    return result.id

if __name__ == '__main__':
    record_id = int(sys.argv[1]) if len(sys.argv) > 1 else 66
    schema = sys.argv[2] if len(sys.argv) > 2 else 'oneotalent'
    
    task_id = trigger_sync(record_id, schema)
    if task_id:
        print(f"📝 Task submitted with ID: {task_id}")
        print(f"   Monitor Celery worker logs for progress")