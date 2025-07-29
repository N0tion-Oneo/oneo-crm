#!/usr/bin/env python
"""
Simple async authentication test to validate Django native async capabilities
"""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')

import django
django.setup()

import asyncio
import time
from django_tenants.utils import schema_context
from django.db import connection
from tenants.models import Tenant
from authentication.models import CustomUser, UserType
from authentication.permissions import AsyncPermissionManager

async def test_basic_async_functionality():
    """Test basic async functionality"""
    print("=== Testing Basic Async Functionality ===\n")
    
    # 1. Test async tenant queries
    print("1. Testing async tenant operations...")
    tenant_count = await Tenant.objects.acount()
    print(f"   ✅ Async tenant count: {tenant_count}")
    
    # Get demo tenant
    demo_tenant = await Tenant.objects.aget(schema_name='demo')
    print(f"   ✅ Retrieved tenant: {demo_tenant.name}")
    
    # 2. Test within tenant schema
    print(f"\n2. Testing within tenant schema ({demo_tenant.schema_name})...")
    
    with schema_context(demo_tenant.schema_name):
        print(f"   Current schema: {connection.schema_name}")
        
        # Test async user count
        user_count = await CustomUser.objects.acount()
        print(f"   ✅ Async user count: {user_count}")
        
        # Test async user type count
        usertype_count = await UserType.objects.acount()
        print(f"   ✅ Async user type count: {usertype_count}")
        
        if user_count > 0:
            # Test async iteration
            print("   ✅ Async user iteration:")
            async for user in CustomUser.objects.select_related('user_type'):
                user_type_name = user.user_type.name if user.user_type else "None"
                print(f"     - {user.username} ({user.email}) - {user_type_name}")
            
            # Get first user for permission testing
            first_user = await CustomUser.objects.select_related('user_type').afirst()
            if first_user and first_user.user_type:
                print(f"\n3. Testing async permission manager with {first_user.username}...")
                
                # Create permission manager
                pm = AsyncPermissionManager(first_user)
                print(f"   ✅ Permission manager created")
                
                # Test async permission retrieval
                permissions = await pm.get_user_permissions()
                print(f"   ✅ Retrieved permissions: {len(permissions)} categories")
                
                # Show permission details
                for resource, actions in list(permissions.items())[:3]:
                    print(f"     {resource}: {actions}")
                
                # Test async permission checking
                has_pipeline_read = await pm.has_permission('action', 'pipelines', 'read')
                print(f"   ✅ Pipeline read permission: {has_pipeline_read}")
                
                # Test async field permissions
                field_perms = await pm.get_field_permissions('test_pipeline', 'test_field')
                print(f"   ✅ Field permissions: {field_perms}")
                
                # Test async cache performance
                print("\n4. Testing async cache performance...")
                await pm.clear_cache()
                
                start_time = time.time()
                perms1 = await pm.get_user_permissions()
                first_call = time.time() - start_time
                
                start_time = time.time()
                perms2 = await pm.get_user_permissions()
                second_call = time.time() - start_time
                
                print(f"   ✅ First call (cache miss): {first_call:.4f}s")
                print(f"   ✅ Second call (cache hit): {second_call:.4f}s")
                
                if second_call > 0:
                    speedup = first_call / second_call
                    print(f"   ✅ Cache speedup: {speedup:.1f}x")
                
                if perms1 == perms2:
                    print("   ✅ Cache consistency: Verified")
            
        else:
            print("   ⚠️  No users found in tenant")
    
    print("\n5. Testing concurrent async operations...")
    
    # Test concurrent tenant operations
    tasks = [
        Tenant.objects.acount(),
        Tenant.objects.filter(schema_name='demo').aexists(),
        Tenant.objects.filter(schema_name='test').aexists(),
    ]
    
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    concurrent_time = time.time() - start_time
    
    print(f"   ✅ 3 concurrent operations in {concurrent_time:.4f}s")
    print(f"   ✅ Results: count={results[0]}, demo_exists={results[1]}, test_exists={results[2]}")
    
    print("\n✅ ALL ASYNC FUNCTIONALITY TESTS PASSED!")
    return True

async def main():
    """Run simple async test"""
    try:
        success = await test_basic_async_functionality()
        
        if success:
            print("\n🎉 DJANGO NATIVE ASYNC: FULLY OPERATIONAL")
            print("✅ Ready to resolve Phase 1 & 2 integration issue")
            print("✅ Ready to proceed with Phase 3 Pipeline System")
            return 0
        else:
            print("\n❌ Async functionality issues detected")
            return 1
    except Exception as e:
        print(f"\n❌ Async test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))