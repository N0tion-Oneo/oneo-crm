#!/usr/bin/env python3

import os
import django
import logging

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from pipelines.models import Record, Pipeline
from django.contrib.auth import get_user_model
from tenants.models import Tenant
from ai.models import AIJob

User = get_user_model()

# Enable debug logging
logging.basicConfig(level=logging.INFO)

def test_ai_trigger():
    """Test AI trigger processing"""
    
    print("🧪 TESTING: AI Trigger System")
    print("=" * 40)
    
    try:
        # Switch to oneotalent tenant
        tenant = Tenant.objects.get(schema_name='oneotalent')
        
        with schema_context(tenant.schema_name):
            # Get the sales pipeline
            pipeline = Pipeline.objects.get(name='Sales Pipeline')
            record = Record.objects.filter(pipeline=pipeline).first()
            user = User.objects.filter(is_superuser=True).first()
            
            print(f"✅ Record: {record.id}")
            print(f"✅ User: {user.email}")
            
            # Check AI jobs before
            ai_jobs_before = AIJob.objects.count()
            print(f"📊 AI Jobs before: {ai_jobs_before}")
            
            # Find button field
            button_field_slug = 'ai_summary_trigger'
            if button_field_slug not in record.data:
                print(f"❌ Button field not found")
                return
                
            # Modify button field
            original_data = record.data.copy()
            button_data = record.data[button_field_slug].copy()
            button_data['triggered'] = not button_data.get('triggered', False)
            record.data[button_field_slug] = button_data
            
            # Set user context
            record._current_user = user
            
            print(f"🔄 Button changed: {original_data[button_field_slug]['triggered']} → {button_data['triggered']}")
            
            # Save record
            record.save()
            
            # Check AI jobs after
            ai_jobs_after = AIJob.objects.count()
            print(f"📊 AI Jobs after: {ai_jobs_after}")
            print(f"🎯 New AI Jobs created: {ai_jobs_after - ai_jobs_before}")
            
            # Show recent AI jobs
            recent_jobs = AIJob.objects.order_by('-created_at')[:3]
            for job in recent_jobs:
                print(f"   🤖 Job {job.id}: {job.job_type} - {job.status} - {job.field_name}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_ai_trigger()