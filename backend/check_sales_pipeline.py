#!/usr/bin/env python3
"""
Check Sales Pipeline fields and sharing configuration
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenants.models import Tenant
from pipelines.models import Pipeline, Field
from django_tenants.utils import schema_context

User = get_user_model()

def check_sales_pipeline():
    """Check Sales Pipeline configuration"""
    
    print("🔍 Checking Sales Pipeline...")
    
    # Get oneotalent tenant
    try:
        talent_tenant = Tenant.objects.get(schema_name='oneotalent')
        print(f"✅ Found oneotalent tenant: {talent_tenant.name}")
    except Tenant.DoesNotExist:
        print("❌ Oneotalent tenant not found")
        return
    
    with schema_context('oneotalent'):
        # Find Sales Pipeline
        try:
            sales_pipeline = Pipeline.objects.get(name='Sales Pipeline')
            print(f"✅ Found Sales Pipeline: {sales_pipeline.name} (ID: {sales_pipeline.id})")
        except Pipeline.DoesNotExist:
            print("❌ Sales Pipeline not found")
            return
        
        # Get all fields
        fields = sales_pipeline.fields.all().order_by('display_order', 'name')
        print(f"\n📋 Sales Pipeline has {fields.count()} fields:")
        
        for field in fields:
            sharing_status = "✅ SHAREABLE" if field.is_visible_in_shared_list_and_detail_views else "❌ NOT SHAREABLE"
            print(f"   - {field.name} ({field.slug})")
            print(f"     Type: {field.field_type}, Order: {field.display_order}")
            print(f"     Sharing: {sharing_status}")
            print(f"     Visible in list: {field.is_visible_in_list}")
            print(f"     Visible in detail: {field.is_visible_in_detail}")
            print()
        
        # Count shareable fields
        shareable_count = fields.filter(is_visible_in_shared_list_and_detail_views=True).count()
        print(f"📊 Summary: {shareable_count}/{fields.count()} fields are shareable")
        
        return {
            'pipeline_id': sales_pipeline.id,
            'total_fields': fields.count(),
            'shareable_fields': shareable_count,
            'fields': [
                {
                    'name': f.name,
                    'slug': f.slug,
                    'type': f.field_type,
                    'shareable': f.is_visible_in_shared_list_and_detail_views
                }
                for f in fields
            ]
        }

if __name__ == '__main__':
    result = check_sales_pipeline()
    if result and result['shareable_fields'] == 0:
        print(f"\n💡 Tip: To enable sharing, update some fields:")
        print(f"   Field.objects.filter(pipeline_id={result['pipeline_id']}).update(is_visible_in_shared_list_and_detail_views=True)")