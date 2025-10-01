#!/usr/bin/env python
"""
Test to manually trigger relationship signals and see WebSocket broadcasts
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def test_relationship_signals():
    """Test relationship signals manually"""

    print('=== RELATIONSHIP SIGNAL TEST ===')
    print()

    with schema_context('oneotalent'):
        from pipelines.models import Record
        from relationships.models import Relationship, RelationshipType
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Get existing records
        sales_record = Record.objects.get(id=54)  # Sales Pipeline
        job_record = Record.objects.get(id=45)    # Job Applications

        print(f"📋 Sales record: {sales_record.id} - {sales_record.data.get('company_name', 'No name')}")
        print(f"📋 Job record: {job_record.id} - {job_record.data.get('vanessas_text_field', 'No field')}")
        print()

        # Get or create a relationship type
        relationship_type, created = RelationshipType.objects.get_or_create(
            slug='assigned_to',
            defaults={
                'name': 'Assigned To',
                'is_bidirectional': True
            }
        )
        print(f"🔗 Relationship type: {relationship_type.slug} (created: {created})")

        # Set user context
        user = User.objects.filter(email='admin@oneo.com').first()
        print(f"👤 User: {user.email if user else 'None'}")
        print()

        print("=== TEST 1: Create Relationship Manually ===")
        print("This should trigger the post_save signal for Relationship")

        # Check if relationship exists
        existing_rel = Relationship.objects.filter(
            source_record_id=job_record.id,
            target_record_id=sales_record.id,
            is_deleted=False
        ).first()

        if existing_rel:
            print(f"🔗 Found existing relationship: {existing_rel.id}")
            print("   Deleting it first...")
            existing_rel.is_deleted = True
            existing_rel.save()

        # Create new relationship
        print(f"📤 Creating relationship: {job_record.id} → {sales_record.id}")
        relationship = Relationship.objects.create(
            source_record_id=job_record.id,
            target_record_id=sales_record.id,
            source_pipeline_id=job_record.pipeline_id,
            target_pipeline_id=sales_record.pipeline_id,
            relationship_type=relationship_type,
            created_by=user
        )

        print(f"✅ Relationship created: {relationship.id}")
        print("👀 Check backend logs for WebSocket signals")
        print()

        print("=== TEST 2: Delete Relationship ===")
        print("This should trigger another signal")

        relationship.is_deleted = True
        relationship.save()

        print(f"✅ Relationship soft deleted")
        print("👀 Check backend logs for WebSocket signals")
        print()

        print("=== EXPECTED LOG PATTERNS ===")
        print("1. 🚨 SIGNAL FIRED: post_save for Relationship [ID]")
        print("2. 📡 Broadcasting record update to WebSocket channels...")
        print("3. pipeline_records_1 and pipeline_records_2 broadcasts")

if __name__ == '__main__':
    test_relationship_signals()