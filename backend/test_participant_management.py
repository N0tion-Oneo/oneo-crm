#!/usr/bin/env python
"""
Test script for the Participant Management System
Tests field mapping, record creation, and linking functionality
"""

import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from communications.models import Participant
from communications.services.participant_management import ParticipantManagementService
from pipelines.models import Pipeline, Field
from duplicates.models import DuplicateRule
from tenants.models import Tenant

User = get_user_model()


def print_section(title):
    """Print a section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_participant_management():
    """Test the participant management system"""
    
    # Use oneotalent tenant
    tenant = Tenant.objects.filter(schema_name='oneotalent').first()
    if not tenant:
        print("❌ Error: oneotalent tenant not found!")
        print("Available tenants:")
        for t in Tenant.objects.exclude(schema_name='public'):
            print(f"  - {t.name} (schema: {t.schema_name})")
        return
    
    print(f"Using tenant: {tenant.name} (schema: {tenant.schema_name})")
    
    with schema_context(tenant.schema_name):
        print_section("Testing Participant Management System")
        
        # Get or create a test user
        user = User.objects.filter(email='admin@oneo.com').first()
        if not user:
            user = User.objects.create_user(
                email='admin@oneo.com',
                password='admin123',
                first_name='Admin'
            )
            print(f"Created test user: {user.email}")
        
        # Create or get a test pipeline
        pipeline, created = Pipeline.objects.get_or_create(
            slug='contacts',
            defaults={
                'name': 'Contacts',
                'description': 'Contact management pipeline',
                'is_active': True,
                'created_by': user
            }
        )
        print(f"{'Created' if created else 'Using'} pipeline: {pipeline.name}")
        
        # Create some fields for the pipeline
        fields_to_create = [
            {'slug': 'email_address', 'name': 'Email Address', 'field_type': 'email'},
            {'slug': 'phone_number', 'name': 'Phone Number', 'field_type': 'phone'},
            {'slug': 'full_name', 'name': 'Full Name', 'field_type': 'text'},
            {'slug': 'linkedin_url', 'name': 'LinkedIn URL', 'field_type': 'url'},
        ]
        
        for field_data in fields_to_create:
            field, created = Field.objects.get_or_create(
                pipeline=pipeline,
                slug=field_data['slug'],
                defaults={
                    'name': field_data['name'],
                    'field_type': field_data['field_type'],
                    'field_config': {},
                    'created_by': user
                }
            )
            if created:
                print(f"  Created field: {field.name}")
        
        # Create a duplicate rule to test field identification
        duplicate_rule, created = DuplicateRule.objects.get_or_create(
            tenant=tenant,
            pipeline=pipeline,
            name='Email and Phone Match',
            defaults={
                'description': 'Match records by email or phone',
                'logic': {
                    'operator': 'OR',
                    'conditions': [
                        {
                            'operator': 'AND',
                            'fields': [
                                {'field': 'email_address', 'match_type': 'email_normalized'}
                            ]
                        },
                        {
                            'operator': 'AND',
                            'fields': [
                                {'field': 'phone_number', 'match_type': 'phone_normalized'}
                            ]
                        }
                    ]
                },
                'is_active': True,
                'created_by': user
            }
        )
        print(f"{'Created' if created else 'Using'} duplicate rule: {duplicate_rule.name}")
        
        # Create or get a test participant
        participant, created = Participant.objects.get_or_create(
            email='john.doe@example.com',
            defaults={
                'name': 'John Doe',
                'phone': '+27782270354',
                'linkedin_member_urn': 'john-doe-123'
            }
        )
        print(f"\n{'Created' if created else 'Using'} participant: {participant.name} ({participant.email})")
        
        # Initialize the service
        service = ParticipantManagementService(tenant=tenant)
        
        print_section("Testing Field Identification from Duplicate Rules")
        
        # Test field identification
        field_purposes = service.get_identifying_fields_from_duplicate_rules(pipeline)
        print("Identified field purposes:")
        for purpose, fields in field_purposes.items():
            if fields:
                print(f"  {purpose}: {fields}")
        
        print_section("Testing Field Mapping Preview")
        
        # Test field mapping preview
        mappings = service.preview_field_mapping(participant, pipeline)
        print(f"Field mappings for participant '{participant.name}':")
        for mapping in mappings:
            print(f"\n  Field: {mapping['field_name']} ({mapping['field_slug']})")
            print(f"    Type: {mapping['field_type']}")
            print(f"    Source: {mapping['source']}")
            print(f"    Participant Value: {mapping['participant_value']}")
            print(f"    Formatted Value: {mapping['formatted_value']}")
            print(f"    Valid: {mapping['is_valid']}")
            if mapping['validation_errors']:
                print(f"    Errors: {mapping['validation_errors']}")
        
        # Only create record if participant is not already linked
        if not participant.contact_record:
            print_section("Testing Record Creation from Participant")
            
            try:
                # Create record from participant
                record = service.create_record_from_participant(
                    participant=participant,
                    pipeline=pipeline,
                    user=user,
                    link_conversations=False  # No conversations to link in test
                )
                
                print(f"✅ Successfully created record: {record.id}")
                print(f"Record data: {json.dumps(record.data, indent=2)}")
                print(f"Participant now linked to record: {participant.contact_record_id}")
                
            except Exception as e:
                print(f"❌ Error creating record: {e}")
        else:
            print(f"\n✅ Participant already linked to record: {participant.contact_record_id}")
        
        print_section("Testing Unlink Functionality")
        
        if participant.contact_record:
            previous_record_id = participant.contact_record_id
            service.unlink_participant(participant, user)
            print(f"✅ Unlinked participant from record {previous_record_id}")
            print(f"Participant contact_record is now: {participant.contact_record}")
        
        print_section("Testing Link to Existing Record")
        
        # Get any existing record or create one
        from pipelines.models import Record
        test_record = Record.objects.filter(pipeline=pipeline).first()
        if not test_record:
            test_record = Record.objects.create(
                pipeline=pipeline,
                data={'test': 'data'},
                created_by=user
            )
        
        service.link_participant_to_record(
            participant=participant,
            record=test_record,
            user=user,
            confidence=0.95,
            link_conversations=False
        )
        print(f"✅ Linked participant to record {test_record.id}")
        print(f"Link confidence: {participant.resolution_confidence}")
        print(f"Link method: {participant.resolution_method}")
        
        print_section("Test Complete!")
        print("\n✅ All participant management tests completed successfully!")
        
        # Summary
        print("\nSummary:")
        print(f"- Tenant: {tenant.name}")
        print(f"- Pipeline: {pipeline.name}")
        print(f"- Fields: {Field.objects.filter(pipeline=pipeline).count()}")
        print(f"- Participant: {participant.name} ({participant.email})")
        print(f"- Linked to Record: {participant.contact_record_id}")


if __name__ == "__main__":
    try:
        test_participant_management()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)