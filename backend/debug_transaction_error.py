#!/usr/bin/env python3
"""
Debug Transaction Error
Reproduce the transaction error that occurs during field creation
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.append('/Users/joshcowan/Oneo CRM/backend')

# Set up Django environment  
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = '1'

import django
django.setup()

from django_tenants.utils import schema_context
from pipelines.models import Pipeline, Field
from pipelines.field_operations import get_field_operation_manager
from django.contrib.auth import get_user_model

User = get_user_model()

def test_field_creation_transaction():
    """Test field creation to reproduce transaction error"""
    
    print("🧪 Testing Field Creation Transaction Error")
    print("=" * 60)
    
    with schema_context('oneotalent'):
        # Get the Sales Pipeline and user
        pipeline = Pipeline.objects.filter(name='Sales Pipeline').first()
        user = User.objects.first()
        
        if not pipeline or not user:
            print("❌ Missing pipeline or user")
            return
        
        print(f"📊 Pipeline: {pipeline.name} (ID: {pipeline.id})")
        print(f"👤 User: {user.username}")
        
        # Test with a field config that might cause issues
        field_config = {
            'name': 'Debug Transaction Field',
            'display_name': 'Debug Transaction Field',
            'field_type': 'text',
            'help_text': '',
            'description': '',
            
            # Configuration objects (from frontend)
            'field_config': {},
            'storage_constraints': {
                'allow_null': True,
                'max_storage_length': None,
                'enforce_uniqueness': False,
                'create_index': False
            },
            'business_rules': {
                'stage_requirements': {},
                'conditional_requirements': [],
                'block_transitions': True,
                'show_warnings': True
            },
            
            # Field behavior
            'enforce_uniqueness': False,
            'create_index': False,
            'is_searchable': True,
            'is_ai_field': False,
            
            # Display configuration
            'display_order': 100,
            'is_visible_in_list': True,
            'is_visible_in_detail': True,
            'is_visible_in_public_forms': False,
            
            # AI configuration
            'ai_config': {}
        }
        
        print(f"\n🚀 Creating field that might cause transaction error")
        print(f"   Name: {field_config['name']}")
        print(f"   Type: {field_config['field_type']}")
        
        try:
            field_manager = get_field_operation_manager(pipeline)
            result = field_manager.create_field(field_config, user)
            
            print(f"\n📊 Creation Result:")
            print(f"   Success: {result.success}")
            
            if result.success:
                print(f"   ✅ Field created: {result.field.name} (slug: {result.field.slug})")
                print(f"   Records migrated: {result.metadata.get('existing_records_migrated', 0)}")
                
                # Clean up
                result.field.delete()
                print(f"   🧹 Test field cleaned up")
            else:
                print(f"   ❌ Errors: {result.errors}")
                print(f"   ⚠️  Warnings: {result.warnings}")
                
        except Exception as e:
            print(f"❌ Exception during field creation: {str(e)}")
            print(f"   Exception type: {type(e).__name__}")
            
            # Print full traceback to see where the transaction error occurs
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    try:
        test_field_creation_transaction()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()