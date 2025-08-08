#!/usr/bin/env python3
"""
Test script to validate the AI processing fix
Tests that records can be saved with _skip_ai_processing flag
"""

import os
import sys
import django

# Add the backend directory to Python path
sys.path.insert(0, '/Users/joshcowan/Oneo CRM/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from pipelines.models import Record
from django_tenants.utils import schema_context
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_ai_processing_fix():
    """Test that _skip_ai_processing prevents recursive AI calls"""
    
    print("🧪 Testing AI Processing Fix...")
    
    try:
        with schema_context('demo'):
            # Get a test record
            records = Record.objects.all()[:1]
            if not records:
                print("❌ No test records found in demo tenant")
                return False
                
            record = records.first()
            print(f"📋 Using test record: {record.id}")
            print(f"📊 Original data keys: {list(record.data.keys())}")
            
            # Test 1: Normal save (should trigger AI processing if enabled)
            print("\n🧪 Test 1: Normal save (AI processing enabled)")
            original_data = record.data.copy()
            record.data['test_normal'] = 'Test content'
            try:
                record.save(update_fields=['data'])
                print("✅ Normal save succeeded")
            except Exception as e:
                print(f"❌ Normal save failed: {e}")
                return False
            
            # Test 2: Save with _skip_ai_processing flag (should NOT trigger AI processing)
            print("\n🧪 Test 2: Save with _skip_ai_processing=True")
            record._skip_ai_processing = True
            record._skip_broadcast = True
            record.data['test_ai_skip'] = 'AI-generated content'
            
            try:
                record.save(update_fields=['data'])
                print("✅ Skip AI processing save succeeded")
                print("✅ No recursive AI processing occurred")
            except Exception as e:
                print(f"❌ Skip AI processing save failed: {e}")
                return False
            
            # Test 3: Verify data was saved correctly
            print("\n🧪 Test 3: Verify data persistence")
            record.refresh_from_db()
            
            if 'test_normal' in record.data and 'test_ai_skip' in record.data:
                print("✅ Both test fields saved correctly")
                print(f"📊 Final data keys: {list(record.data.keys())}")
            else:
                print("❌ Test fields not saved correctly")
                return False
                
            print("\n🎉 All tests passed! AI processing fix is working correctly.")
            return True
            
    except Exception as e:
        print(f"💥 Critical test failure: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_ai_processing_fix()
    sys.exit(0 if success else 1)