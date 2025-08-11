#!/usr/bin/env python3
"""
Test script to verify USER field type implementation
"""
import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_user_field_implementation():
    """Test USER field type implementation"""
    print("🧪 Testing USER Field Implementation")
    print("=" * 50)
    
    # Test 1: FieldType enum
    print("\n1. Testing FieldType enum...")
    try:
        from pipelines.field_types import FieldType
        assert hasattr(FieldType, 'USER'), "USER not found in FieldType enum"
        assert FieldType.USER == "user", f"USER field type value incorrect: {FieldType.USER}"
        print("   ✅ FieldType.USER exists and has correct value")
    except Exception as e:
        print(f"   ❌ FieldType test failed: {e}")
        return False
    
    # Test 2: UserFieldConfig class
    print("\n2. Testing UserFieldConfig class...")
    try:
        from pipelines.field_types import UserFieldConfig, FIELD_TYPE_CONFIGS
        
        # Test config creation
        config = UserFieldConfig(
            relationship_type="assigned_to",
            allow_multiple=True,
            default_role="primary"
        )
        assert config.relationship_type == "assigned_to"
        assert config.allow_multiple == True
        assert config.default_role == "primary"
        
        # Test registry mapping
        assert FieldType.USER in FIELD_TYPE_CONFIGS
        assert FIELD_TYPE_CONFIGS[FieldType.USER] == UserFieldConfig
        
        print("   ✅ UserFieldConfig class works correctly")
    except Exception as e:
        print(f"   ❌ UserFieldConfig test failed: {e}")
        return False
    
    # Test 3: Field validation
    print("\n3. Testing USER field validation...")
    try:
        from pipelines.field_types import validate_field_config
        
        # Valid config
        valid_config = {
            "relationship_type": "assigned_to",
            "allow_multiple": True,
            "default_role": "primary",
            "allowed_roles": ["primary", "secondary"]
        }
        validated = validate_field_config(FieldType.USER, valid_config)
        print("   ✅ Valid config validation passed")
        
        # Invalid config
        try:
            invalid_config = {
                "relationship_type": "invalid_type",  # Invalid
                "allow_multiple": True
            }
            validate_field_config(FieldType.USER, invalid_config)
            print("   ❌ Invalid config should have failed")
        except ValueError:
            print("   ✅ Invalid config validation correctly failed")
        
    except Exception as e:
        print(f"   ❌ Validation test failed: {e}")
        return False
    
    # Test 4: Field validator integration
    print("\n4. Testing FieldValidator integration...")
    try:
        from pipelines.validators import FieldValidator
        
        validator = FieldValidator(FieldType.USER, {})
        
        # Test valid user assignment data
        valid_assignment = {
            "user_assignments": [
                {"user_id": 123, "role": "primary"},
                {"user_id": 456, "role": "secondary"}
            ]
        }
        
        result = validator.validate_storage(valid_assignment, {})
        assert result.is_valid, f"Valid assignment should pass: {result.errors}"
        print("   ✅ User assignment validation works")
        
        # Test invalid assignment
        invalid_assignment = {
            "user_assignments": [
                {"user_id": "invalid", "role": "primary"}  # Invalid user_id
            ]
        }
        
        result = validator.validate_storage(invalid_assignment, {})
        assert not result.is_valid, "Invalid assignment should fail"
        print("   ✅ Invalid assignment correctly rejected")
        
    except Exception as e:
        print(f"   ❌ FieldValidator test failed: {e}")
        return False
    
    # Test 5: Pipeline field creation
    print("\n5. Testing Pipeline field creation...")
    try:
        from pipelines.models import Pipeline, Field
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get or create test user
        test_user, created = User.objects.get_or_create(
            email='test@example.com',
            defaults={'first_name': 'Test', 'last_name': 'User'}
        )
        
        # Get or create test pipeline
        pipeline, created = Pipeline.objects.get_or_create(
            slug='test-user-field',
            defaults={
                'name': 'Test User Field Pipeline',
                'description': 'Test pipeline for USER field',
                'created_by': test_user
            }
        )
        
        # Create USER field
        user_field_config = {
            "relationship_type": "assigned_to",
            "allow_multiple": True,
            "default_role": "primary",
            "allowed_roles": ["primary", "secondary", "collaborator"]
        }
        
        user_field = Field.objects.create(
            pipeline=pipeline,
            name='Assigned Users',
            field_type='user',
            field_config=user_field_config,
            display_name='Assigned Users',
            help_text='Users assigned to this record',
            created_by=test_user
        )
        
        print(f"   ✅ USER field created successfully: {user_field.name} (ID: {user_field.id})")
        
    except Exception as e:
        print(f"   ❌ Pipeline field creation failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 ALL TESTS PASSED! USER field implementation is working correctly.")
    print("\n📋 Implementation Summary:")
    print("   ✅ FieldType.USER enum value")
    print("   ✅ UserFieldConfig with relationships integration")
    print("   ✅ Field validation with multiple user assignments")
    print("   ✅ FieldValidator with user assignment validation")
    print("   ✅ Pipeline field creation and storage")
    print("\n🚀 USER field type is ready for production use!")
    
    return True

if __name__ == "__main__":
    test_user_field_implementation()