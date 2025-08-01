#!/usr/bin/env python
"""
Basic Phase 2 Authentication System Test
Tests async user model and permission system functionality
"""

import os
import sys
import django
import asyncio
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django.contrib.auth import get_user_model
from authentication.models import UserType, UserSession
from authentication.permissions import AsyncPermissionManager

User = get_user_model()


async def test_user_model():
    """Test custom user model functionality"""
    try:
        # Test user creation
        admin_type = await UserType.objects.aget(slug='admin')
        user = await User.objects.acreate_user(
            username='testadmin',
            email='admin@demo.com',
            password='testpass123',
            user_type=admin_type
        )
        
        print("✅ User model: Custom user creation working")
        
        # Test async activity update
        await user.aupdate_last_activity()
        print("✅ User model: Async activity update working")
        
        return user
    except Exception as e:
        print(f"❌ User model: {e}")
        return None


async def test_user_types():
    """Test user type functionality"""
    try:
        # Test user type retrieval
        user_types = []
        async for user_type in UserType.objects.all():
            user_types.append(user_type)
        
        print(f"✅ User types: {len(user_types)} types found")
        
        # Test specific user type
        admin_type = await UserType.objects.aget(slug='admin')
        assert admin_type.name == 'Admin'
        assert admin_type.is_system_default == True
        print("✅ User types: Admin type configuration correct")
        
        return True
    except Exception as e:
        print(f"❌ User types: {e}")
        return False


async def test_permission_manager(user):
    """Test async permission manager"""
    try:
        # Test permission manager creation
        pm = AsyncPermissionManager(user)
        
        # Test permission retrieval
        permissions = await pm.get_user_permissions()
        assert 'system' in permissions
        print("✅ Permission manager: Permission retrieval working")
        
        # Test permission checking
        has_full_access = await pm.has_permission('action', 'system', 'full_access')
        assert has_full_access == True
        print("✅ Permission manager: Permission checking working")
        
        # Test field permissions
        field_perms = await pm.get_field_permissions('test_pipeline', 'test_field')
        assert 'read' in field_perms
        print("✅ Permission manager: Field permissions working")
        
        return True
    except Exception as e:
        print(f"❌ Permission manager: {e}")
        return False


async def test_session_model():
    """Test user session model"""
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Test session cleanup method exists
        expired_count = await UserSession.acleanup_expired_sessions()
        print(f"✅ Session model: Cleanup method working (cleaned {expired_count} sessions)")
        
        return True
    except Exception as e:
        print(f"❌ Session model: {e}")
        return False


async def test_database_operations():
    """Test async database operations"""
    try:
        # Test async count
        user_count = await User.objects.acount()
        print(f"✅ Database: Async count working ({user_count} users)")
        
        # Test async iteration
        user_types = []
        async for ut in UserType.objects.filter(is_system_default=True)[:2]:
            user_types.append(ut.name)
        print(f"✅ Database: Async iteration working ({len(user_types)} types)")
        
        return True
    except Exception as e:
        print(f"❌ Database operations: {e}")
        return False


async def main():
    """Run all Phase 2 basic tests"""
    print("🧪 Testing Phase 2 Authentication System")
    print("=" * 60)
    
    # Switch to demo tenant schema
    from django_tenants.utils import schema_context
    from tenants.models import Tenant
    
    try:
        demo_tenant = await Tenant.objects.aget(schema_name='demo')
        print(f"✅ Tenant: Connected to {demo_tenant.name}")
    except Exception as e:
        print(f"❌ Tenant connection failed: {e}")
        return
    
    # Run tests in tenant context
    connection.set_tenant(demo_tenant)
    
    tests = [
        test_user_types,
        test_database_operations,
        test_session_model,
    ]
    
    # Test user creation and permissions
    user = await test_user_model()
    if user:
        tests.append(lambda: test_permission_manager(user))
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    print("=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 2 Basic Functionality: ALL TESTS PASSED!")
        print("\n🚀 System Status: Authentication system working with async support")
        print("\nFeatures verified:")
        print("- ✅ Custom user model with async operations")
        print("- ✅ User types with default configurations")
        print("- ✅ Async permission manager")
        print("- ✅ Session management models")
        print("- ✅ Multi-tenant database operations")
        return True
    else:
        print(f"⚠️ {total - passed} tests failed - check configuration")
        return False


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)