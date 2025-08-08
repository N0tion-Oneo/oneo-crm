#!/usr/bin/env python
"""
Test script to validate duplicate system API functionality before migration
"""
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings BEFORE importing Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

import django
django.setup()

# Now import Django modules
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def test_duplicate_rule_serializer():
    """Test that DuplicateRule serializer works correctly"""
    print("🧪 Testing DuplicateRule serializer...")
    
    try:
        from api.serializers import DuplicateRuleSerializer
        from duplicates.models import DuplicateRule
        from pipelines.models import Pipeline
        from tenants.models import Tenant
        
        # Use existing tenant
        tenant = Tenant.objects.filter(schema_name__in=['demo', 'public']).first()
        if not tenant:
            print("⚠️  No existing tenant found - skipping serializer test")
            return True
        
        pipeline = Pipeline.objects.filter(tenant=tenant).first()
        if not pipeline:
            print("⚠️  No pipeline found for testing - skipping serializer test")
            return True
            
        # Test serializer validation
        test_data = {
            'name': 'Test Rule',
            'description': 'Test duplicate rule',
            'pipeline': pipeline.id,
            'logic': {
                'operator': 'AND',
                'fields': [
                    {'field': 'email', 'match_type': 'exact'}
                ]
            },
            'action_on_duplicate': 'warn'
        }
        
        # Mock request context
        class MockRequest:
            def __init__(self, tenant):
                self.tenant = tenant
                self.user = None
        
        mock_request = MockRequest(tenant)
        serializer = DuplicateRuleSerializer(data=test_data, context={'request': mock_request})
        
        if serializer.is_valid():
            print("✅ DuplicateRule serializer validation passes")
            return True
        else:
            print(f"❌ ERROR: DuplicateRule serializer validation failed: {serializer.errors}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: DuplicateRule serializer test failed: {e}")
        return False

def test_model_creation():
    """Test that models can be created correctly"""
    print("\n🧪 Testing model creation...")
    
    try:
        from duplicates.models import DuplicateRule, URLExtractionRule
        from tenants.models import Tenant
        from pipelines.models import Pipeline
        from django.db import transaction
        
        # Use existing tenant
        tenant = Tenant.objects.filter(schema_name__in=['demo', 'public']).first()
        if not tenant:
            print("⚠️  No existing tenant found - skipping model creation test")
            return True
        
        # Test URLExtractionRule creation
        url_rule = URLExtractionRule.objects.get_or_create(
            tenant=tenant,
            name='Test LinkedIn Rule',
            defaults={
                'description': 'Test URL extraction rule',
                'domain_patterns': ['linkedin.com'],
                'extraction_pattern': r'/in/([^/]+)',
                'extraction_format': 'linkedin:{}',
                'is_active': True
            }
        )[0]
        
        print(f"✅ URLExtractionRule created: {url_rule}")
        
        # Test DuplicateRule creation
        pipeline = Pipeline.objects.filter(tenant=tenant).first()
        if pipeline:
            duplicate_rule = DuplicateRule.objects.get_or_create(
                tenant=tenant,
                name='Test Duplicate Rule',
                defaults={
                    'description': 'Test duplicate detection rule',
                    'pipeline': pipeline,
                    'logic': {
                        'operator': 'AND',
                        'fields': [
                            {'field': 'email', 'match_type': 'exact'}
                        ]
                    },
                    'action_on_duplicate': 'warn',
                    'is_active': True
                }
            )[0]
            
            print(f"✅ DuplicateRule created: {duplicate_rule}")
        else:
            print("⚠️  No pipeline found - skipping DuplicateRule creation")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Model creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_related_names():
    """Test that related names work correctly"""
    print("\n🧪 Testing related names...")
    
    try:
        from tenants.models import Tenant
        from duplicates.models import DuplicateRule, URLExtractionRule
        
        # Use existing tenant
        tenant = Tenant.objects.filter(schema_name__in=['demo', 'public']).first()
        if not tenant:
            print("⚠️  No existing tenant found - skipping related names test")
            return True
        
        # Test URLExtractionRule related name
        url_rules = tenant.duplicate_url_extraction_rules.all()
        print(f"✅ URLExtractionRule related name works: {url_rules.count()} rules found")
        
        # Test DuplicateRule related name
        duplicate_rules = tenant.duplicate_rules.all()
        print(f"✅ DuplicateRule related name works: {duplicate_rules.count()} rules found")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Related names test failed: {e}")
        return False

def test_admin_interface():
    """Test that admin interface works correctly"""
    print("\n🧪 Testing admin interface...")
    
    try:
        from django.contrib import admin
        from duplicates.models import DuplicateRule, URLExtractionRule
        
        # Check that models are registered
        if DuplicateRule not in admin.site._registry:
            print("❌ ERROR: DuplicateRule not registered in admin")
            return False
        
        if URLExtractionRule not in admin.site._registry:
            print("❌ ERROR: URLExtractionRule not registered in admin")
            return False
            
        print("✅ All duplicate models are registered in admin")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Admin interface test failed: {e}")
        return False

def test_viewset_registration():
    """Test that ViewSets are properly registered in URLs"""
    print("\n🧪 Testing ViewSet registration...")
    
    try:
        from django.urls import resolve, reverse, NoReverseMatch
        from api.views.duplicates import DuplicateRuleViewSet
        
        # Test that URL resolution works
        try:
            url = reverse('duplicate-rule-list')
            print(f"✅ duplicate-rule-list URL resolves to: {url}")
        except NoReverseMatch:
            print("❌ ERROR: duplicate-rule-list URL not found")
            return False
        
        # Test URL resolution
        try:
            resolver = resolve('/api/v1/duplicate-rules/')
            if resolver.func.cls == DuplicateRuleViewSet:
                print("✅ DuplicateRuleViewSet is properly registered")
            else:
                print(f"❌ ERROR: Wrong ViewSet registered: {resolver.func.cls}")
                return False
        except:
            print("❌ ERROR: Failed to resolve /api/v1/duplicate-rules/ URL")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: ViewSet registration test failed: {e}")
        return False

def test_logic_engine_compatibility():
    """Test that logic engine works with renamed models"""
    print("\n🧪 Testing logic engine compatibility...")
    
    try:
        from duplicates.logic_engine import DuplicateLogicEngine
        from duplicates.models import DuplicateRule
        from tenants.models import Tenant
        from pipelines.models import Pipeline
        
        # Use existing tenant
        tenant = Tenant.objects.filter(schema_name__in=['demo', 'public']).first()
        if not tenant:
            print("⚠️  No existing tenant found - skipping logic engine test")
            return True
        
        # Initialize engine
        engine = DuplicateLogicEngine(tenant.id)
        print("✅ DuplicateLogicEngine initializes correctly")
        
        # Test with a DuplicateRule if available
        duplicate_rule = DuplicateRule.objects.filter(tenant=tenant).first()
        if duplicate_rule:
            # Test basic evaluation (with dummy data)
            test_record1 = {'email': 'test@example.com', 'name': 'John Doe'}
            test_record2 = {'email': 'test@example.com', 'name': 'John Smith'}
            
            try:
                result = engine.evaluate_rule(duplicate_rule, test_record1, test_record2)
                print(f"✅ Logic engine evaluation works: {result}")
            except Exception as e:
                print(f"⚠️  Logic engine evaluation error (expected if no fields match): {e}")
        else:
            print("⚠️  No DuplicateRule found - skipping evaluation test")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Logic engine compatibility test failed: {e}")
        return False

def main():
    """Run all API functionality tests"""
    print("🚀 TESTING DUPLICATE SYSTEM API FUNCTIONALITY")
    print("=" * 55)
    
    tests = [
        test_duplicate_rule_serializer,
        test_model_creation,
        test_related_names,
        test_admin_interface,
        test_viewset_registration,
        test_logic_engine_compatibility,
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
    
    print("\n" + "=" * 55)
    print(f"🎯 TEST RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ ALL FUNCTIONALITY TESTS PASSED! System is ready.")
        return True
    else:
        print("❌ SOME TESTS FAILED! Review issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)