#!/usr/bin/env python3

import os
import django
import traceback

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from pipelines.models import Record, Pipeline
from django.contrib.auth import get_user_model
from tenants.models import Tenant

User = get_user_model()

def test_execution_flow():
    """Test where exactly the save execution stops"""
    
    print("🧪 TESTING: Save Method Execution Flow")
    print("=" * 50)
    
    try:
        tenant = Tenant.objects.get(schema_name='oneotalent')
        
        with schema_context(tenant.schema_name):
            pipeline = Pipeline.objects.get(name='Sales Pipeline')
            record = Record.objects.filter(pipeline=pipeline).first()
            user = User.objects.filter(is_superuser=True).first()
            
            # Modify button field
            button_field_slug = 'ai_summary_trigger'
            original_data = record.data.copy()
            button_data = record.data[button_field_slug].copy()
            button_data['triggered'] = not button_data.get('triggered', False)
            button_data['test_timestamp'] = '2025-08-09T15:55:00Z'
            record.data[button_field_slug] = button_data
            
            # Set user context
            record._current_user = user
            
            print(f"🔄 Modified button field: {button_data['triggered']}")
            print(f"👤 User context: {record._current_user.email}")
            print(f"🚫 Skip flags: ai_processing={getattr(record, '_skip_ai_processing', False)}, broadcast={getattr(record, '_skip_broadcast', False)}")
            
            # Monkey patch the save method to add debugging at critical points
            original_update_pipeline_stats = record._update_pipeline_stats
            
            def debug_update_pipeline_stats(self):
                print(f"🔍 EXECUTION POINT: _update_pipeline_stats() called")
                return original_update_pipeline_stats()
                
            record._update_pipeline_stats = debug_update_pipeline_stats.__get__(record, Record)
            
            print(f"\n💾 Starting save operation...")
            record.save()
            print(f"✅ Save completed successfully")
            
    except Exception as e:
        print(f"❌ Error during save: {e}")
        traceback.print_exc()

if __name__ == '__main__':
    test_execution_flow()