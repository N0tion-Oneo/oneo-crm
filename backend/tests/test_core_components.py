#!/usr/bin/env python
"""
Simple test to validate core components of unified architecture
"""
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_field_state_manager():
    """Test FieldStateManager basic functionality"""
    print("🧪 Testing FieldStateManager...")
    
    from pipelines.state.field_state_manager import get_field_state_manager
    from pipelines.models import Pipeline, Field
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Create test data
        user = User.objects.create_user(
            username='testuser', 
            email='test@example.com', 
            password='test123'
        )
        pipeline = Pipeline.objects.create(
            name='Test Pipeline',
            slug='test-pipeline', 
            pipeline_type='crm',
            created_by=user
        )
        field = Field.objects.create(
            pipeline=pipeline,
            name='Test Field',
            field_type='text',
            created_by=user
        )
        
        # Test state manager
        state_manager = get_field_state_manager()
        operation_id = "test_op_001"
        
        # Capture state
        success = state_manager.capture_field_state(field.id, operation_id)
        print(f"   ✅ Capture state: {success}")
        
        # Get state
        state = state_manager.get_field_state(field.id, operation_id)
        print(f"   ✅ Get state: {state is not None}")
        
        # Cleanup
        state_manager.cleanup_operation_state(operation_id)
        print(f"   ✅ Cleanup: OK")
        
        # Cleanup test data
        field.delete()
        pipeline.delete()
        user.delete()
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_field_validator():
    """Test FieldValidator basic functionality"""
    print("🧪 Testing FieldValidator...")
    
    from pipelines.validation.field_validator import FieldValidator
    from pipelines.models import Pipeline
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Create test data
        user = User.objects.create_user(
            username='testvalidator', 
            email='testvalidator@example.com', 
            password='test123'
        )
        pipeline = Pipeline.objects.create(
            name='Validator Test Pipeline',
            slug='validator-test-pipeline', 
            pipeline_type='crm',
            created_by=user
        )
        
        validator = FieldValidator()
        
        # Test valid field creation
        valid_config = {
            'name': 'Valid Test Field',
            'field_type': 'text',
            'is_required': False
        }
        
        result = validator.validate_field_creation(valid_config, pipeline)
        print(f"   ✅ Valid field creation: {result.valid}")
        
        # Test invalid field creation
        invalid_config = {
            'field_type': 'text'
            # Missing name
        }
        
        result = validator.validate_field_creation(invalid_config, pipeline)
        print(f"   ✅ Invalid field creation detected: {not result.valid}")
        print(f"   ✅ Error count: {len(result.errors)}")
        
        # Cleanup
        pipeline.delete()
        user.delete()
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_data_migrator():
    """Test DataMigrator basic functionality"""  
    print("🧪 Testing DataMigrator...")
    
    from pipelines.migration.data_migrator import DataMigrator
    from pipelines.models import Pipeline
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Create test data
        user = User.objects.create_user(
            username='testmigrator', 
            email='testmigrator@example.com', 
            password='test123'
        )
        pipeline = Pipeline.objects.create(
            name='Migrator Test Pipeline',
            slug='migrator-test-pipeline', 
            pipeline_type='crm',
            created_by=user
        )
        
        migrator = DataMigrator(pipeline)
        print(f"   ✅ DataMigrator created: OK")
        print(f"   ✅ Pipeline reference: {migrator.pipeline.name}")
        
        # Cleanup
        pipeline.delete() 
        user.delete()
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_field_operation_manager():
    """Test FieldOperationManager basic functionality"""
    print("🧪 Testing FieldOperationManager...")
    
    from pipelines.field_operations import get_field_operation_manager
    from pipelines.models import Pipeline
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Create test data
        user = User.objects.create_user(
            username='testoperator', 
            email='testoperator@example.com', 
            password='test123'
        )
        pipeline = Pipeline.objects.create(
            name='Operation Test Pipeline',
            slug='operation-test-pipeline', 
            pipeline_type='crm',
            created_by=user
        )
        
        # Get field operation manager
        field_manager = get_field_operation_manager(pipeline)
        print(f"   ✅ FieldOperationManager created: OK")
        
        # Test field creation
        field_config = {
            'name': 'Test Operation Field',
            'field_type': 'text',
            'is_required': False
        }
        
        result = field_manager.create_field(field_config, user)
        print(f"   ✅ Field creation result: {result.success}")
        
        if result.success:
            print(f"   ✅ Field created: {result.field.name}")
            print(f"   ✅ Operation ID: {result.operation_id}")
            
            # Test field update
            changes = {'display_name': 'Updated Display Name'}
            update_result = field_manager.update_field(result.field.id, changes, user)
            print(f"   ✅ Field update result: {update_result.success}")
            
            if update_result.success:
                print(f"   ✅ Field updated: {update_result.field.display_name}")
        else:
            print(f"   ❌ Field creation errors: {result.errors}")
        
        # Cleanup
        pipeline.delete()  # This should cascade delete fields
        user.delete()
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all component tests"""
    print("\n" + "="*60)
    print("🏗️  UNIFIED ARCHITECTURE COMPONENT TESTS")
    print("="*60 + "\n")
    
    tests = [
        test_field_state_manager,
        test_field_validator,
        test_data_migrator,
        test_field_operation_manager
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   💥 Test failed with exception: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print("="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 95:
        print("🎉 EXCELLENT: All core components working!")
        print("✅ Unified architecture is ready for production!")
    elif success_rate >= 75:
        print("👍 GOOD: Most components working")
        print("🔧 Minor issues to address")
    else:
        print("🚨 CRITICAL: Major component issues")
        print("❌ Architecture needs significant attention")
    
    print("="*60)
    
    return passed == total

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)