#!/usr/bin/env python3
"""
Unit tests for the encrypted share links system
Tests the core functionality without requiring a running server
"""

import sys
import os
import tempfile
import json
from datetime import datetime, timedelta

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

def test_encryption_integration():
    """Test the complete encryption integration"""
    
    print("🧪 Testing Encryption Integration")
    print("=" * 40)
    
    # Configure Django settings
    print("\n0. Configuring Django settings...")
    try:
        import django
        from django.conf import settings
        
        if not settings.configured:
            settings.configure(
                SECRET_KEY='test_secret_key_for_development_only_please_change_in_production',
                USE_TZ=True,
                DATABASES={
                    'default': {
                        'ENGINE': 'django.db.backends.sqlite3',
                        'NAME': ':memory:',
                    }
                },
                CACHES={
                    'default': {
                        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
                    }
                },
            )
        django.setup()
        print("✅ Django settings configured")
    except Exception as e:
        print(f"❌ Django configuration failed: {e}")
        return False
    
    # Test 1: Import and initialize encryption utility
    print("\n1. Testing encryption utility import...")
    
    try:
        from utils.encryption import ShareLinkEncryption
        encryption = ShareLinkEncryption()
        print("✅ ShareLinkEncryption imported and initialized successfully")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Generate working day expiry
    print("\n2. Testing working day calculation...")
    
    try:
        expires_timestamp = encryption.generate_working_day_expiry(working_days=5)
        expires_date = datetime.fromtimestamp(expires_timestamp)
        
        # Verify it's a weekday and at 5 PM
        print(f"✅ Expiry date: {expires_date.strftime('%A, %Y-%m-%d %H:%M:%S')}")
        print(f"✅ Is weekday: {expires_date.weekday() < 5}")
        print(f"✅ Is 5 PM: {expires_date.hour == 17}")
        
        if expires_date.weekday() >= 5:
            print("❌ Expiry date is not a weekday!")
            return False
        
        if expires_date.hour != 17:
            print("❌ Expiry time is not 5 PM!")
            return False
        
    except Exception as e:
        print(f"❌ Working day calculation failed: {e}")
        return False
    
    # Test 3: Encrypt share data
    print("\n3. Testing share data encryption...")
    
    try:
        # Test data
        record_id = "550e8400-e29b-41d4-a716-446655440000"
        user_id = 123
        
        encrypted_token = encryption.encrypt_share_data(
            record_id=record_id,
            user_id=user_id,
            expires_timestamp=expires_timestamp
        )
        
        print(f"✅ Encrypted token generated")
        print(f"   Length: {len(encrypted_token)} characters")
        print(f"   Sample: {encrypted_token[:30]}...")
        
        # Verify token is URL-safe
        url_safe_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
        if all(c in url_safe_chars for c in encrypted_token):
            print("✅ Token contains only URL-safe characters")
        else:
            print("❌ Token contains non-URL-safe characters!")
            return False
            
    except Exception as e:
        print(f"❌ Encryption failed: {e}")
        return False
    
    # Test 4: Decrypt and validate share data
    print("\n4. Testing share data decryption...")
    
    try:
        payload, error = encryption.decrypt_share_data(encrypted_token)
        
        if error:
            print(f"❌ Decryption failed: {error}")
            return False
        
        print("✅ Decryption successful")
        print(f"   Record ID: {payload['record_id']}")
        print(f"   User ID: {payload['user_id']}")
        print(f"   Expires: {datetime.fromtimestamp(payload['expires']).isoformat()}")
        print(f"   Created: {datetime.fromtimestamp(payload['created']).isoformat()}")
        
        # Validate payload data
        if payload['record_id'] != record_id:
            print(f"❌ Record ID mismatch: expected {record_id}, got {payload['record_id']}")
            return False
        
        if payload['user_id'] != user_id:
            print(f"❌ User ID mismatch: expected {user_id}, got {payload['user_id']}")
            return False
        
        if payload['expires'] != expires_timestamp:
            print(f"❌ Expires timestamp mismatch: expected {expires_timestamp}, got {payload['expires']}")
            return False
        
        print("✅ All payload data matches original input")
        
    except Exception as e:
        print(f"❌ Decryption test failed: {e}")
        return False
    
    # Test 5: Test expired token handling
    print("\n5. Testing expired token handling...")
    
    try:
        # Create an expired token (1 hour ago)
        expired_expires = int((datetime.now() - timedelta(hours=1)).timestamp())
        expired_token = encryption.encrypt_share_data(
            record_id=record_id,
            user_id=user_id,
            expires_timestamp=expired_expires
        )
        
        expired_payload, expired_error = encryption.decrypt_share_data(expired_token)
        
        if expired_payload:
            print("❌ Expired token was accepted - security issue!")
            return False
        
        if "expired" not in expired_error.lower():
            print(f"❌ Expired error message unexpected: {expired_error}")
            return False
        
        print("✅ Expired token correctly rejected")
        print(f"   Error: {expired_error}")
        
    except Exception as e:
        print(f"❌ Expired token test failed: {e}")
        return False
    
    # Test 6: Test invalid token handling
    print("\n6. Testing invalid token handling...")
    
    try:
        # Test various invalid tokens
        invalid_tokens = [
            "invalid_token",
            "",
            "a" * 100,
            "SGVsbG8gV29ybGQ=",  # Valid base64 but invalid encrypted data
        ]
        
        for i, invalid_token in enumerate(invalid_tokens, 1):
            invalid_payload, invalid_error = encryption.decrypt_share_data(invalid_token)
            
            if invalid_payload:
                print(f"❌ Invalid token {i} was accepted - security issue!")
                return False
            
            print(f"✅ Invalid token {i} correctly rejected: {invalid_error[:50]}...")
        
    except Exception as e:
        print(f"❌ Invalid token test failed: {e}")
        return False
    
    # Test 7: Test working days remaining calculation
    print("\n7. Testing working days remaining calculation...")
    
    try:
        # Test with various timestamps
        now = datetime.now()
        
        # 3 working days from now
        test_expires = encryption.generate_working_day_expiry(working_days=3)
        remaining_days = encryption.calculate_working_days_remaining(test_expires)
        
        print(f"✅ 3 working days expire at: {datetime.fromtimestamp(test_expires).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"✅ Remaining working days: {remaining_days}")
        
        if remaining_days < 2 or remaining_days > 3:
            print(f"❌ Unexpected remaining days: {remaining_days} (expected 2-3)")
            return False
        
        # Test already expired
        past_timestamp = int((now - timedelta(days=1)).timestamp())
        past_remaining = encryption.calculate_working_days_remaining(past_timestamp)
        
        if past_remaining != 0:
            print(f"❌ Past timestamp should have 0 remaining days, got {past_remaining}")
            return False
        
        print("✅ Working days calculation working correctly")
        
    except Exception as e:
        print(f"❌ Working days remaining test failed: {e}")
        return False
    
    # Test 8: Test URL construction simulation
    print("\n8. Testing URL construction simulation...")
    
    try:
        # Simulate URL construction like in the API
        base_url = "http://demo.localhost:8000"
        share_url = f"{base_url}/api/v1/shared-records/{encrypted_token}/"
        
        # Extract token from URL (like in SharedRecordViewSet.retrieve)
        extracted_token = share_url.split('/shared-records/')[-1].rstrip('/')
        
        if extracted_token != encrypted_token:
            print(f"❌ Token extraction failed: {extracted_token[:30]}... != {encrypted_token[:30]}...")
            return False
        
        print("✅ URL construction and token extraction working")
        print(f"   Share URL: {share_url[:50]}...")
        print(f"   Extracted token matches original: {len(extracted_token)} chars")
        
        # Verify the extracted token can be decrypted
        verify_payload, verify_error = encryption.decrypt_share_data(extracted_token)
        
        if verify_error:
            print(f"❌ Extracted token decryption failed: {verify_error}")
            return False
        
        print("✅ Extracted token successfully decrypted")
        
    except Exception as e:
        print(f"❌ URL construction test failed: {e}")
        return False
    
    print("\n" + "=" * 40)
    print("🎉 All encryption integration tests passed!")
    print("\nSummary:")
    print("✅ Encryption utility properly initialized")
    print("✅ Working day calculation accurate")
    print("✅ Encryption/decryption cycle working")
    print("✅ Security validation (expired/invalid tokens)")
    print("✅ URL-safe token generation")
    print("✅ Working days remaining calculation")
    print("✅ URL construction and extraction")
    
    print(f"\n🔐 Sample encrypted share link:")
    print(f"   {base_url}/api/v1/shared-records/{encrypted_token}/")
    print(f"\n⏰ Link expires: {datetime.fromtimestamp(expires_timestamp).strftime('%A, %B %d, %Y at %I:%M %p')}")
    print(f"📊 Working days until expiry: {encryption.calculate_working_days_remaining(expires_timestamp)}")
    
    return True

if __name__ == "__main__":
    success = test_encryption_integration()
    sys.exit(0 if success else 1)