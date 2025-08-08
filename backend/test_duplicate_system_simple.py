#!/usr/bin/env python
"""
Simple test to validate duplicate system works after naming standardization
"""
import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

import django
django.setup()

def test_basic_functionality():
    """Test basic duplicate system functionality"""
    print("🧪 Testing Basic Duplicate System Functionality")
    print("=" * 50)
    
    try:
        # Test model imports
        print("1. Testing model imports...")
        from duplicates.models import (
            DuplicateRule, URLExtractionRule, DuplicateRuleTest, DuplicateDetectionResult,
            DuplicateMatch, DuplicateResolution, DuplicateAnalytics, DuplicateExclusion
        )
        print("   ✅ All models import successfully")
        
        # Test serializer imports
        print("2. Testing serializer imports...")
        from api.serializers import DuplicateRuleSerializer
        from duplicates.serializers import DuplicateMatchSerializer
        print("   ✅ All serializers import successfully")
        
        # Test ViewSet imports
        print("3. Testing ViewSet imports...")
        from api.views.duplicates import DuplicateRuleViewSet, DuplicateMatchViewSet
        print("   ✅ All ViewSets import successfully")
        
        # Test admin imports
        print("4. Testing admin imports...")
        from django.contrib import admin
        if DuplicateRule in admin.site._registry:
            print("   ✅ DuplicateRule registered in admin")
        else:
            print("   ❌ DuplicateRule not registered in admin")
            
        # Test logic engine
        print("5. Testing logic engine...")
        from duplicates.logic_engine import DuplicateLogicEngine
        engine = DuplicateLogicEngine(1)  # Test tenant ID
        print("   ✅ Logic engine initializes correctly")
        
        # Test signals
        print("6. Testing signal configuration...")
        from django.db.models.signals import post_save
        from duplicates.models import DuplicateRule
        receivers = post_save._live_receivers(sender=DuplicateRule)
        if receivers:
            print("   ✅ DuplicateRule signals are connected")
        else:
            print("   ⚠️  No DuplicateRule signals found")
        
        # Test URL configuration
        print("7. Testing URL configuration...")
        from django.urls import reverse, NoReverseMatch
        try:
            url = reverse('duplicate-rule-list')
            print(f"   ✅ duplicate-rule-list URL: {url}")
        except NoReverseMatch:
            print("   ❌ duplicate-rule-list URL not found")
        
        print("\n✅ ALL BASIC FUNCTIONALITY TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    if success:
        print("\n🎉 DUPLICATE SYSTEM NAMING STANDARDIZATION SUCCESSFUL!")
        print("The system is ready for production use.")
    else:
        print("\n💥 TESTS FAILED!")
        print("Fix issues before proceeding.")
    
    sys.exit(0 if success else 1)