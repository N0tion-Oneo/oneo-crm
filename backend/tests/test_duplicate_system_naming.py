#!/usr/bin/env python
"""
Test script to validate duplicate system naming changes before migration
"""
import os
import sys
import django
from django.conf import settings

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_model_imports():
    """Test that all model imports work correctly"""
    print("🧪 Testing model imports...")
    
    try:
        from duplicates.models import (
            DuplicateRule, URLExtractionRule, DuplicateRuleTest, DuplicateDetectionResult,
            DuplicateMatch, DuplicateResolution, DuplicateAnalytics, DuplicateExclusion
        )
        print("✅ All duplicate models import successfully")
        
        # Test that old imports fail (as expected)
        try:
            from duplicates.rule_models import SimpleDuplicateRule
            print("❌ ERROR: Old rule_models.py import should fail but didn't!")
            return False
        except ImportError:
            print("✅ Old rule_models.py import correctly fails (expected)")
            
        return True
    except ImportError as e:
        print(f"❌ ERROR: Model import failed: {e}")
        return False

def test_serializer_imports():
    """Test that serializer imports work correctly"""
    print("\n🧪 Testing serializer imports...")
    
    try:
        from duplicates.serializers import (
            DuplicateMatchSerializer, DuplicateResolutionSerializer, 
            DuplicateAnalyticsSerializer, DuplicateExclusionSerializer
        )
        print("✅ Duplicate serializers import successfully")
        
        from api.serializers import (
            DuplicateRuleSerializer, URLExtractionRuleSerializer, DuplicateRuleTestSerializer
        )
        print("✅ API serializers import successfully")
        
        return True
    except ImportError as e:
        print(f"❌ ERROR: Serializer import failed: {e}")
        return False

def test_view_imports():
    """Test that view imports work correctly"""
    print("\n🧪 Testing view imports...")
    
    try:
        from api.views.duplicates import (
            DuplicateRuleViewSet, URLExtractionRuleViewSet, DuplicateRuleTestViewSet,
            DuplicateMatchViewSet, DuplicateAnalyticsViewSet, DuplicateExclusionViewSet
        )
        print("✅ All duplicate ViewSets import successfully")
        
        return True
    except ImportError as e:
        print(f"❌ ERROR: View import failed: {e}")
        return False

def test_admin_imports():
    """Test that admin imports work correctly"""
    print("\n🧪 Testing admin imports...")
    
    try:
        from duplicates.admin import (
            DuplicateRuleAdmin, URLExtractionRuleAdmin, DuplicateRuleTestAdmin,
            DuplicateMatchAdmin, DuplicateAnalyticsAdmin, DuplicateExclusionAdmin
        )
        print("✅ All duplicate admin classes import successfully")
        
        return True
    except ImportError as e:
        print(f"❌ ERROR: Admin import failed: {e}")
        return False

def test_model_relationships():
    """Test that model relationships are correctly defined"""
    print("\n🧪 Testing model relationships...")
    
    try:
        from duplicates.models import DuplicateRule, DuplicateMatch, DuplicateAnalytics
        from tenants.models import Tenant
        from pipelines.models import Pipeline
        
        # Test field existence and relationships
        duplicate_rule_fields = [f.name for f in DuplicateRule._meta.get_fields()]
        expected_fields = ['id', 'tenant', 'name', 'description', 'pipeline', 'logic', 'action_on_duplicate', 'is_active', 'created_at', 'updated_at', 'created_by']
        
        for field in expected_fields:
            if field not in duplicate_rule_fields:
                print(f"❌ ERROR: DuplicateRule missing field: {field}")
                return False
        
        print("✅ DuplicateRule has all expected fields")
        
        # Test foreign key relationships
        tenant_field = DuplicateRule._meta.get_field('tenant')
        if tenant_field.related_model != Tenant:
            print("❌ ERROR: DuplicateRule.tenant relationship incorrect")
            return False
        
        pipeline_field = DuplicateRule._meta.get_field('pipeline')
        if pipeline_field.related_model != Pipeline:
            print("❌ ERROR: DuplicateRule.pipeline relationship incorrect")
            return False
            
        print("✅ DuplicateRule relationships are correct")
        
        # Test DuplicateMatch relationship to DuplicateRule
        rule_field = DuplicateMatch._meta.get_field('rule')
        if rule_field.related_model != DuplicateRule:
            print("❌ ERROR: DuplicateMatch.rule relationship incorrect")
            return False
            
        print("✅ DuplicateMatch.rule relationship is correct")
        
        return True
    except Exception as e:
        print(f"❌ ERROR: Model relationship test failed: {e}")
        return False

def test_url_configuration():
    """Test that URL configuration is correct"""
    print("\n🧪 Testing URL configuration...")
    
    try:
        from api.urls import router
        
        # Get registered URL patterns
        url_patterns = [pattern.pattern._regex for pattern in router.urls if hasattr(pattern.pattern, '_regex')]
        
        # Check for duplicate-rules endpoint
        duplicate_rules_found = any('duplicate-rules' in str(pattern) for pattern in url_patterns)
        if not duplicate_rules_found:
            print("❌ ERROR: duplicate-rules endpoint not found in URL configuration")
            return False
            
        print("✅ duplicate-rules endpoint found in URL configuration")
        
        return True
    except Exception as e:
        print(f"❌ ERROR: URL configuration test failed: {e}")
        return False

def test_signal_configuration():
    """Test that signal handlers are correctly configured"""
    print("\n🧪 Testing signal configuration...")
    
    try:
        import duplicates.signals
        from django.db.models.signals import post_save, pre_save
        from duplicates.models import DuplicateRule
        from pipelines.models import Record
        
        # Check that signals are connected
        post_save_receivers = post_save._live_receivers(sender=DuplicateRule)
        if not post_save_receivers:
            print("❌ ERROR: No post_save signal receivers found for DuplicateRule")
            return False
            
        print("✅ DuplicateRule post_save signal is connected")
        
        pre_save_receivers = pre_save._live_receivers(sender=Record)
        if not pre_save_receivers:
            print("❌ ERROR: No pre_save signal receivers found for Record")
            return False
            
        print("✅ Record pre_save signal is connected")
        
        return True
    except Exception as e:
        print(f"❌ ERROR: Signal configuration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 TESTING DUPLICATE SYSTEM NAMING CHANGES")
    print("=" * 50)
    
    tests = [
        test_model_imports,
        test_serializer_imports,
        test_view_imports,
        test_admin_imports,
        test_model_relationships,
        test_url_configuration,
        test_signal_configuration,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 TEST RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ ALL TESTS PASSED! Ready for migration.")
        return True
    else:
        print("❌ SOME TESTS FAILED! Fix issues before migration.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)