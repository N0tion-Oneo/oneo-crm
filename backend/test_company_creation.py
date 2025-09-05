#!/usr/bin/env python
"""Test company creation with duplicate rule field mapping only"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model

User = get_user_model()
from communications.models import Participant, ParticipantSettings
from communications.services.auto_create_service import AutoCreateContactService
from pipelines.models import Pipeline, Field
from duplicates.models import DuplicateRule

# Switch to oneotalent tenant
schema_name = 'oneotalent'

with schema_context(schema_name):
    print(f"\n🏢 Testing company creation with duplicate rule fields only in tenant: {schema_name}")
    
    # Get admin user
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        print("❌ No admin user found")
        sys.exit(1)
    print(f"✅ Using admin user: {admin.email}")
    
    # Get or create settings
    settings = ParticipantSettings.objects.first()
    if not settings:
        print("❌ No participant settings found")
        sys.exit(1)
    
    # Check company pipeline configuration
    if settings.enable_real_time_creation and settings.default_company_pipeline_id:
        company_pipeline = Pipeline.objects.filter(id=settings.default_company_pipeline_id).first()
        if company_pipeline:
            print(f"\n📋 Company pipeline: {company_pipeline.name}")
            
            # Check duplicate rules for this pipeline
            duplicate_rules = DuplicateRule.objects.filter(
                pipeline_id=company_pipeline.id,
                is_active=True
            )
            
            print(f"📑 Active duplicate rules: {duplicate_rules.count()}")
            for rule in duplicate_rules:
                print(f"  - Rule: {rule.name}")
                print(f"    Logic: {rule.logic}")
            
            # Get fields from the company pipeline
            fields = Field.objects.filter(pipeline_id=company_pipeline.id)
            print(f"\n🔤 Company pipeline fields:")
            for field in fields:
                print(f"  - {field.slug}: {field.name} (type: {field.field_type})")
            
            # Create a test participant
            test_participant = Participant.objects.create(
                email="test@example.com",
                name="Test User"
            )
            print(f"\n👤 Created test participant: {test_participant.name}")
            
            # Initialize service
            service = AutoCreateContactService()
            
            # Test company creation
            try:
                print("\n🏗️ Testing company creation from domain...")
                domain = "example.com"
                
                # Get field purposes from duplicate rules
                from communications.services.participant_management import ParticipantManagementService
                participant_service = ParticipantManagementService()
                field_purposes = participant_service.get_identifying_fields_from_duplicate_rules(company_pipeline)
                
                print(f"📊 Field purposes from duplicate rules:")
                for purpose, field_list in field_purposes.items():
                    if field_list:
                        print(f"  {purpose}: {field_list}")
                
                # Check configured company name field
                if settings.company_name_field:
                    print(f"📝 Configured company name field: {settings.company_name_field}")
                else:
                    print("⚠️ No company name field configured")
                
                # Create company
                company = service.create_company_from_domain(domain, test_participant, admin)
                
                if company:
                    print(f"✅ Company created successfully!")
                    print(f"  ID: {company.id}")
                    print(f"  Data: {company.data}")
                else:
                    print("❌ Failed to create company")
                    
            except Exception as e:
                print(f"❌ Error creating company: {e}")
                import traceback
                traceback.print_exc()
            
            # Cleanup
            test_participant.delete()
            print("\n🧹 Test participant cleaned up")
            
        else:
            print(f"❌ Company pipeline not found (ID: {settings.default_company_pipeline_id})")
    else:
        print("❌ Real-time creation not enabled or no company pipeline configured")
        print(f"  enable_real_time_creation: {settings.enable_real_time_creation}")
        print(f"  default_company_pipeline_id: {settings.default_company_pipeline_id}")