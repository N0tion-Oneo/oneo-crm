#!/usr/bin/env python
"""
Test to verify which channels relationship updates are being broadcast to
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Field, Record, Pipeline

def test_websocket_channels(tenant_schema='oneotalent'):
    """Test to understand the channel mapping"""

    with schema_context(tenant_schema):
        try:
            print('=== WEBSOCKET CHANNEL MAPPING TEST ===')
            print()

            # Get the relation field and records
            relation_field = Field.objects.get(id=316)  # contacts field
            sales_record = Record.objects.get(id=516)  # Companies record
            job_app_record = Record.objects.get(id=518)  # Contacts record

            print(f"🔧 Relation field: {relation_field.slug} (ID: {relation_field.id})")
            print(f"📍 Field belongs to pipeline: {relation_field.pipeline.name} (ID: {relation_field.pipeline.id})")
            print(f"📋 Sales Record: {sales_record.id} from pipeline {sales_record.pipeline.name} (ID: {sales_record.pipeline.id})")
            print(f"📋 Contact Record: {job_app_record.id} from pipeline {job_app_record.pipeline.name} (ID: {job_app_record.pipeline.id})")
            print()

            print("🔍 Expected WebSocket Channels for Relationship Updates:")
            print(f"   📡 Sales record updates: pipeline_records_{sales_record.pipeline.id}")
            print(f"   📡 Contact record updates: pipeline_records_{job_app_record.pipeline.id}")
            print(f"   📡 General pipeline updates: pipelines_overview")
            print(f"   📡 Individual record updates: document_{sales_record.id}, document_{job_app_record.id}")
            print()

            print("🌐 Frontend Subscription Check:")
            print("From the backend logs, I can see the frontend is subscribed to:")
            print("   - pipeline_records_1 (Pipeline ID 1)")
            print("   - pipeline_records_2 (Pipeline ID 2)")
            print("   - pipeline_updates")
            print()

            # Check if there's a mismatch
            sales_pipeline_id = sales_record.pipeline.id
            contact_pipeline_id = job_app_record.pipeline.id

            print(f"🔍 Channel Mismatch Analysis:")
            print(f"   📊 Sales record is in pipeline {sales_pipeline_id} (Companies)")
            print(f"   📊 Contact record is in pipeline {contact_pipeline_id} (Contacts)")
            print(f"   📊 Frontend is subscribed to pipeline_records_1 and pipeline_records_2")
            print()

            if sales_pipeline_id == 1 or sales_pipeline_id == 2:
                print(f"   ✅ Sales record pipeline {sales_pipeline_id} IS subscribed by frontend")
            else:
                print(f"   ❌ Sales record pipeline {sales_pipeline_id} is NOT subscribed by frontend")

            if contact_pipeline_id == 1 or contact_pipeline_id == 2:
                print(f"   ✅ Contact record pipeline {contact_pipeline_id} IS subscribed by frontend")
            else:
                print(f"   ❌ Contact record pipeline {contact_pipeline_id} is NOT subscribed by frontend")

            print()

            # Show the actual pipeline numbers for debugging
            print("🔍 All Pipeline Information:")
            pipelines = Pipeline.objects.filter(is_active=True).order_by('id')
            for pipeline in pipelines:
                print(f"   🏗️ Pipeline {pipeline.id}: {pipeline.name}")

            print()
            print('=== ANALYSIS COMPLETE ===')

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_websocket_channels()