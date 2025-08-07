#!/usr/bin/env python
"""
Comprehensive test runner for the unified field management architecture

This script runs all tests for the new unified system and provides detailed reporting.
"""
import os
import sys
import django
import time
import subprocess
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

# Add the project root to the Python path
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.test.utils import get_runner
from django.conf import settings
from django.core.management import call_command


class UnifiedArchitectureTestRunner:
    """
    Comprehensive test runner for unified field management architecture
    """
    
    def __init__(self):
        self.test_modules = [
            'tests.test_unified_field_management',
            'tests.test_field_validator', 
            'tests.test_data_migrator',
            'tests.test_unified_api_integration'
        ]
        
        self.results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0,
            'execution_time': 0,
            'module_results': {},
            'detailed_results': []
        }
    
    def print_header(self):
        """Print test runner header"""
        print("\n" + "="*80)
        print("🧪 UNIFIED FIELD MANAGEMENT ARCHITECTURE - COMPREHENSIVE TEST SUITE")
        print("="*80)
        print(f"Testing {len(self.test_modules)} test modules...")
        print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")
    
    def print_module_header(self, module_name):
        """Print header for individual test module"""
        print(f"\n📋 Testing Module: {module_name}")
        print("-" * 60)
    
    def run_module_tests(self, module_name):
        """Run tests for a specific module"""
        self.print_module_header(module_name)
        
        # Capture test output
        output_buffer = StringIO()
        error_buffer = StringIO()
        
        start_time = time.time()
        
        try:
            # Run tests with Django test runner
            TestRunner = get_runner(settings)
            test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
            
            with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                result = test_runner.run_tests([module_name])
            
            execution_time = time.time() - start_time
            
            # Parse results (simplified - Django test runner doesn't provide detailed stats easily)
            output = output_buffer.getvalue()
            error_output = error_buffer.getvalue()
            
            # Count test results from output
            passed = output.count('ok')
            failed = output.count('FAIL')
            errors = output.count('ERROR')
            skipped = output.count('skip')
            
            module_result = {
                'module': module_name,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'skipped': skipped,
                'execution_time': execution_time,
                'output': output,
                'error_output': error_output,
                'django_result': result
            }
            
            self.results['module_results'][module_name] = module_result
            
            # Update totals
            self.results['total_tests'] += passed + failed + errors + skipped
            self.results['passed'] += passed
            self.results['failed'] += failed
            self.results['errors'] += errors
            self.results['skipped'] += skipped
            self.results['execution_time'] += execution_time
            
            # Print module summary
            if result == 0:  # Success
                print(f"✅ {module_name}: PASSED ({passed} tests, {execution_time:.2f}s)")
            else:  # Failure
                print(f"❌ {module_name}: FAILED ({failed} failed, {errors} errors, {execution_time:.2f}s)")
                if error_output:
                    print(f"   Errors: {error_output[:200]}...")
            
            return module_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_result = {
                'module': module_name,
                'passed': 0,
                'failed': 0,
                'errors': 1,
                'skipped': 0,
                'execution_time': execution_time,
                'output': '',
                'error_output': str(e),
                'exception': e
            }
            
            self.results['module_results'][module_name] = error_result
            self.results['errors'] += 1
            self.results['execution_time'] += execution_time
            
            print(f"💥 {module_name}: EXCEPTION - {str(e)}")
            
            return error_result
    
    def run_all_tests(self):
        """Run all test modules"""
        self.print_header()
        
        overall_start_time = time.time()
        
        for module in self.test_modules:
            result = self.run_module_tests(module)
            self.results['detailed_results'].append(result)
        
        self.results['total_execution_time'] = time.time() - overall_start_time
        
        return self.results
    
    def print_detailed_summary(self):
        """Print detailed test results summary"""
        print("\n" + "="*80)
        print("📊 DETAILED TEST RESULTS SUMMARY")
        print("="*80)
        
        # Overall statistics
        total = self.results['total_tests']
        passed = self.results['passed']
        failed = self.results['failed']
        errors = self.results['errors']
        skipped = self.results['skipped']
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n🔢 Overall Statistics:")
        print(f"   Total Tests:    {total}")
        print(f"   ✅ Passed:      {passed}")
        print(f"   ❌ Failed:      {failed}")
        print(f"   💥 Errors:      {errors}")
        print(f"   ⏭️  Skipped:     {skipped}")
        print(f"   📈 Success Rate: {success_rate:.1f}%")
        print(f"   ⏱️  Total Time:   {self.results['total_execution_time']:.2f}s")
        
        # Module breakdown
        print(f"\n📋 Module Breakdown:")
        for module, result in self.results['module_results'].items():
            module_total = result['passed'] + result['failed'] + result['errors'] + result['skipped']
            module_success_rate = (result['passed'] / module_total * 100) if module_total > 0 else 0
            
            status_icon = "✅" if result['failed'] + result['errors'] == 0 else "❌"
            
            print(f"   {status_icon} {module}:")
            print(f"      Tests: {module_total} | Passed: {result['passed']} | Failed: {result['failed']} | Errors: {result['errors']}")
            print(f"      Success Rate: {module_success_rate:.1f}% | Time: {result['execution_time']:.2f}s")
        
        # Architecture validation
        print(f"\n🏗️ Architecture Validation:")
        
        # Check if core components are tested
        core_components = [
            'FieldOperationManager',
            'FieldValidator', 
            'DataMigrator',
            'FieldStateManager',
            'API Integration'
        ]
        
        components_tested = 0
        for component in core_components:
            # Check if component appears in test module names or outputs
            tested = any(component.lower().replace(' ', '_') in module.lower() or 
                        component.lower() in str(result.get('output', '')).lower()
                        for module, result in self.results['module_results'].items())
            
            status = "✅" if tested else "❌"
            print(f"   {status} {component}: {'Tested' if tested else 'Not Tested'}")
            if tested:
                components_tested += 1
        
        architecture_coverage = (components_tested / len(core_components) * 100)
        print(f"   📊 Architecture Coverage: {architecture_coverage:.1f}%")
        
        return self.results
    
    def print_failure_details(self):
        """Print detailed information about failures"""
        has_failures = any(
            result['failed'] > 0 or result['errors'] > 0 
            for result in self.results['module_results'].values()
        )
        
        if not has_failures:
            return
        
        print("\n" + "="*80)
        print("🔍 FAILURE DETAILS")
        print("="*80)
        
        for module, result in self.results['module_results'].items():
            if result['failed'] > 0 or result['errors'] > 0:
                print(f"\n❌ {module}:")
                
                if result.get('error_output'):
                    print("   Error Output:")
                    error_lines = result['error_output'].split('\n')[:10]  # First 10 lines
                    for line in error_lines:
                        if line.strip():
                            print(f"     {line}")
                
                if result.get('output'):
                    # Extract failure information from output
                    output_lines = result['output'].split('\n')
                    failure_lines = [line for line in output_lines if 'FAIL' in line or 'ERROR' in line]
                    if failure_lines:
                        print("   Failed Tests:")
                        for line in failure_lines[:5]:  # First 5 failures
                            print(f"     {line.strip()}")
    
    def print_recommendations(self):
        """Print recommendations based on test results"""
        print("\n" + "="*80)
        print("💡 RECOMMENDATIONS")
        print("="*80)
        
        total = self.results['total_tests']
        passed = self.results['passed']
        failed = self.results['failed']
        errors = self.results['errors']
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        if success_rate >= 95:
            print("🎉 EXCELLENT: Test suite is in excellent condition!")
            print("   ✅ Architecture is well-tested and stable")
            print("   ✅ Ready for production deployment")
            
        elif success_rate >= 85:
            print("👍 GOOD: Test suite is in good condition")
            print("   ✅ Architecture is mostly stable") 
            print("   🔧 Consider fixing remaining failures before deployment")
            
        elif success_rate >= 70:
            print("⚠️ MODERATE: Test suite needs attention")
            print("   🔧 Several issues need to be addressed")
            print("   ❌ Not recommended for production deployment")
            
        else:
            print("🚨 CRITICAL: Test suite has significant issues")
            print("   ❌ Major problems with the architecture")
            print("   🛠️ Requires immediate attention before deployment")
        
        # Specific recommendations
        print(f"\n🎯 Specific Actions:")
        
        if failed > 0:
            print(f"   🔧 Fix {failed} failing tests")
        
        if errors > 0:
            print(f"   💥 Resolve {errors} error conditions")
        
        if self.results['total_execution_time'] > 60:
            print(f"   ⚡ Optimize test performance (currently {self.results['total_execution_time']:.1f}s)")
        
        # Check architecture-specific recommendations
        failed_modules = [
            module for module, result in self.results['module_results'].items()
            if result['failed'] > 0 or result['errors'] > 0
        ]
        
        if any('field_operation' in module for module in failed_modules):
            print("   🏗️ FieldOperationManager needs attention - core functionality affected")
        
        if any('validator' in module for module in failed_modules):
            print("   ✅ Field validation system needs fixes - data integrity at risk")
        
        if any('migrator' in module for module in failed_modules):
            print("   🔄 Data migration system needs attention - schema changes may fail")
        
        if any('api' in module for module in failed_modules):
            print("   🌐 API integration issues - external interfaces affected")
    
    def save_results_to_file(self):
        """Save detailed results to a file"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f'/Users/joshcowan/Oneo CRM/backend/test_results_{timestamp}.txt'
        
        try:
            with open(filename, 'w') as f:
                f.write("UNIFIED FIELD MANAGEMENT ARCHITECTURE - TEST RESULTS\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Test Run: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Tests: {self.results['total_tests']}\n")
                f.write(f"Passed: {self.results['passed']}\n")
                f.write(f"Failed: {self.results['failed']}\n")
                f.write(f"Errors: {self.results['errors']}\n")
                f.write(f"Execution Time: {self.results['total_execution_time']:.2f}s\n\n")
                
                f.write("MODULE DETAILS:\n")
                f.write("-" * 40 + "\n")
                
                for module, result in self.results['module_results'].items():
                    f.write(f"\n{module}:\n")
                    f.write(f"  Passed: {result['passed']}\n")
                    f.write(f"  Failed: {result['failed']}\n")
                    f.write(f"  Errors: {result['errors']}\n")
                    f.write(f"  Time: {result['execution_time']:.2f}s\n")
                    
                    if result.get('error_output'):
                        f.write(f"  Errors:\n")
                        for line in result['error_output'].split('\n')[:20]:
                            if line.strip():
                                f.write(f"    {line}\n")
            
            print(f"\n💾 Detailed results saved to: {filename}")
            
        except Exception as e:
            print(f"⚠️ Failed to save results to file: {e}")


def main():
    """Main test runner function"""
    runner = UnifiedArchitectureTestRunner()
    
    try:
        # Run all tests
        results = runner.run_all_tests()
        
        # Print comprehensive results
        runner.print_detailed_summary()
        runner.print_failure_details()
        runner.print_recommendations()
        
        # Save results
        runner.save_results_to_file()
        
        print("\n" + "="*80)
        print("🏁 TEST EXECUTION COMPLETED")
        print("="*80)
        
        # Return appropriate exit code
        if results['failed'] == 0 and results['errors'] == 0:
            print("🎉 ALL TESTS PASSED - UNIFIED ARCHITECTURE IS READY!")
            return 0
        else:
            print(f"⚠️  TESTS FAILED - {results['failed']} failures, {results['errors']} errors")
            return 1
            
    except KeyboardInterrupt:
        print("\n🛑 Test execution interrupted by user")
        return 2
    except Exception as e:
        print(f"\n💥 Test execution failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)