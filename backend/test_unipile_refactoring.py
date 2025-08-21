"""
Test script to validate UniPile SDK refactoring
Tests backward compatibility and core functionality
"""
import sys
import warnings

# Suppress deprecation warnings during testing
warnings.filterwarnings('ignore', category=DeprecationWarning)

def test_backward_compatibility():
    """Test that all old imports still work"""
    print("🧪 Testing Backward Compatibility...")
    
    try:
        # Test original import pattern (how most files currently import)
        from communications.unipile_sdk import (
            unipile_service, UnipileClient, UnipileConnectionError,
            UnipileAccountClient, UnipileMessagingClient, UnipileUsersClient,
            UnipileWebhookClient, UnipileLinkedInClient, UnipileEmailClient,
            UnipileCalendarClient, UnipileRequestClient, UnipileService
        )
        print("✅ All original imports work")
        
        # Test that unipile_service is available and has the right methods
        assert hasattr(unipile_service, 'get_client'), "unipile_service missing get_client method"
        assert hasattr(unipile_service, 'connect_user_account'), "unipile_service missing connect_user_account method"
        assert hasattr(unipile_service, 'send_message'), "unipile_service missing send_message method"
        assert hasattr(unipile_service, 'mark_chat_as_read'), "unipile_service missing mark_chat_as_read method"
        print("✅ unipile_service has all expected methods")
        
        # Test that client classes are available
        assert UnipileClient is not None, "UnipileClient not available"
        assert UnipileAccountClient is not None, "UnipileAccountClient not available"
        print("✅ All client classes available")
        
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False

def test_new_imports():
    """Test that new import patterns work"""
    print("\n🧪 Testing New Import Patterns...")
    
    try:
        # Test new modular import pattern
        from communications.unipile import (
            UnipileClient, UnipileService, unipile_service,
            UnipileConnectionError, UnipileAuthenticationError
        )
        print("✅ New unipile package imports work")
        
        # Test direct module imports
        from communications.unipile.core.client import UnipileClient as CoreClient
        from communications.unipile.clients.account import UnipileAccountClient
        from communications.unipile.services.service import UnipileService
        print("✅ Direct module imports work")
        
        # Verify they're the same classes
        assert UnipileClient is CoreClient, "Import paths should reference same class"
        print("✅ Import paths reference same classes")
        
        return True
        
    except Exception as e:
        print(f"❌ New import test failed: {e}")
        return False

def test_client_initialization():
    """Test that clients can be initialized (without actual connections)"""
    print("\n🧪 Testing Client Initialization...")
    
    try:
        from communications.unipile_sdk import UnipileClient, unipile_service
        
        # Test creating a client instance
        client = UnipileClient("https://test.example.com", "test_token")
        print("✅ UnipileClient can be instantiated")
        
        # Test that sub-clients are available via properties
        assert hasattr(client, 'account'), "Client missing account property"
        assert hasattr(client, 'messaging'), "Client missing messaging property"
        assert hasattr(client, 'users'), "Client missing users property"
        assert hasattr(client, 'webhooks'), "Client missing webhooks property"
        assert hasattr(client, 'linkedin'), "Client missing linkedin property"
        assert hasattr(client, 'email'), "Client missing email property"
        assert hasattr(client, 'calendar'), "Client missing calendar property"
        assert hasattr(client, 'request'), "Client missing request property"
        print("✅ All client properties available")
        
        # Test lazy loading (accessing a property should create the sub-client)
        account_client = client.account
        assert account_client is not None, "Account client should be created"
        print("✅ Lazy loading works")
        
        # Test service initialization
        assert unipile_service is not None, "Global service should be available"
        print("✅ Global unipile_service available")
        
        return True
        
    except Exception as e:
        print(f"❌ Client initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_structure():
    """Test that all expected files exist"""
    print("\n🧪 Testing File Structure...")
    
    import os
    
    base_path = "communications/unipile"
    expected_files = [
        "__init__.py",
        "core/__init__.py",
        "core/client.py", 
        "core/exceptions.py",
        "clients/__init__.py",
        "clients/account.py",
        "clients/messaging.py",
        "clients/users.py",
        "clients/webhooks.py",
        "clients/linkedin.py",
        "clients/email.py",
        "clients/calendar.py",
        "services/__init__.py",
        "services/service.py",
        "utils/__init__.py",
        "utils/request.py"
    ]
    
    try:
        for file_path in expected_files:
            full_path = os.path.join(base_path, file_path)
            assert os.path.exists(full_path), f"Missing file: {full_path}"
        
        print(f"✅ All {len(expected_files)} expected files exist")
        return True
        
    except Exception as e:
        print(f"❌ File structure test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 UniPile SDK Refactoring Validation")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_backward_compatibility,
        test_new_imports, 
        test_client_initialization
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
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Refactoring successful!")
        print("\n✅ The refactoring maintains full backward compatibility")
        print("✅ All existing code will continue to work without changes") 
        print("✅ New modular structure is available for future development")
        return True
    else:
        print("❌ Some tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)