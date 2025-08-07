#!/usr/bin/env python3
"""
Debug Text Field Creation
Test creating a text field to understand what's causing the error
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

def test_text_field_creation():
    """Test creating a text field like the frontend does"""
    
    print("🧪 Testing Text Field Creation")
    print("=" * 50)
    
    with schema_context('oneotalent'):
        # Get the Sales Pipeline and user
        pipeline = Pipeline.objects.filter(name='Sales Pipeline').first()
        user = User.objects.first()
        
        if not pipeline or not user:
            print("❌ Missing pipeline or user")
            return
        
        print(f"📊 Pipeline: {pipeline.name} (ID: {pipeline.id})")
        print(f"👤 User: {user.username}")
        
        # Create the same field config as frontend would send
        field_config = {
            'name': 'Test Text Field',
            'display_name': 'Test Text Field',
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
            'display_order': 50,
            'is_visible_in_list': True,
            'is_visible_in_detail': True,
            'is_visible_in_public_forms': False,
            
            # AI configuration
            'ai_config': {}
        }
        
        print(f"\n🚀 Creating text field with config:")
        print(f"   Name: {field_config['name']}")
        print(f"   Type: {field_config['field_type']}")
        print(f"   Config: {field_config['field_config']}")
        
        try:
            field_manager = get_field_operation_manager(pipeline)
            result = field_manager.create_field(field_config, user)
            
            print(f"\n📊 Creation Result:")
            print(f"   Success: {result.success}")
            
            if result.success:
                print(f"   Created Field: {result.field.name} (slug: {result.field.slug})")
                print(f"   Field Config: {result.field.field_config}")
                print(f"   Storage Constraints: {result.field.storage_constraints}")
                print(f"   ✅ Text field creation successful!")
                
                # Clean up
                result.field.delete()
                print(f"   🧹 Test field cleaned up")
            else:
                print(f"   ❌ Errors: {result.errors}")
                
        except Exception as e:
            print(f"❌ Exception during field creation: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    try:
        test_text_field_creation()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()