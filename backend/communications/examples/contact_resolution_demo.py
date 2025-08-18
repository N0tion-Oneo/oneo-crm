#!/usr/bin/env python3
"""
Communications Contact Resolution Demo

This script demonstrates how the new contact resolution system works:
1. Uses duplicate rules to identify contacts from communication data
2. Validates email domains against related pipeline records  
3. Provides manual resolution options for unmatched communications

To run this demo:
cd /path/to/backend
source venv/bin/activate
python communications/examples/contact_resolution_demo.py
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from communications.resolvers.contact_identifier import ContactIdentifier
from communications.resolvers.relationship_context import RelationshipContextResolver
from duplicates.models import DuplicateRule
from pipelines.models import Pipeline


def demo_contact_resolution():
    """Demonstrate the contact resolution system"""
    
    print("🚀 Communications Contact Resolution Demo")
    print("=" * 50)
    
    # Demo data - typical WhatsApp message data
    sample_message_data = {
        'email': 'john.doe@acme.com',
        'phone': '+1234567890',
        'name': 'John Doe',
        'linkedin_url': 'https://linkedin.com/in/johndoe'
    }
    
    print(f"📧 Sample Message Data:")
    for key, value in sample_message_data.items():
        print(f"   {key}: {value}")
    print()
    
    # Check for available pipelines with duplicate rules
    print("🔍 Checking Available Pipelines with Duplicate Rules...")
    pipelines_with_rules = Pipeline.objects.filter(
        duplicate_rules__action_on_duplicate='detect_only'
    ).distinct()
    
    if not pipelines_with_rules.exists():
        print("❌ No pipelines found with duplicate rules configured")
        print("   To use contact resolution, you need to:")
        print("   1. Create a pipeline (e.g., 'Contacts')")
        print("   2. Add duplicate rules for email, phone, or other contact fields")
        print("   3. Configure URL extraction rules for domain matching")
        return
    
    print(f"✅ Found {pipelines_with_rules.count()} pipeline(s) with duplicate rules:")
    for pipeline in pipelines_with_rules:
        rules_count = pipeline.duplicate_rules.filter(action_on_duplicate='detect_only').count()
        print(f"   - {pipeline.name}: {rules_count} duplicate rule(s)")
    print()
    
    # Initialize contact resolver (mock tenant_id for demo)
    print("🔧 Initializing Contact Resolution Services...")
    try:
        # Use tenant_id = 1 for demo purposes
        contact_identifier = ContactIdentifier(tenant_id=1)
        relationship_resolver = RelationshipContextResolver(tenant_id=1)
        print("✅ Contact resolution services initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        return
    print()
    
    # Attempt contact identification
    print("🔍 Attempting Contact Identification...")
    try:
        identified_contact = contact_identifier.identify_contact(sample_message_data)
        
        if identified_contact:
            print(f"✅ Contact identified!")
            print(f"   Contact ID: {identified_contact.id}")
            print(f"   Contact Title: {identified_contact.title}")
            print(f"   Pipeline: {identified_contact.pipeline.name}")
            
            # Get relationship context with domain validation
            print("\n🔗 Checking Relationship Context...")
            relationship_context = relationship_resolver.get_relationship_context(
                contact_record=identified_contact,
                message_email=sample_message_data.get('email')
            )
            
            print(f"   Domain Validated: {relationship_context['domain_validated']}")
            print(f"   Validation Status: {relationship_context['validation_status']}")
            print(f"   Message Domain: {relationship_context['message_domain']}")
            
            if relationship_context['pipeline_context']:
                print("   Related Pipelines:")
                for context in relationship_context['pipeline_context']:
                    print(f"     - {context['pipeline_name']} (via {context['relationship_type']})")
            else:
                print("   No related pipeline records found")
                
        else:
            print("❌ No matching contact found")
            print("   This communication would be flagged for manual resolution")
            print("   Available actions:")
            print("   1. Connect to existing contact (POST /api/v1/messages/{id}/connect_contact/)")
            print("   2. Create new contact (POST /api/v1/messages/{id}/create_contact/)")
            
    except Exception as e:
        print(f"❌ Error during contact identification: {e}")
    print()
    
    # Show API endpoints available
    print("🌐 Available API Endpoints:")
    print("   GET /api/v1/messages/unmatched_contacts/")
    print("     - List messages needing manual contact resolution")
    print("   GET /api/v1/messages/domain_validation_warnings/")
    print("     - List messages with domain validation warnings")
    print("   POST /api/v1/messages/{id}/connect_contact/")
    print("     - Manually connect message to existing contact")
    print("   POST /api/v1/messages/{id}/create_contact/")
    print("     - Create new contact from message data")
    print()
    
    print("✅ Demo Complete!")
    print("📖 The contact resolution system is now integrated and ready to use.")


if __name__ == '__main__':
    demo_contact_resolution()