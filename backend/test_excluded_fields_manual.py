#!/usr/bin/env python3
"""
Manual test script for AI excluded fields functionality
Run this with: python manage.py runscript test_excluded_fields_manual --settings=oneo_crm.settings
"""

import os
import sys
import django
from unittest.mock import MagicMock

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django_tenants.utils import schema_context
from tenants.models import Tenant
from pipelines.models import Pipeline, Record
from django.contrib.auth import get_user_model
from ai.processors import AIFieldProcessor

User = get_user_model()

def test_excluded_fields():
    """Test that excluded fields are properly filtered from AI processing"""
    print("🧪 Testing AI Excluded Fields Implementation")
    print("=" * 60)
    
    try:
        # Get the existing tenant
        tenant = Tenant.objects.get(schema_name='oneotalent')
        print(f"✅ Using tenant: {tenant.name} ({tenant.schema_name})")
        
        with schema_context(tenant.schema_name):
            # Get a user
            user = User.objects.filter(is_active=True).first()
            if not user:
                print("❌ No active user found")
                return False
            print(f"✅ Using user: {user.email}")
            
            # Create or get a test pipeline
            pipeline, created = Pipeline.objects.get_or_create(
                name='AI Excluded Fields Test Pipeline',
                defaults={
                    'description': 'Test pipeline for excluded fields',
                    'created_by': user
                }
            )
            print(f"✅ {'Created' if created else 'Using'} pipeline: {pipeline.name}")
            
            # Create test record with sensitive data
            test_data = {
                'company_name': 'TechCorp Inc',
                'contact_person': 'John Smith',
                'email': 'john@techcorp.com',        # SENSITIVE
                'phone': '+1-555-123-4567',          # SENSITIVE
                'ssn': '123-45-6789',                # SENSITIVE
                'credit_card': '4111-1111-1111-1111', # SENSITIVE
                'industry': 'technology',
                'deal_value': 50000,
                'notes': 'Interested in our enterprise solution'
            }
            
            record = Record.objects.create(
                pipeline=pipeline,
                data=test_data,
                created_by=user,
                updated_by=user
            )
            print(f"✅ Created test record with ID: {record.id}")
            
            # Mock the API key for testing
            def mock_get_api_key():
                return 'test-api-key-12345'
            
            # Test the AIFieldProcessor with excluded fields
            processor = AIFieldProcessor(tenant, user)
            processor._get_tenant_api_key = mock_get_api_key
            
            print("\n🔒 Testing Excluded Fields Configuration")
            print("-" * 40)
            
            # Test configuration with excluded fields
            field_config = {
                'excluded_fields': ['email', 'ssn', 'credit_card', 'phone'],
                'include_all_fields': True,
                'prompt_template': 'Analyze this complete record: {*}. Company: {company_name}, Contact: {email}'
            }
            
            # Test 1: _build_context should exclude sensitive fields
            print("\n1. Testing _build_context method...")
            context = processor._build_context(record, field_config, {})
            
            excluded_found = []
            included_found = []
            
            for field in field_config['excluded_fields']:
                if field in context:
                    excluded_found.append(field)
                else:
                    print(f"   ✅ Field '{field}' properly excluded from context")
            
            for field in ['company_name', 'contact_person', 'industry', 'deal_value', 'notes']:
                if field in context:
                    included_found.append(field)
                    print(f"   ✅ Field '{field}' properly included in context")
            
            if excluded_found:
                print(f"   ❌ ERROR: These fields should have been excluded: {excluded_found}")
                return False
            
            # Test 2: _preprocess_template should exclude sensitive fields from {*} expansion
            print("\n2. Testing _preprocess_template method...")
            template = "Analyze this complete record: {*}"
            processed_template = processor._preprocess_template(template, record, field_config)
            
            sensitive_data_found = []
            safe_data_found = []
            
            # Check for sensitive data that should be excluded
            sensitive_values = ['john@techcorp.com', '123-45-6789', '4111-1111-1111-1111', '+1-555-123-4567']
            for value in sensitive_values:
                if value in processed_template:
                    sensitive_data_found.append(value)
                else:
                    print(f"   ✅ Sensitive data '{value}' properly excluded from {{*}} expansion")
            
            # Check for safe data that should be included
            safe_values = ['TechCorp Inc', 'John Smith', 'technology', '50000']
            for value in safe_values:
                if value in processed_template:
                    safe_data_found.append(value)
                    print(f"   ✅ Safe data '{value}' properly included in {{*}} expansion")
            
            if sensitive_data_found:
                print(f"   ❌ ERROR: These sensitive values were found in template: {sensitive_data_found}")
                return False
            
            # Test 3: Test with no excluded fields (should include everything)
            print("\n3. Testing with no excluded fields...")
            no_exclusion_config = {
                'excluded_fields': [],
                'include_all_fields': True,
                'prompt_template': 'Data: {*}'
            }
            
            all_context = processor._build_context(record, no_exclusion_config, {})
            all_template = processor._preprocess_template("Data: {*}", record, no_exclusion_config)
            
            # All original fields should be present
            all_present = True
            for field_name, field_value in test_data.items():
                if field_name not in all_context or str(field_value) not in all_template:
                    print(f"   ❌ Field {field_name} missing when no exclusions configured")
                    all_present = False
                else:
                    print(f"   ✅ Field '{field_name}' included when no exclusions")
            
            if not all_present:
                return False
            
            # Test 4: Individual field references should respect exclusions
            print("\n4. Testing individual field references...")
            individual_context = processor._build_context(record, field_config, {})
            
            # Non-excluded field should be accessible
            if individual_context.get('company_name') == 'TechCorp Inc':
                print("   ✅ Non-excluded field 'company_name' accessible")
            else:
                print("   ❌ Non-excluded field 'company_name' not accessible")
                return False
            
            # Excluded field should not be accessible
            if individual_context.get('email') is None:
                print("   ✅ Excluded field 'email' not accessible")
            else:
                print("   ❌ Excluded field 'email' should not be accessible")
                return False
            
            print("\n" + "=" * 60)
            print("🎉 ALL TESTS PASSED! Excluded fields implementation working correctly!")
            print("=" * 60)
            
            # Display the final processed template for verification
            print(f"\n📝 Sample processed template:")
            print("-" * 40)
            print(processed_template[:300] + "..." if len(processed_template) > 300 else processed_template)
            print("-" * 40)
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_excluded_fields()
    if success:
        print("\n✅ AI Excluded Fields implementation validated successfully!")
        sys.exit(0)
    else:
        print("\n❌ AI Excluded Fields implementation has issues!")
        sys.exit(1)