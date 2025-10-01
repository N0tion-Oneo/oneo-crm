#!/usr/bin/env python
"""
Clean up all relationships to start fresh
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oneo_crm.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django_tenants.utils import schema_context
from relationships.models import Relationship

def clean_relationships(tenant_schema='oneotalent'):
    """Clean up all relationships"""

    print(f"\n{'='*80}")
    print(f"🧹 CLEANING ALL RELATIONSHIPS")
    print(f"{'='*80}\n")

    with schema_context(tenant_schema):
        try:
            # Count all relationships
            all_relationships = Relationship.objects.all()
            print(f"📊 Total relationships before: {all_relationships.count()}")

            # Delete all relationships
            deleted_count = all_relationships.delete()[0]
            print(f"🗑️ Deleted {deleted_count} relationships")

            # Verify
            remaining = Relationship.objects.all().count()
            print(f"📊 Relationships remaining: {remaining}")

            print(f"\n✅ Cleanup completed!")

        except Exception as e:
            print(f"\n❌ Cleanup failed with error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*80}")
    print(f"🏁 CLEANUP COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    clean_relationships('oneotalent')