#!/usr/bin/env python
"""
Test record operations to identify what's broken
"""
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_record_validation():
    """Test record validation functionality"""
    print("🧪 Testing Record Validation...")
    
    try:
        from pipelines.models import Pipeline, Record, Field
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Create test user if doesn't exist
        try:
            user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
        
        # Create test pipeline
        try:
            pipeline = Pipeline.objects.get(slug='test-record-pipeline')
        except Pipeline.DoesNotExist:
            pipeline = Pipeline.objects.create(
                name='Test Record Pipeline',
                slug='test-record-pipeline',
                pipeline_type='crm',
                created_by=user
            )
        
        # Create a simple text field
        try:
            field = Field.objects.get(pipeline=pipeline, slug='test_field')
        except Field.DoesNotExist:
            field = Field.objects.create(
                pipeline=pipeline,
                name='Test Field',
                field_type='text',
                created_by=user
            )
        
        print(f"   ✅ Test setup: Pipeline {pipeline.name}, Field {field.name}")
        
        # Test basic record creation
        try:
            record_data = {field.slug: 'test value'}
            record = Record(
                pipeline=pipeline,
                title='Test Record',
                data=record_data,
                created_by=user
            )
            
            # This should trigger validation
            record.save()
            print(f"   ✅ Record creation successful: {record.id}")
            
            # Test record update
            record.data[field.slug] = 'updated value'
            record.save()
            print(f"   ✅ Record update successful")
            
            # Test record deletion
            record.soft_delete(user)
            print(f"   ✅ Record soft delete successful")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Record operations failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"   ❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_field_validation():
    """Test field validation that might be affecting records"""
    print("🧪 Testing Field Validation...")
    
    try:
        from pipelines.validators import validate_record_data
        from pipelines.field_types import FieldType
        
        # Test basic validation
        field_definitions = [{
            'slug': 'test_field',
            'field_type': 'text',
            'field_config': {'max_length': 100},
            'storage_constraints': {},
            'business_rules': {}
        }]
        
        record_data = {'test_field': 'test value'}
        
        result = validate_record_data(field_definitions, record_data, 'storage')
        print(f"   ✅ Validation result: {result}")
        
        if result.get('is_valid', False):
            print(f"   ✅ Validation successful")
            return True
        else:
            print(f"   ❌ Validation failed: {result.get('errors', {})}")
            return False
            
    except Exception as e:
        print(f"   ❌ Field validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports():
    """Test that all necessary imports work"""
    print("🧪 Testing Imports...")
    
    imports_to_test = [
        ('pipelines.models', ['Pipeline', 'Record', 'Field']),
        ('pipelines.validators', ['validate_record_data']),
        ('pipelines.field_types', ['FieldType']),
        ('pipelines.serializers', ['RecordSerializer']),
    ]
    
    all_success = True
    
    for module_name, classes in imports_to_test:
        try:
            module = __import__(module_name, fromlist=classes)
            
            for class_name in classes:
                if hasattr(module, class_name):
                    print(f"   ✅ {module_name}.{class_name}: OK")
                else:
                    print(f"   ❌ {module_name}.{class_name}: NOT FOUND")
                    all_success = False
                    
        except Exception as e:
            print(f"   ❌ {module_name}: IMPORT FAILED - {e}")
            all_success = False
    
    return all_success

def test_record_serializer():
    """Test record serializer functionality"""
    print("🧪 Testing Record Serializer...")
    
    try:
        from pipelines.serializers import RecordSerializer, RecordCreateSerializer
        from pipelines.models import Pipeline
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get test user and pipeline
        try:
            user = User.objects.get(username='testuser')
            pipeline = Pipeline.objects.get(slug='test-record-pipeline')
        except (User.DoesNotExist, Pipeline.DoesNotExist):
            print("   ⚠️  Test data not available, skipping serializer test")
            return True
        
        # Test serializer instantiation
        serializer = RecordSerializer()
        print(f"   ✅ RecordSerializer instantiated")
        
        create_serializer = RecordCreateSerializer()
        print(f"   ✅ RecordCreateSerializer instantiated")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Record serializer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic tests"""
    print("\n" + "="*60)
    print("🔍 RECORD OPERATIONS DIAGNOSTIC")
    print("="*60 + "\n")
    
    tests = [
        test_imports,
        test_field_validation,
        test_record_serializer,
        test_record_validation,
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
    print("📊 DIAGNOSTIC RESULTS")
    print("="*60)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("🎉 All tests passed - record operations should work!")
        print("✅ The issue might be frontend or API-related")
    elif success_rate >= 75:
        print("👍 Most functionality working")
        print("🔧 Some components need attention")
    else:
        print("🚨 CRITICAL: Major backend issues detected")
        print("❌ Record operations are broken")
    
    print("="*60)
    
    return passed == total

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)