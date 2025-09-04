#!/usr/bin/env python
"""Test domain-based secondary record linking"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Record
from communications.models import Participant
from communications.record_communications.storage import ParticipantLinkManager

def test_domain_linking():
    """Test domain field updates trigger secondary linking"""
    tenant_schema = 'oneotalent'
    
    with schema_context(tenant_schema):
        # Find the companies pipeline
        company_pipeline = Pipeline.objects.filter(slug='companies').first()
        if not company_pipeline:
            print("❌ No companies pipeline found")
            return
            
        print(f"✅ Found companies pipeline: {company_pipeline.name}")
        
        # Get the Oneo Digital record
        oneo_record = Record.objects.filter(
            pipeline=company_pipeline,
            data__name__icontains='Oneo Digital'
        ).first()
        
        if not oneo_record:
            print("❌ No Oneo Digital record found")
            return
            
        print(f"✅ Found Oneo Digital record: {oneo_record.id}")
        print(f"  Current domain: {oneo_record.data.get('domain')}")
        
        # Check for participants with oneodigital.com email domain
        participants_with_domain = Participant.objects.filter(
            email__iendswith='@oneodigital.com'
        )
        
        print(f"\n📧 Found {participants_with_domain.count()} participants with @oneodigital.com emails:")
        
        for p in participants_with_domain:
            print(f"  - {p.email} (ID: {p.id})")
            print(f"    Primary record: {p.contact_record_id}")
            print(f"    Secondary record: {p.secondary_record_id}")
            
        # Now test updating the domain field
        print("\n🔄 Testing domain update...")
        
        # First ensure domain is set
        if not oneo_record.data.get('domain'):
            oneo_record.data['domain'] = 'oneodigital.com'
            oneo_record.save()
            print("  ✅ Set domain to oneodigital.com")
        
        # Now update to trigger sync
        oneo_record.data['domain'] = 'oneodigital.com'  # Re-set to trigger save signal
        oneo_record.save()
        print("  ✅ Updated domain (should trigger sync)")
        
        # Check if participants are now linked
        print("\n🔗 Checking participant secondary linking after update:")
        
        participants_with_domain = participants_with_domain.select_related('secondary_record')
        
        linked_count = 0
        for p in participants_with_domain:
            p.refresh_from_db()  # Refresh to get latest data
            if p.secondary_record_id == oneo_record.id:
                linked_count += 1
                print(f"  ✅ {p.email} linked to company record {oneo_record.id}")
            elif p.secondary_record_id:
                print(f"  ⚠️ {p.email} linked to different record {p.secondary_record_id}")
            else:
                print(f"  ❌ {p.email} not linked as secondary")
                
        print(f"\n📊 Summary: {linked_count}/{participants_with_domain.count()} participants linked as secondary")
        
        # Test the management command
        print("\n🛠️ Testing management command for bulk linking...")
        from django.core.management import call_command
        
        try:
            # Run in dry-run mode first
            call_command('link_secondary_by_domain', 
                        tenant=tenant_schema,
                        record_id=oneo_record.id,
                        dry_run=True)
            print("  ✅ Management command dry-run successful")
        except Exception as e:
            print(f"  ❌ Management command failed: {e}")

if __name__ == '__main__':
    test_domain_linking()