#!/usr/bin/env python3
"""
Test script to verify phone field validation works correctly
"""
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from pipelines.field_types import PhoneFieldConfig
from pipelines.validators import FieldValidator

def test_phone_validation():
    """Test phone field validation with various input types"""
    
    print("🧪 Testing Phone Field Validation")
    print("=" * 50)
    
    # Test 1: Phone field with country code required
    print("\n📞 Test 1: Phone with country code required")
    config_with_country = {
        'require_country_code': True,
        'default_country': 'US',
        'format_display': True
    }
    
    validator_with_country = FieldValidator('phone', config_with_country)
    
    # Test phone object (from frontend)
    try:
        phone_obj = {"country_code": "+1", "number": "5551234567"}
        result = validator_with_country.validate_storage(phone_obj, {})
        print(f"✅ Phone object: {phone_obj} → Valid: {result.is_valid}, Value: {result.cleaned_value}")
    except Exception as e:
        print(f"❌ Phone object failed: {e}")
    
    # Test invalid phone object (missing number)
    try:
        invalid_obj = {"country_code": "+1", "number": ""}
        result = validator_with_country.validate_storage(invalid_obj, {})
        print(f"❌ Invalid object should have failed: {invalid_obj} → Valid: {result.is_valid}, Errors: {result.errors}")
    except Exception as e:
        print(f"✅ Invalid object correctly failed: {e}")
    
    # Test string phone with country code
    try:
        string_phone = "+1 555-123-4567"
        result = validator_with_country.validate_storage(string_phone, {})
        print(f"✅ String phone: {string_phone} → Valid: {result.is_valid}, Value: {result.cleaned_value}")
    except Exception as e:
        print(f"❌ String phone failed: {e}")
    
    print("\n📞 Test 2: Phone without country code required")
    config_no_country = {
        'require_country_code': False,
        'format_display': True
    }
    
    validator_no_country = FieldValidator('phone', config_no_country)
    
    # Test simple phone string
    try:
        simple_phone = "555-123-4567"
        result = validator_no_country.validate_storage(simple_phone, {})
        print(f"✅ Simple phone: {simple_phone} → Valid: {result.is_valid}, Value: {result.cleaned_value}")
    except Exception as e:
        print(f"❌ Simple phone failed: {e}")
    
    # Test phone object (should fail when country code not required)
    try:
        phone_obj = {"country_code": "+1", "number": "5551234567"}
        result = validator_no_country.validate_storage(phone_obj, {})
        print(f"❌ Phone object should have failed: {phone_obj} → Valid: {result.is_valid}")
    except Exception as e:
        print(f"✅ Phone object correctly failed: {e}")
    
    print("\n🎉 Phone validation test completed!")

if __name__ == "__main__":
    test_phone_validation()