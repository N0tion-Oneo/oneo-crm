#!/usr/bin/env python
"""
Simple test for WebSocket updates using existing frontend records
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def test_frontend_websocket_simple():
    """Test WebSocket updates with existing records"""

    print('=== FRONTEND WEBSOCKET SIMPLE TEST ===')
    print()

    with schema_context('oneotalent'):
        from pipelines.models import Record
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Get existing records
        sales_record = Record.objects.get(id=54)  # "Test Tobbid2" in Sales Pipeline
        job_record = Record.objects.get(id=45)    # "test" in Job Applications

        print(f"📋 Sales record: {sales_record.id} - {sales_record.data.get('company_name', 'No name')}")
        print(f"📋 Job record: {job_record.id} - {job_record.data.get('vanessas_text_field', 'No field')}")
        print(f"🔍 Current company_relation: {job_record.data.get('company_relation', [])}")
        print()

        # Set user context
        user = User.objects.filter(email='admin@oneo.com').first()
        if user:
            job_record._current_user = user
            print(f"👤 Set user context: {user.email}")
        else:
            print("⚠️  No admin user found")
        print()

        print("=== TEST 1: Add Relationship ===")
        print(f"Setting company_relation = [{sales_record.id}] on job record {job_record.id}")
        print(f"Expected WebSocket broadcasts:")
        print(f"  📡 pipeline_records_1 (Sales Pipeline)")
        print(f"  📡 pipeline_records_2 (Job Applications)")
        print()

        # Update relationship
        job_record.data = job_record.data or {}
        job_record.data['company_relation'] = [sales_record.id]

        try:
            job_record.save()
            print("✅ Relationship created successfully!")
            print("👀 Check backend logs for WebSocket broadcasts")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

        print("=== TEST 2: Remove Relationship ===")
        print("Setting company_relation = [] on job record")

        # Remove relationship
        job_record.data['company_relation'] = []

        try:
            job_record.save()
            print("✅ Relationship removed successfully!")
            print("👀 Check backend logs for WebSocket broadcasts")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()

        print("=== INSTRUCTIONS ===")
        print("1. Open browser: http://oneotalent.localhost:3000")
        print("2. Navigate to Sales Pipeline (ID 1) records")
        print("3. Navigate to Job Applications (ID 2) records")
        print("4. Watch for real-time updates in record lists")
        print("5. Check browser WebSocket messages in dev tools")

if __name__ == '__main__':
    test_frontend_websocket_simple()