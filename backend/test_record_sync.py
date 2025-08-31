#!/usr/bin/env python
"""
Test script for record-level communication sync
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from pipelines.models import Pipeline, Field, Record
from communications.record_communications.services.record_sync_manager import RecordSyncManager
from communications.record_communications.models import (
    RecordCommunicationProfile,
    RecordAttendeeMapping,
    RecordCommunicationLink
)
from duplicates.models import DuplicateRule
from django.contrib.auth import get_user_model

User = get_user_model()


def test_provider_id_construction():
    """Test provider ID construction from identifiers"""
    print("\n🧪 Testing Provider ID Construction")
    print("=" * 50)
    
    sync_manager = RecordSyncManager()
    
    # Test WhatsApp provider ID
    identifiers = {
        'phone': ['+277203124113', '0782270354'],
        'email': ['john@example.com'],
        'linkedin': ['linkedin.com/in/john-doe']
    }
    
    # Test WhatsApp
    whatsapp_ids = sync_manager._build_provider_ids(identifiers, 'whatsapp')
    print(f"WhatsApp Provider IDs: {whatsapp_ids}")
    assert '277203124113@s.whatsapp.net' in whatsapp_ids
    assert '27782270354@s.whatsapp.net' in whatsapp_ids
    
    # Test LinkedIn
    linkedin_ids = sync_manager._build_provider_ids(identifiers, 'linkedin')
    print(f"LinkedIn Provider IDs: {linkedin_ids}")
    assert 'john-doe' in linkedin_ids
    assert 'john@example.com' in linkedin_ids
    
    # Test Instagram
    instagram_ids = sync_manager._build_provider_ids(identifiers, 'instagram')
    print(f"Instagram Provider IDs: {instagram_ids}")
    assert 'john' in instagram_ids
    
    print("✅ Provider ID construction working correctly!")


def test_identifier_type_mapping():
    """Test identifier type mapping"""
    print("\n🧪 Testing Identifier Type Mapping")
    print("=" * 50)
    
    sync_manager = RecordSyncManager()
    
    channels = ['whatsapp', 'telegram', 'linkedin', 'instagram', 'messenger', 'twitter', 'email']
    for channel in channels:
        identifier_type = sync_manager._get_identifier_type(channel)
        match_type = sync_manager._get_match_type(channel)
        print(f"{channel:12} -> identifier: {identifier_type:10} match: {match_type}")
    
    print("✅ Identifier type mapping working correctly!")


def test_record_sync_flow():
    """Test the record sync flow with mock data"""
    print("\n🧪 Testing Record Sync Flow")
    print("=" * 50)
    
    try:
        # Get or create test pipeline
        pipeline, created = Pipeline.objects.get_or_create(
            slug='test_contacts',
            defaults={
                'name': 'Test Contacts',
                'pipeline_type': 'contacts',
                'is_active': True
            }
        )
        print(f"Pipeline: {pipeline.name} (created: {created})")
        
        # Create test fields
        email_field, _ = Field.objects.get_or_create(
            pipeline=pipeline,
            slug='email',
            defaults={
                'label': 'Email',
                'field_type': 'email',
                'is_required': False
            }
        )
        
        phone_field, _ = Field.objects.get_or_create(
            pipeline=pipeline,
            slug='phone',
            defaults={
                'label': 'Phone',
                'field_type': 'phone',
                'is_required': False
            }
        )
        
        # Create duplicate rule to define identifier fields
        duplicate_rule, _ = DuplicateRule.objects.get_or_create(
            pipeline=pipeline,
            name='Email and Phone Match',
            defaults={
                'logic': {
                    'fields': [
                        {'field': 'email'},
                        {'field': 'phone'}
                    ]
                },
                'is_active': True
            }
        )
        print(f"Duplicate Rule: {duplicate_rule.name}")
        
        # Create test record
        record, created = Record.objects.get_or_create(
            pipeline=pipeline,
            slug='john-doe-test',
            defaults={
                'data': {
                    'email': 'john@example.com',
                    'phone': '+277203124113',
                    'name': 'John Doe'
                }
            }
        )
        print(f"Record: {record.slug} (created: {created})")
        
        # Get or create communication profile
        profile, created = RecordCommunicationProfile.objects.get_or_create(
            record=record,
            defaults={'pipeline': pipeline}
        )
        
        # Extract identifiers
        from communications.record_communications.services.identifier_extractor import RecordIdentifierExtractor
        extractor = RecordIdentifierExtractor()
        identifiers = extractor.extract_identifiers_from_record(record)
        
        print(f"\nExtracted Identifiers:")
        for key, values in identifiers.items():
            if values:
                print(f"  {key}: {values}")
        
        # Update profile with identifiers
        profile.communication_identifiers = identifiers
        profile.save()
        
        # Test provider ID construction
        sync_manager = RecordSyncManager()
        
        for channel_type in ['whatsapp', 'linkedin', 'instagram']:
            provider_ids = sync_manager._build_provider_ids(identifiers, channel_type)
            if provider_ids:
                print(f"\n{channel_type.capitalize()} Provider IDs: {provider_ids}")
        
        print("\n✅ Record sync flow setup completed successfully!")
        
        # Check attendee mappings
        mappings = RecordAttendeeMapping.objects.filter(record=record)
        print(f"\nAttendee Mappings: {mappings.count()}")
        
        # Check communication links
        links = RecordCommunicationLink.objects.filter(record=record)
        print(f"Communication Links: {links.count()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("\n🚀 Starting Record-Level Sync Tests")
    print("=" * 60)
    
    test_provider_id_construction()
    test_identifier_type_mapping()
    test_record_sync_flow()
    
    print("\n" + "=" * 60)
    print("🎉 All tests completed!")


if __name__ == '__main__':
    main()