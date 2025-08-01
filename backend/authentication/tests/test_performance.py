"""
Performance tests for authentication system
Tests caching, permission calculations, and API response times
"""

import time
import asyncio
from django.test import TestCase, TransactionTestCase
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITransactionTestCase
from authentication.models import UserType, UserSession
from authentication.permissions import AsyncPermissionManager

User = get_user_model()


class PermissionCachingPerformanceTest(TransactionTestCase):
    """Test permission caching performance"""
    
    def setUp(self):
        """Set up test data"""
        cache.clear()
        
        self.user_type = UserType.objects.create(
            name="Manager",
            slug="manager",
            base_permissions={
                'system': {'actions': ['view_dashboard']},
                'pipelines': {'actions': ['read', 'update']},
                'records': {'actions': ['create', 'read', 'update']},
                'fields': {
                    'pipeline_1': {
                        'field_1': {'read': True, 'write': True},
                        'field_2': {'read': True, 'write': False},
                        'field_3': {'read': False, 'write': False}
                    },
                    'pipeline_2': {
                        'field_1': {'read': True, 'write': True}
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
    
    def test_permission_calculation_caching(self):
        """Test that permission calculation is cached for performance"""
        async def run_test():
            pm = AsyncPermissionManager(self.user)
            
            # First call should calculate and cache
            start_time = time.time()
            permissions1 = await pm.get_user_permissions()
            first_call_time = time.time() - start_time
            
            # Second call should use cache
            start_time = time.time()
            permissions2 = await pm.get_user_permissions()
            second_call_time = time.time() - start_time
            
            # Results should be identical
            self.assertEqual(permissions1, permissions2)
            
            # Second call should be significantly faster (at least 5x faster)
            self.assertLess(second_call_time, first_call_time * 0.2)
            
            # Cache hit should be very fast (under 1ms typically)
            self.assertLess(second_call_time, 0.001)
        
        asyncio.run(run_test())
    
    def test_bulk_permission_checks_performance(self):
        """Test performance of bulk permission checks"""
        async def run_test():
            pm = AsyncPermissionManager(self.user)
            
            # Warm up cache
            await pm.get_user_permissions()
            
            # Test bulk permission checks
            start_time = time.time()
            
            # Perform 1000 permission checks
            for i in range(100):
                await pm.has_permission('action', 'pipelines', 'read')
                await pm.has_permission('action', 'pipelines', 'update')
                await pm.has_permission('action', 'records', 'create')
                await pm.has_permission('action', 'records', 'read')
                await pm.has_permission('action', 'records', 'update')
                
                await pm.get_field_permissions('pipeline_1', 'field_1')
                await pm.get_field_permissions('pipeline_1', 'field_2')
                await pm.get_field_permissions('pipeline_1', 'field_3')
                await pm.get_field_permissions('pipeline_2', 'field_1')
                await pm.get_field_permissions('pipeline_2', 'field_2')
            
            total_time = time.time() - start_time
            
            # 1000 permission checks should complete in under 0.5 seconds
            self.assertLess(total_time, 0.5)
            
            # Average per check should be under 0.5ms
            avg_time_per_check = total_time / 1000
            self.assertLess(avg_time_per_check, 0.0005)
        
        asyncio.run(run_test())
    
    def test_permission_cache_miss_performance(self):
        """Test performance when cache is missed"""
        async def run_test():
            pm = AsyncPermissionManager(self.user)
            
            # Clear cache to force miss
            await pm.clear_cache()
            
            # Time cache miss
            start_time = time.time()
            permissions = await pm.get_user_permissions()
            cache_miss_time = time.time() - start_time
            
            # Cache miss should still be reasonably fast (under 10ms)
            self.assertLess(cache_miss_time, 0.01)
            
            # Should return expected permissions
            self.assertIn('system', permissions)
            self.assertIn('pipelines', permissions)
        
        asyncio.run(run_test())
    
    def test_multiple_users_cache_isolation(self):
        """Test cache isolation between multiple users"""
        async def run_test():
            # Create additional users
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
                user_type=self.user_type,
                permission_overrides={
                    'pipelines': {'actions': ['read']}  # Different permissions
                }
            )
            
            pm1 = AsyncPermissionManager(self.user)
            pm2 = AsyncPermissionManager(user2)
            pm3 = AsyncPermissionManager(user3)
            
            # Get permissions for all users (should cache separately)
            start_time = time.time()
            perms1 = await pm1.get_user_permissions()
            perms2 = await pm2.get_user_permissions()
            perms3 = await pm3.get_user_permissions()
            total_time = time.time() - start_time
            
            # Should complete quickly even with multiple users
            self.assertLess(total_time, 0.05)
            
            # User 1 and 2 should have same permissions (same user type)
            self.assertEqual(perms1, perms2)
            
            # User 3 should have different permissions (has overrides)
            self.assertNotEqual(perms1, perms3)
            
            # Second call should use cache for all users
            start_time = time.time()
            await pm1.get_user_permissions()
            await pm2.get_user_permissions()
            await pm3.get_user_permissions()
            cached_time = time.time() - start_time
            
            # Should be much faster on cache hit
            self.assertLess(cached_time, total_time * 0.1)
        
        from asgiref.sync import sync_to_async
        asyncio.run(run_test())


class SessionPerformanceTest(TransactionTestCase):
    """Test session management performance"""
    
    def setUp(self):
        """Set up test data"""
        self.user_type = UserType.objects.create(
            name="User",
            slug="user",
            base_permissions={'pipelines': {'actions': ['read']}}
        )
        
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='testpass123',
            user_type=self.user_type
        )
    
    def test_session_cleanup_performance(self):
        """Test performance of session cleanup operations"""
        async def run_test():
            from authentication.session_utils import AsyncSessionManager
            
            # Create multiple sessions (some expired)
            sessions_created = 0
            for i in range(50):
                if i % 2 == 0:
                    # Create expired session
                    expires_at = timezone.now() - timezone.timedelta(hours=1)
                else:
                    # Create active session
                    expires_at = timezone.now() + timezone.timedelta(hours=1)
                
                await sync_to_async(UserSession.objects.create)(
                    user=self.user,
                    session_key=f'test_session_{i}_{"_" * 20}',
                    expires_at=expires_at
                )
                sessions_created += 1
            
            # Test cleanup performance
            start_time = time.time()
            cleaned_count = await AsyncSessionManager.cleanup_expired_sessions()
            cleanup_time = time.time() - start_time
            
            # Should clean up expired sessions quickly (under 100ms)
            self.assertLess(cleanup_time, 0.1)
            
            # Should have cleaned up about half the sessions
            self.assertGreaterEqual(cleaned_count, 20)
            self.assertLessEqual(cleaned_count, 30)
        
        from django.utils import timezone
        from asgiref.sync import sync_to_async
        asyncio.run(run_test())
    
    def test_concurrent_session_operations(self):
        """Test performance of concurrent session operations"""
        async def run_test():
            from authentication.session_utils import AsyncSessionManager
            
            # Test concurrent session creation
            async def create_session(index):
                return await AsyncSessionManager.create_session(
                    user=self.user,
                    session_key=f'concurrent_session_{index}_{"_" * 10}',
                    ip_address='127.0.0.1'
                )
            
            start_time = time.time()
            
            # Create 20 sessions concurrently
            tasks = [create_session(i) for i in range(20)]
            sessions = await asyncio.gather(*tasks)
            
            creation_time = time.time() - start_time
            
            # Should complete quickly (under 500ms)
            self.assertLess(creation_time, 0.5)
            
            # Should have created all sessions
            self.assertEqual(len(sessions), 20)
            
            # All sessions should be valid
            for session in sessions:
                self.assertIsNotNone(session)
                self.assertEqual(session.user, self.user)
        
        asyncio.run(run_test())


class APIPerformanceTest(APITransactionTestCase):
    """Test API endpoint performance"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user_type = UserType.objects.create(
            name="User",
            slug="user",
            base_permissions={
                'pipelines': {'actions': ['read', 'update']},
                'records': {'actions': ['create', 'read']}
            }
        )
        
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='testpass123',
            user_type=self.user_type
        )
    
    def test_login_performance(self):
        """Test login endpoint performance"""
        # Test multiple login attempts
        times = []
        
        for i in range(10):
            start_time = time.time()
            
            response = self.client.post('/api/auth/login/', {
                'username': 'user@example.com',
                'password': 'testpass123'
            })
            
            end_time = time.time()
            times.append(end_time - start_time)
            
            self.assertEqual(response.status_code, 200)
            
            # Logout to clean up session
            self.client.post('/api/auth/logout/')
        
        # Calculate average time
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Login should be fast (under 200ms average, 500ms max)
        self.assertLess(avg_time, 0.2)
        self.assertLess(max_time, 0.5)
    
    def test_permission_endpoint_performance(self):
        """Test permissions endpoint performance"""
        self.client.force_authenticate(user=self.user)
        
        # Test multiple requests
        times = []
        
        for i in range(20):
            start_time = time.time()
            
            response = self.client.get('/api/auth/permissions/')
            
            end_time = time.time()
            times.append(end_time - start_time)
            
            self.assertEqual(response.status_code, 200)
        
        # Calculate performance metrics
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Should be very fast due to caching (under 50ms average, 200ms max)
        self.assertLess(avg_time, 0.05)
        self.assertLess(max_time, 0.2)
    
    def test_current_user_endpoint_performance(self):
        """Test current user endpoint performance"""
        self.client.force_authenticate(user=self.user)
        
        # Test multiple requests
        times = []
        
        for i in range(20):
            start_time = time.time()
            
            response = self.client.get('/api/auth/me/')
            
            end_time = time.time()
            times.append(end_time - start_time)
            
            self.assertEqual(response.status_code, 200)
        
        # Calculate performance metrics
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Should be fast (under 100ms average, 300ms max)
        self.assertLess(avg_time, 0.1)
        self.assertLess(max_time, 0.3)


class DatabaseQueryPerformanceTest(TransactionTestCase):
    """Test database query performance"""
    
    def setUp(self):
        """Set up test data"""
        # Create multiple user types
        self.user_types = []
        for i in range(5):
            user_type = UserType.objects.create(
                name=f"Type {i}",
                slug=f"type_{i}",
                base_permissions={
                    'pipelines': {'actions': ['read']},
                    'records': {'actions': ['read']}
                }
            )
            self.user_types.append(user_type)
        
        # Create multiple users
        self.users = []
        for i in range(20):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='testpass123',
                user_type=self.user_types[i % len(self.user_types)]
            )
            self.users.append(user)
    
    def test_user_type_query_performance(self):
        """Test user type related query performance"""
        async def run_test():
            # Test retrieving user with user type
            start_time = time.time()
            
            for user in self.users:
                # Simulate getting user with user type (select_related equivalent)
                user_with_type = await User.objects.select_related('user_type').aget(id=user.id)
                self.assertIsNotNone(user_with_type.user_type)
            
            query_time = time.time() - start_time
            
            # Should complete quickly (under 500ms for 20 queries)
            self.assertLess(query_time, 0.5)
            
            # Average per query should be under 25ms
            avg_time = query_time / len(self.users)
            self.assertLess(avg_time, 0.025)
        
        asyncio.run(run_test())
    
    def test_permission_manager_query_performance(self):
        """Test permission manager query performance"""
        async def run_test():
            start_time = time.time()
            
            # Test permission calculation for multiple users
            for user in self.users[:10]:  # Test first 10 users
                pm = AsyncPermissionManager(user)
                permissions = await pm.get_user_permissions()
                self.assertIsInstance(permissions, dict)
            
            calculation_time = time.time() - start_time
            
            # Should complete quickly (under 200ms for 10 users)
            self.assertLess(calculation_time, 0.2)
            
            # Now test with cache hits
            start_time = time.time()
            
            for user in self.users[:10]:
                pm = AsyncPermissionManager(user)
                permissions = await pm.get_user_permissions()
                self.assertIsInstance(permissions, dict)
            
            cached_time = time.time() - start_time
            
            # Cache hits should be much faster
            self.assertLess(cached_time, calculation_time * 0.1)
        
        asyncio.run(run_test())