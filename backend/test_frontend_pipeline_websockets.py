#!/usr/bin/env python
"""
Test WebSocket updates using the actual pipelines the frontend is working with (Pipelines 1 & 2)
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def test_frontend_pipeline_websockets():
    """Test WebSocket updates on the actual pipelines the frontend uses"""

    print('=== FRONTEND PIPELINE WEBSOCKET TEST ===')
    print('Testing WebSocket updates for Pipeline 1 (Sales) and Pipeline 2 (Job Applications)')
    print()

    with schema_context('oneotalent'):
        from pipelines.models import Pipeline, Field, Record

        # Get the actual pipelines the frontend is using
        sales_pipeline = Pipeline.objects.get(id=1)  # Sales Pipeline
        job_pipeline = Pipeline.objects.get(id=2)    # Job Applications

        print(f"🏗️ Sales Pipeline: {sales_pipeline.name} (ID: {sales_pipeline.id})")
        print(f"🏗️ Job Pipeline: {job_pipeline.name} (ID: {job_pipeline.id})")
        print()

        # Get the relationship field from Job Applications to Sales
        relation_field = Field.objects.get(pipeline=job_pipeline, slug='company_relation')
        print(f"🔗 Relation field: {relation_field.slug} (ID: {relation_field.id})")
        print(f"   Config: {relation_field.field_config}")
        print()

        # Create test records if they don't exist
        print("📋 Creating test records...")

        # Sales record
        sales_record, created = Record.objects.get_or_create(
            pipeline=sales_pipeline,
            data__company_name='Test Company WebSocket',
            defaults={
                'data': {
                    'company_name': 'Test Company WebSocket',
                    'contact_email': 'test@example.com',
                    'deal_value': 50000
                }
            }
        )
        print(f"   Sales record: {sales_record.id} ({'created' if created else 'existing'})")

        # Job Application record
        job_record, created = Record.objects.get_or_create(
            pipeline=job_pipeline,
            data__vanessas_text_field='Test Job WebSocket',
            defaults={
                'data': {
                    'vanessas_text_field': 'Test Job WebSocket',
                    'email_2': 'job@example.com'
                }
            }
        )
        print(f"   Job record: {job_record.id} ({'created' if created else 'existing'})")
        print()

        print("🔍 Expected WebSocket Channels:")
        print(f"   📡 Sales record updates should broadcast to: pipeline_records_{sales_pipeline.id}")
        print(f"   📡 Job record updates should broadcast to: pipeline_records_{job_pipeline.id}")
        print(f"   📡 Frontend should be subscribed to: pipeline_records_1, pipeline_records_2")
        print()

        # Test relationship creation
        print("=== TEST 1: Create Relationship ===")
        print(f"Setting company_relation = [{sales_record.id}] on job record {job_record.id}")

        job_record.data = job_record.data or {}
        job_record.data['company_relation'] = [sales_record.id]
        job_record.save()

        print("✅ Relationship created")
        print("👀 Check backend logs for WebSocket broadcasts to:")
        print(f"   📡 pipeline_records_{sales_pipeline.id}")
        print(f"   📡 pipeline_records_{job_pipeline.id}")
        print()

        # Test relationship removal
        print("=== TEST 2: Remove Relationship ===")
        print("Setting company_relation = [] on job record")

        job_record.data['company_relation'] = []
        job_record.save()

        print("✅ Relationship removed")
        print("👀 Check backend logs for WebSocket broadcasts")
        print()

        print("=== MONITORING INSTRUCTIONS ===")
        print("1. Open frontend in browser: http://oneotalent.localhost:3000")
        print("2. Navigate to Sales Pipeline records")
        print("3. Navigate to Job Applications records")
        print("4. Watch for real-time updates when relationships change")
        print("5. Check browser dev tools WebSocket messages")
        print("6. Verify backend logs show correct channel broadcasts")

if __name__ == '__main__':
    test_frontend_pipeline_websockets()