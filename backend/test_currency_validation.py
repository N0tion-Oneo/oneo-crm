#!/usr/bin/env python3
"""
Test script to verify currency field validation works correctly
"""
import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from pipelines.field_types import NumberFieldConfig
from pipelines.validators import FieldValidator

def test_currency_validation():
    """Test currency field validation with various input types"""
    
    # Create a currency field configuration as dictionary (not object)
    config = {
        'format': 'currency',
        'currency_code': 'USD',
        'decimal_places': 2
    }
    
    # Create validator instance
    validator = FieldValidator('number', config)
    
    print("🧪 Testing Currency Field Validation")
    print("=" * 50)
    
    # Test 1: Currency object (from frontend)
    try:
        currency_obj = {"amount": 123.45, "currency": "USD"}
        result = validator.validate_storage(currency_obj, {})
        print(f"✅ Currency object: {currency_obj} → Valid: {result.is_valid}, Value: {result.cleaned_value}")
    except Exception as e:
        print(f"❌ Currency object failed: {e}")
    
    # Test 2: Simple number 
    try:
        simple_num = 123.45
        result = validator.validate_storage(simple_num, {})
        print(f"✅ Simple number: {simple_num} → Valid: {result.is_valid}, Value: {result.cleaned_value}")
    except Exception as e:
        print(f"❌ Simple number failed: {e}")
    
    # Test 3: String currency
    try:
        string_currency = "$123.45"
        result = validator.validate_storage(string_currency, {})
        print(f"✅ String currency: {string_currency} → Valid: {result.is_valid}, Value: {result.cleaned_value}")
    except Exception as e:
        print(f"❌ String currency failed: {e}")
    
    # Test 4: Invalid currency object (should fail)
    try:
        invalid_obj = {"amount": "not_a_number", "currency": "USD"}
        result = validator.validate_storage(invalid_obj, {})
        print(f"❌ Invalid object should have failed: {invalid_obj} → Valid: {result.is_valid}, Errors: {result.errors}")
    except Exception as e:
        print(f"✅ Invalid object correctly failed: {e}")
    
    # Test 5: Negative currency (should fail)
    try:
        negative_currency = {"amount": -123.45, "currency": "USD"}
        result = validator.validate_storage(negative_currency, {})
        print(f"❌ Negative currency should have failed: {negative_currency} → Valid: {result.is_valid}, Errors: {result.errors}")
    except Exception as e:
        print(f"✅ Negative currency correctly failed: {e}")
    
    print("\n🎉 Currency validation test completed!")

if __name__ == "__main__":
    test_currency_validation()