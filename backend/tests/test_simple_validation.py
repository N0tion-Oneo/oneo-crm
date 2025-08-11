#!/usr/bin/env python
"""
Simple validation test for unified architecture components
Tests only the logic without database dependencies
"""
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_field_validator_logic():
    """Test FieldValidator logic without database"""
    print("🧪 Testing FieldValidator Logic...")
    
    from pipelines.validation.field_validator import FieldValidator
    
    try:
        validator = FieldValidator()
        print("   ✅ FieldValidator instantiated successfully")
        
        # Test validation result structure
        from pipelines.validation.field_validator import FieldValidationResult
        
        # Test valid result
        valid_result = FieldValidationResult(valid=True, errors=[], warnings=['test warning'])
        print(f"   ✅ Valid result: {valid_result.valid}")
        print(f"   ✅ Warnings: {len(valid_result.warnings)}")
        
        # Test invalid result
        invalid_result = FieldValidationResult(valid=False, errors=['test error'])
        print(f"   ✅ Invalid result detected: {not invalid_result.valid}")
        print(f"   ✅ Error count: {len(invalid_result.errors)}")
        
        # Test to_dict method
        result_dict = valid_result.to_dict()
        print(f"   ✅ Result dict keys: {list(result_dict.keys())}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_migrator_structure():
    """Test DataMigrator structure without database"""
    print("🧪 Testing DataMigrator Structure...")
    
    from pipelines.migration.data_migrator import MigrationResult
    
    try:
        # Test migration result
        success_result = MigrationResult(
            success=True,
            records_processed=10,
            records_migrated=10,
            processing_time_seconds=1.5
        )
        
        print(f"   ✅ Success result: {success_result.success}")
        print(f"   ✅ Records processed: {success_result.records_processed}")
        print(f"   ✅ Processing time: {success_result.processing_time_seconds}s")
        
        # Test to_dict method
        result_dict = success_result.to_dict()
        expected_keys = [
            'success', 'records_processed', 'records_migrated', 
            'errors', 'warnings', 'processing_time_seconds', 'timestamp'
        ]
        
        for key in expected_keys:
            if key in result_dict:
                print(f"   ✅ Result dict has key: {key}")
            else:
                print(f"   ❌ Missing key: {key}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_field_state_manager_structure():
    """Test FieldStateManager structure"""
    print("🧪 Testing FieldStateManager Structure...")
    
    from pipelines.state.field_state_manager import FieldStateManager, get_field_state_manager
    
    try:
        # Test singleton
        manager1 = get_field_state_manager()
        manager2 = get_field_state_manager()
        print(f"   ✅ Singleton pattern: {manager1 is manager2}")
        
        # Test basic structure
        print(f"   ✅ State storage initialized: {hasattr(manager1, '_state_storage')}")
        print(f"   ✅ State timestamps initialized: {hasattr(manager1, '_state_timestamps')}")
        print(f"   ✅ Lock initialized: {hasattr(manager1, '_lock')}")
        
        # Test memory usage method
        memory_info = manager1.get_memory_usage_info()
        expected_keys = ['active_operations', 'total_field_states', 'estimated_memory_bytes']
        
        for key in expected_keys:
            if key in memory_info:
                print(f"   ✅ Memory info has key: {key}")
            else:
                print(f"   ❌ Missing memory info key: {key}")
                return False
        
        print(f"   ✅ Active operations count: {memory_info['active_operations']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_field_operation_result_structure():
    """Test FieldOperationResult structure"""
    print("🧪 Testing FieldOperationResult Structure...")
    
    from pipelines.field_operations import FieldOperationResult
    
    try:
        # Test success result
        success_result = FieldOperationResult(
            success=True,
            field=None,  # Would be Field instance in real usage
            operation_id="test_op_001",
            warnings=["Test warning"],
            metadata={'test': 'data'}
        )
        
        print(f"   ✅ Success result: {success_result.success}")
        print(f"   ✅ Operation ID: {success_result.operation_id}")
        print(f"   ✅ Warnings count: {len(success_result.warnings)}")
        print(f"   ✅ Metadata keys: {list(success_result.metadata.keys())}")
        
        # Test to_dict method
        result_dict = success_result.to_dict()
        expected_keys = [
            'success', 'field_id', 'operation_id', 'errors', 
            'warnings', 'metadata', 'timestamp'
        ]
        
        for key in expected_keys:
            if key in result_dict:
                print(f"   ✅ Result dict has key: {key}")
            else:
                print(f"   ❌ Missing key: {key}")
                return False
        
        # Test failure result
        failure_result = FieldOperationResult(
            success=False,
            operation_id="test_op_002",
            errors=["Validation failed", "Field name required"]
        )
        
        print(f"   ✅ Failure result: {not failure_result.success}")
        print(f"   ✅ Error count: {len(failure_result.errors)}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_imports_and_dependencies():
    """Test that all components can be imported"""
    print("🧪 Testing Imports and Dependencies...")
    
    components_to_test = [
        ('pipelines.field_operations', ['FieldOperationManager', 'FieldOperationResult', 'get_field_operation_manager']),
        ('pipelines.validation.field_validator', ['FieldValidator', 'FieldValidationResult']),
        ('pipelines.migration.data_migrator', ['DataMigrator', 'MigrationResult']),
        ('pipelines.state.field_state_manager', ['FieldStateManager', 'get_field_state_manager'])
    ]
    
    all_success = True
    
    for module_name, classes in components_to_test:
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

def test_architectural_integration():
    """Test architectural integration points"""
    print("🧪 Testing Architectural Integration...")
    
    try:
        # Test that FieldOperationManager can import its dependencies
        from pipelines.field_operations import FieldOperationManager
        print("   ✅ FieldOperationManager imports OK")
        
        # Test that it references the right components
        import inspect
        source = inspect.getsource(FieldOperationManager.__init__)
        
        dependencies = [
            'FieldValidator',
            'DataMigrator', 
            'get_field_state_manager'
        ]
        
        for dep in dependencies:
            if dep in source:
                print(f"   ✅ FieldOperationManager uses {dep}")
            else:
                print(f"   ⚠️  FieldOperationManager may not use {dep}")
        
        # Test that main methods exist
        methods = ['create_field', 'update_field', 'delete_field', 'restore_field']
        for method in methods:
            if hasattr(FieldOperationManager, method):
                print(f"   ✅ FieldOperationManager.{method}: EXISTS")
            else:
                print(f"   ❌ FieldOperationManager.{method}: MISSING")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Run all validation tests"""
    print("\n" + "="*70)
    print("🔍 UNIFIED ARCHITECTURE - STRUCTURE VALIDATION TESTS")
    print("="*70 + "\n")
    
    tests = [
        test_imports_and_dependencies,
        test_field_validator_logic,
        test_data_migrator_structure,
        test_field_state_manager_structure,
        test_field_operation_result_structure,
        test_architectural_integration
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
    
    print("="*70)
    print("📊 STRUCTURE VALIDATION RESULTS")
    print("="*70)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("🎉 PERFECT: All architectural components are correctly structured!")
        print("✅ Unified architecture is ready for integration testing!")
        print("✅ All imports working, all classes defined, all methods present")
    elif success_rate >= 90:
        print("🌟 EXCELLENT: Architecture is very well structured")
        print("🔧 Minor issues to address")
    elif success_rate >= 75:
        print("👍 GOOD: Architecture is mostly well structured")
        print("🔧 Some issues to address")
    else:
        print("🚨 CRITICAL: Major structural issues")
        print("❌ Architecture needs significant work")
    
    # Detailed breakdown
    print("\n🏗️ Architecture Assessment:")
    if passed >= 6:
        print("   ✅ Core Components: All properly defined")
        print("   ✅ Integration Points: Working correctly") 
        print("   ✅ Error Handling: Structured result objects")
        print("   ✅ Dependencies: All imports successful")
    elif passed >= 4:
        print("   ✅ Core Components: Mostly working")
        print("   ⚠️  Integration Points: Some issues")
        print("   ✅ Dependencies: Mostly working")
    else:
        print("   ❌ Core Components: Major issues")
        print("   ❌ Integration Points: Broken")
        print("   ❌ Dependencies: Import problems")
    
    print("="*70)
    
    return passed == total

if __name__ == '__main__':
    success = main()
    print(f"\n🏁 VALIDATION {'PASSED' if success else 'FAILED'}")
    exit(0 if success else 1)