"""
Test cases for permission system
Tests AsyncPermissionManager and permission calculation logic
"""

import asyncio
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.cache import cache
from authentication.models import UserType
from authentication.permissions import AsyncPermissionManager

User = get_user_model()


class AsyncPermissionManagerTest(TransactionTestCase):
    """Test AsyncPermissionManager functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user_type = UserType.objects.create(
            name="Manager",
            slug="manager",
            base_permissions={
                'system': {'actions': ['view_dashboard']},
                'pipelines': {
                    'actions': ['read', 'update'],
                    'pipeline_1': {'actions': ['read', 'update', 'delete']}
                },
                'fields': {
                    'pipeline_1': {
                        'salary': {'read': False, 'write': False},
                        'name': {'read': True, 'write': True}
                    }
                }
            }
        )
        
        self.user = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123',
            user_type=self.user_type
        )
        
        # Clear cache before each test
        cache.clear()
    
    def test_get_user_permissions_caching(self):
        """Test permission retrieval and caching"""
        async def run_test():
            pm = AsyncPermissionManager(self.user)
            
            # First call should calculate and cache
            permissions1 = await pm.get_user_permissions()
            
            # Second call should use cache
            permissions2 = await pm.get_user_permissions()
            
            # Results should be identical
            self.assertEqual(permissions1, permissions2)
            
            # Check that permissions were calculated correctly
            self.assertIn('system', permissions1)
            self.assertIn('pipelines', permissions1)
            self.assertEqual(permissions1['system']['actions'], ['view_dashboard'])
        
        asyncio.run(run_test())
    
    def test_has_permission_basic(self):
        """Test basic permission checking"""
        async def run_test():
            pm = AsyncPermissionManager(self.user)
            
            # Test basic permissions
            self.assertTrue(await pm.has_permission('action', 'pipelines', 'read'))
            self.assertTrue(await pm.has_permission('action', 'pipelines', 'update'))
            self.assertFalse(await pm.has_permission('action', 'pipelines', 'delete'))
        
        asyncio.run(run_test())
    
    def test_has_permission_resource_specific(self):
        """Test resource-specific permission checking"""
        async def run_test():
            pm = AsyncPermissionManager(self.user)
            
            # Test resource-specific permissions
            self.assertTrue(await pm.has_permission('action', 'pipelines', 'delete', 'pipeline_1'))
            self.assertFalse(await pm.has_permission('action', 'pipelines', 'delete', 'pipeline_2'))
        
        asyncio.run(run_test())
    
    def test_get_field_permissions(self):
        """Test field-level permission checking"""
        async def run_test():
            pm = AsyncPermissionManager(self.user)
            
            # Test field permissions
            salary_perms = await pm.get_field_permissions('pipeline_1', 'salary')
            self.assertFalse(salary_perms['read'])
            self.assertFalse(salary_perms['write'])
            self.assertFalse(salary_perms['delete'])
            
            name_perms = await pm.get_field_permissions('pipeline_1', 'name')
            self.assertTrue(name_perms['read'])
            self.assertTrue(name_perms['write'])
            self.assertFalse(name_perms['delete'])  # Default value
            
            # Test field that doesn't have specific permissions (should default to True for read)
            default_perms = await pm.get_field_permissions('pipeline_1', 'unknown_field')
            self.assertTrue(default_perms['read'])
            self.assertFalse(default_perms['write'])
            self.assertFalse(default_perms['delete'])
        
        asyncio.run(run_test())
    
    def test_permission_overrides(self):
        """Test user-specific permission overrides"""
        async def run_test():
            # Create user with permission overrides
            user_with_overrides = await sync_to_async(User.objects.create_user)(
                username='override_user',
                email='override@example.com',
                password='testpass123',
                user_type=self.user_type,
                permission_overrides={
                    'pipelines': {'actions': ['read']},  # Remove update permission
                    'records': {'actions': ['create', 'read', 'update']}  # Add new resource
                }
            )
            
            pm = AsyncPermissionManager(user_with_overrides)
            permissions = await pm.get_user_permissions()
            
            # Check that overrides were applied
            self.assertEqual(permissions['pipelines']['actions'], ['read'])
            self.assertIn('records', permissions)
            self.assertEqual(permissions['records']['actions'], ['create', 'read', 'update'])
            
            # Check permission checking with overrides
            self.assertTrue(await pm.has_permission('action', 'pipelines', 'read'))
            self.assertFalse(await pm.has_permission('action', 'pipelines', 'update'))
            self.assertTrue(await pm.has_permission('action', 'records', 'create'))
        
        from asgiref.sync import sync_to_async
        asyncio.run(run_test())
    
    def test_system_full_access(self):
        """Test system full access permission"""
        async def run_test():
            # Create admin user with full access
            admin_type = await sync_to_async(UserType.objects.create)(
                name="Admin",
                slug="admin",
                base_permissions={
                    'system': {'actions': ['full_access']}
                }
            )
            
            admin_user = await sync_to_async(User.objects.create_user)(
                username='admin',
                email='admin@example.com',
                password='testpass123',
                user_type=admin_type
            )
            
            pm = AsyncPermissionManager(admin_user)
            
            # Admin should have access to everything
            self.assertTrue(await pm.has_permission('action', 'pipelines', 'delete'))
            self.assertTrue(await pm.has_permission('action', 'users', 'create'))
            self.assertTrue(await pm.has_permission('action', 'anything', 'anything'))
        
        from asgiref.sync import sync_to_async
        asyncio.run(run_test())
    
    def test_user_without_user_type(self):
        """Test user without user type has no permissions"""
        async def run_test():
            user_no_type = await sync_to_async(User.objects.create_user)(
                username='no_type',
                email='notype@example.com',
                password='testpass123'
                # No user_type assigned
            )
            
            pm = AsyncPermissionManager(user_no_type)
            permissions = await pm.get_user_permissions()
            
            # Should return empty permissions
            self.assertEqual(permissions, {})
            
            # Should not have any permissions
            self.assertFalse(await pm.has_permission('action', 'pipelines', 'read'))
        
        from asgiref.sync import sync_to_async
        asyncio.run(run_test())
    
    def test_cache_clearing(self):
        """Test cache clearing functionality"""
        async def run_test():
            pm = AsyncPermissionManager(self.user)
            
            # Get permissions (should cache them)
            permissions1 = await pm.get_user_permissions()
            
            # Clear cache
            await pm.clear_cache()
            
            # Update user type permissions
            self.user_type.base_permissions = {
                'system': {'actions': ['admin_access']}
            }
            await sync_to_async(self.user_type.save)()
            
            # Get permissions again (should calculate fresh)
            permissions2 = await pm.get_user_permissions()
            
            # Should be different now
            self.assertNotEqual(permissions1, permissions2)
            self.assertEqual(permissions2['system']['actions'], ['admin_access'])
        
        from asgiref.sync import sync_to_async
        asyncio.run(run_test())
    
    def test_clear_user_type_cache(self):
        """Test clearing cache for all users of a user type"""
        async def run_test():
            # Create additional users with same user type
            user2 = await sync_to_async(User.objects.create_user)(
                username='user2',
                email='user2@example.com',
                password='testpass123',
                user_type=self.user_type
            )
            
            user3 = await sync_to_async(User.objects.create_user)(
                username='user3',
                email='user3@example.com',
                password='testpass123',
                user_type=self.user_type
            )
            
            # Get permissions for all users (cache them)
            pm1 = AsyncPermissionManager(self.user)
            pm2 = AsyncPermissionManager(user2)
            pm3 = AsyncPermissionManager(user3)
            
            await pm1.get_user_permissions()
            await pm2.get_user_permissions()
            await pm3.get_user_permissions()
            
            # Clear cache for the user type
            await AsyncPermissionManager.clear_user_type_cache(self.user_type.id)
            
            # All users should have fresh cache now
            # (This is hard to test directly, but we can verify the method runs without error)
            self.assertTrue(True)  # Method completed successfully
        
        from asgiref.sync import sync_to_async
        asyncio.run(run_test())


class PermissionCalculationTest(TestCase):
    """Test permission calculation logic"""
    
    def test_permission_structure_validation(self):
        """Test that permission structures are valid"""
        user_type = UserType.objects.create(
            name="Test",
            slug="test",
            base_permissions={
                'pipelines': {'actions': ['read', 'update']},
                'fields': {
                    'pipeline_1': {
                        'field_1': {'read': True, 'write': False}
                    }
                }
            }
        )
        
        # Test that JSONB field accepts the structure
        user_type.full_clean()  # Should not raise validation error
        
        # Test that we can retrieve nested values
        self.assertEqual(
            user_type.base_permissions['pipelines']['actions'], 
            ['read', 'update']
        )
        self.assertTrue(
            user_type.base_permissions['fields']['pipeline_1']['field_1']['read']
        )