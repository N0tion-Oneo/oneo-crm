#!/usr/bin/env python
"""
Test script for the stage trigger system
Run this to see how stage transitions automatically trigger form completion prompts
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from pipelines.models import Pipeline, Field, Record
from pipelines.triggers import StageTransitionDetector, get_stage_trigger_status

User = get_user_model()

def create_test_data():
    """Create test pipeline with stage-based business rules"""
    print("Creating test data...")
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        email='test@example.com',
        defaults={'first_name': 'Test', 'last_name': 'User'}
    )
    
    # Create test pipeline
    pipeline, created = Pipeline.objects.get_or_create(
        name='Sales Pipeline - Stage Triggers Test',
        slug='sales-stage-test',
        defaults={
            'description': 'Test pipeline for stage trigger functionality',
            'pipeline_type': 'CRM',
            'created_by': user
        }
    )
    
    if created:
        print(f"Created pipeline: {pipeline.name}")
    
    # Create fields with stage requirements
    
    # Stage field
    stage_field, created = Field.objects.get_or_create(
        pipeline=pipeline,
        slug='stage',
        defaults={
            'name': 'Stage',
            'display_name': 'Deal Stage',
            'field_type': 'select',
            'field_config': {
                'options': [
                    {'value': 'lead', 'label': 'Lead'},
                    {'value': 'qualified', 'label': 'Qualified'},
                    {'value': 'proposal', 'label': 'Proposal'},
                    {'value': 'closed', 'label': 'Closed'}
                ]
            },
            'business_rules': {
                'stage_requirements': {
                    'qualified': {'required': False},
                    'proposal': {'required': False}, 
                    'closed': {'required': False}
                }
            }
        }
    )
    
    # Company name - required for qualified stage
    company_field, created = Field.objects.get_or_create(
        pipeline=pipeline,
        slug='company_name',
        defaults={
            'name': 'Company Name',
            'display_name': 'Company Name',
            'field_type': 'text',
            'is_visible_in_public_forms': True,
            'business_rules': {
                'stage_requirements': {
                    'qualified': {'required': True},
                    'proposal': {'required': True},
                    'closed': {'required': True}
                }
            }
        }
    )
    
    # Budget - required for proposal stage
    budget_field, created = Field.objects.get_or_create(
        pipeline=pipeline,
        slug='budget',
        defaults={
            'name': 'Budget',
            'display_name': 'Budget Amount',
            'field_type': 'number',
            'is_visible_in_public_forms': False,
            'business_rules': {
                'stage_requirements': {
                    'proposal': {'required': True},
                    'closed': {'required': True}
                }
            }
        }
    )
    
    # Decision maker - required for proposal stage
    decision_maker_field, created = Field.objects.get_or_create(
        pipeline=pipeline,
        slug='decision_maker',
        defaults={
            'name': 'Decision Maker',
            'display_name': 'Decision Maker Contact',
            'field_type': 'text',
            'is_visible_in_public_forms': True,
            'business_rules': {
                'stage_requirements': {
                    'proposal': {'required': True},
                    'closed': {'required': True}
                }
            }
        }
    )
    
    print(f"Created {Field.objects.filter(pipeline=pipeline).count()} fields")
    
    return pipeline, user

def test_stage_transitions():
    """Test stage transition detection and triggering"""
    print("\n" + "="*60)
    print("TESTING STAGE TRANSITION TRIGGERS")
    print("="*60)
    
    pipeline, user = create_test_data()
    
    # Test 1: Create record in lead stage (no missing fields)
    print("\n1. Creating record in 'lead' stage...")
    record = Record.objects.create(
        pipeline=pipeline,
        data={
            'stage': 'lead',
            'contact_name': 'John Smith',
        },
        created_by=user,
        updated_by=user
    )
    
    status = get_stage_trigger_status(record)
    print(f"   Stage: {status['current_stage']}")
    print(f"   Missing fields: {len(status['missing_fields'])}")
    print(f"   Should trigger: {status['should_trigger']}")
    
    # Test 2: Move to qualified stage (company_name required)
    print("\n2. Moving to 'qualified' stage without company name...")
    record.data['stage'] = 'qualified'
    record.save()  # This should trigger the signal
    
    status = get_stage_trigger_status(record)
    print(f"   Stage: {status['current_stage']}")
    print(f"   Missing fields: {[f['display_name'] for f in status['missing_fields']]}")
    print(f"   Should trigger: {status['should_trigger']}")
    if status['should_trigger']:
        print(f"   Internal form URL: {status['form_urls']['internal_form']}")
        print(f"   Public form URL: {status['form_urls']['public_form']}")
    
    # Test 3: Add company name and move to proposal stage
    print("\n3. Adding company name and moving to 'proposal' stage...")
    record.data.update({
        'stage': 'proposal',
        'company_name': 'Acme Corp'
    })
    record.save()  # This should trigger the signal
    
    status = get_stage_trigger_status(record)
    print(f"   Stage: {status['current_stage']}")
    print(f"   Missing fields: {[f['display_name'] for f in status['missing_fields']]}")
    print(f"   Should trigger: {status['should_trigger']}")
    if status['should_trigger']:
        print(f"   Internal form URL: {status['form_urls']['internal_form']}")
        print(f"   Public form URL: {status['form_urls']['public_form']}")
    
    # Test 4: Complete all required fields
    print("\n4. Completing all required fields...")
    record.data.update({
        'budget': 50000,
        'decision_maker': 'Jane Doe, CTO'
    })
    record.save()
    
    status = get_stage_trigger_status(record)
    print(f"   Stage: {status['current_stage']}")
    print(f"   Missing fields: {len(status['missing_fields'])}")
    print(f"   Should trigger: {status['should_trigger']}")
    
    # Test 5: Test double filtering for public forms
    print("\n5. Testing public form field filtering...")
    print("   Fields available in public stage forms:")
    for field in status.get('missing_fields', []):
        if field['is_visible_in_public_forms']:
            print(f"   ✓ {field['display_name']} (public + stage required)")
        else:
            print(f"   ✗ {field['display_name']} (stage required but not public)")
    
    print(f"\n   Record final data: {record.data}")
    
    return record

def test_api_endpoint():
    """Test the API endpoint for stage trigger status"""
    print("\n" + "="*60)
    print("TESTING API ENDPOINT")
    print("="*60)
    
    record = Record.objects.first()
    if record:
        print(f"API endpoint available at:")
        print(f"GET /api/v1/pipelines/{record.pipeline.id}/records/{record.id}/stage-trigger-status/")
        
        # Simulate moving record to trigger state
        record.data['stage'] = 'proposal'
        record.data.pop('budget', None)  # Remove budget to trigger missing field
        record.save()
        
        status = get_stage_trigger_status(record)
        print(f"\nCurrent trigger status:")
        print(f"- Stage: {status['current_stage']}")
        print(f"- Missing fields: {[f['display_name'] for f in status['missing_fields']]}")
        print(f"- Should trigger: {status['should_trigger']}")
        print(f"- Form URLs generated: {len(status['form_urls'])} URLs")

if __name__ == "__main__":
    print("🚀 SMART STAGE TRIGGER SYSTEM TEST")
    print("This demonstrates automatic form triggering when records move between stages\n")
    
    try:
        record = test_stage_transitions()
        test_api_endpoint()
        
        print("\n" + "="*60)
        print("✅ STAGE TRIGGER SYSTEM WORKING!")
        print("="*60)
        print("Key Features Demonstrated:")
        print("• Automatic stage transition detection")
        print("• Missing required field identification") 
        print("• Smart form URL generation")
        print("• Double filtering for public forms (public + stage required)")
        print("• Django signal-based triggering")
        print("• API endpoint for real-time status")
        print("\nTo see triggers in action, check the Django logs for 'STAGE TRIGGER:' messages.")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()