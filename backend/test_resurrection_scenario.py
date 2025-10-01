#!/usr/bin/env python
"""
Test the specific resurrection scenario for WebSocket updates
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context

def test_resurrection_scenario():
    """Test the resurrection scenario where a soft-deleted relationship is reactivated"""

    print('=== RELATIONSHIP RESURRECTION TEST ===')
    print()

    with schema_context('oneotalent'):
        from pipelines.models import Record
        from relationships.models import Relationship
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Get test records
        sales_record = Record.objects.get(id=54)  # Sales Pipeline
        job_record = Record.objects.get(id=45)    # Job Applications

        print(f"📋 Sales record: {sales_record.id} - {sales_record.data.get('company_name', 'No name')}")
        print(f"📋 Job record: {job_record.id} - {job_record.data.get('vanessas_text_field', 'No field')}")
        print()

        # Set user context
        user = User.objects.filter(email='admin@oneo.com').first()
        if user:
            job_record._current_user = user
            print(f"👤 Set user context: {user.email}")
        else:
            print("⚠️  No admin user found")
        print()

        print("=== STEP 1: Create a relationship ===")
        job_record.data = job_record.data or {}
        job_record.data['company_relation'] = [sales_record.id]
        job_record.save()
        print("✅ Created relationship")

        # Find the relationship that was just created
        created_relationship = Relationship.objects.filter(
            source_record_id__in=[job_record.id, sales_record.id],
            target_record_id__in=[job_record.id, sales_record.id],
            is_deleted=False
        ).first()

        if created_relationship:
            print(f"🔗 Found created relationship ID: {created_relationship.id}")
            print(f"   Source: {created_relationship.source_record_id} → Target: {created_relationship.target_record_id}")
        else:
            print("❌ No relationship found after creation")
            return
        print()

        print("=== STEP 2: Soft delete the relationship manually ===")
        # Manually soft delete the relationship to simulate the scenario
        from django.utils import timezone
        created_relationship.is_deleted = True
        created_relationship.deleted_at = timezone.now()
        created_relationship.deleted_by = user
        created_relationship.save()
        print(f"✅ Soft deleted relationship ID: {created_relationship.id}")
        print()

        print("=== STEP 3: Clear the relationship field ===")
        job_record.data['company_relation'] = []
        job_record.save()
        print("✅ Cleared relationship field")
        print()

        print("=== STEP 4: Re-add the relationship (should resurrect) ===")
        print("This should trigger resurrection logic in RelationFieldHandler")
        print("Expected logs:")
        print("   ✓ Resurrected bidirectional relationship to 54")
        print("   📡 This should trigger post_save signal for Relationship")
        print("   🔄 WEBSOCKET: Processing relationship resurrection/update")
        print()

        # Re-add the relationship - this should resurrect the existing one
        job_record.data['company_relation'] = [sales_record.id]
        job_record.save()
        print("✅ Re-added relationship - check logs for resurrection")
        print()

        # Check if the relationship was actually resurrected
        resurrected_relationship = Relationship.objects.filter(
            id=created_relationship.id,
            is_deleted=False
        ).first()

        if resurrected_relationship:
            print(f"✅ RESURRECTION CONFIRMED: Relationship ID {created_relationship.id} is now active")
            print(f"   is_deleted: {resurrected_relationship.is_deleted}")
            print(f"   deleted_at: {resurrected_relationship.deleted_at}")
        else:
            print(f"❌ RESURRECTION FAILED: Relationship ID {created_relationship.id} is still deleted")
        print()

        print("=== CHECK BACKEND LOGS ===")
        print("Look for these specific log patterns:")
        print("   🚨 SIGNAL FIRED: post_save for Relationship <ID>")
        print("   🔄 WEBSOCKET: Processing relationship resurrection/update - ID: <ID>")
        print("   🔄 WEBSOCKET: Triggering record updates for relationship resurrected")
        print()

if __name__ == '__main__':
    test_resurrection_scenario()