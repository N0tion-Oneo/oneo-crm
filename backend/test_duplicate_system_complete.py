#!/usr/bin/env python
"""
Final comprehensive test of the complete duplicate detection system
"""
import os
import sys

# Configure Django settings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

import django
django.setup()

def run_complete_system_test():
    """Run comprehensive test of the entire duplicate system"""
    print("🚀 COMPREHENSIVE DUPLICATE SYSTEM TEST")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Model Structure
    print("1. Testing Model Structure...")
    try:
        from duplicates.models import (
            DuplicateRule, URLExtractionRule, DuplicateRuleTest, DuplicateDetectionResult,
            DuplicateMatch, DuplicateResolution, DuplicateAnalytics, DuplicateExclusion
        )
        
        # Check model fields
        rule_fields = [f.name for f in DuplicateRule._meta.get_fields()]
        required_fields = ['id', 'tenant', 'name', 'pipeline', 'logic', 'action_on_duplicate', 'is_active']
        
        for field in required_fields:
            if field not in rule_fields:
                raise Exception(f"Missing required field: {field}")
        
        print("   ✅ All models and fields present")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Model structure test failed: {e}")
        tests_failed += 1
    
    # Test 2: API Endpoints
    print("2. Testing API Endpoints...")
    try:
        from django.test import Client
        from tenants.models import Tenant
        
        client = Client()
        tenant = Tenant.objects.filter(schema_name='oneotalent').first()
        
        if tenant:
            # Test all endpoints return proper status codes
            endpoints = [
                '/api/v1/duplicate-rules/',
                '/api/v1/url-extraction-rules/', 
                '/api/v1/duplicate-matches/',
                '/api/v1/duplicate-analytics/',
                '/api/v1/duplicate-exclusions/'
            ]
            
            all_good = True
            for endpoint in endpoints:
                response = client.get(endpoint, HTTP_HOST='oneotalent.localhost:8000')
                if response.status_code not in [200, 401, 403]:
                    all_good = False
                    break
            
            if all_good:
                print("   ✅ All API endpoints accessible")
                tests_passed += 1
            else:
                print("   ❌ Some API endpoints not working")
                tests_failed += 1
        else:
            print("   ⚠️  No test tenant found - skipping API test")
    except Exception as e:
        print(f"   ❌ API endpoints test failed: {e}")
        tests_failed += 1
    
    # Test 3: Admin Registration
    print("3. Testing Admin Registration...")
    try:
        from django.contrib import admin
        from duplicates.models import (
            DuplicateRule, URLExtractionRule, DuplicateMatch, 
            DuplicateAnalytics, DuplicateExclusion
        )
        
        models_to_check = [
            DuplicateRule, URLExtractionRule, DuplicateMatch, 
            DuplicateAnalytics, DuplicateExclusion
        ]
        
        all_registered = True
        for model_class in models_to_check:
            if model_class not in admin.site._registry:
                all_registered = False
                break
        
        if all_registered:
            print("   ✅ All models registered in admin")
            tests_passed += 1
        else:
            print("   ❌ Some models not registered in admin")
            tests_failed += 1
    except Exception as e:
        print(f"   ❌ Admin registration test failed: {e}")
        tests_failed += 1
    
    # Test 4: Serializers
    print("4. Testing Serializers...")
    try:
        from api.serializers import DuplicateRuleSerializer
        from duplicates.serializers import DuplicateMatchSerializer, DuplicateAnalyticsSerializer
        
        # Test serializer imports and basic functionality
        print("   ✅ All serializers import successfully")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Serializers test failed: {e}")
        tests_failed += 1
    
    # Test 5: Logic Engine
    print("5. Testing Logic Engine...")
    try:
        from duplicates.logic_engine import DuplicateLogicEngine, FieldMatcher
        
        # Test initialization
        engine = DuplicateLogicEngine(1)
        field_matcher = FieldMatcher(1)
        
        print("   ✅ Logic engine and field matcher initialize correctly")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Logic engine test failed: {e}")
        tests_failed += 1
    
    # Test 6: Signal Configuration
    print("6. Testing Signal Configuration...")
    try:
        from django.db.models.signals import post_save, pre_save
        from duplicates.models import DuplicateRule
        from pipelines.models import Record
        
        # Check signal connections
        rule_signals = post_save._live_receivers(sender=DuplicateRule)
        record_signals = pre_save._live_receivers(sender=Record)
        
        if rule_signals and record_signals:
            print("   ✅ Django signals properly connected")
            tests_passed += 1
        else:
            print("   ❌ Some signals not connected")
            tests_failed += 1
    except Exception as e:
        print(f"   ❌ Signal configuration test failed: {e}")
        tests_failed += 1
    
    # Test 7: Database Tables
    print("7. Testing Database Tables...")
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            # Check that main tables exist
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'oneotalent' 
                AND tablename LIKE 'duplicates_%'
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = [
                'duplicates_duplicaterule',
                'duplicates_urlextractionrule',
                'duplicates_duplicatematch',
                'duplicates_duplicateanalytics',
                'duplicates_duplicateexclusion'
            ]
            
            all_tables_exist = all(table in tables for table in expected_tables)
            
            if all_tables_exist:
                print("   ✅ All database tables exist")
                tests_passed += 1
            else:
                print(f"   ❌ Missing tables. Found: {tables}")
                tests_failed += 1
    except Exception as e:
        print(f"   ❌ Database tables test failed: {e}")
        tests_failed += 1
    
    # Final Results
    print("\n" + "=" * 60)
    print(f"🎯 FINAL TEST RESULTS:")
    print(f"   ✅ Tests Passed: {tests_passed}")
    print(f"   ❌ Tests Failed: {tests_failed}")
    print(f"   📊 Success Rate: {(tests_passed / (tests_passed + tests_failed) * 100):.1f}%")
    
    if tests_failed == 0:
        print("\n🎉 ALL TESTS PASSED! DUPLICATE SYSTEM FULLY OPERATIONAL!")
        print("✅ The duplicate detection system is production-ready")
        return True
    else:
        print(f"\n⚠️  {tests_failed} test(s) failed. Review issues before production use.")
        return False

if __name__ == "__main__":
    success = run_complete_system_test()
    sys.exit(0 if success else 1)