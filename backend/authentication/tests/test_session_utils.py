"""
Test cases for session management utilities
Tests AsyncSessionManager and session-related functionality
"""

import asyncio
from datetime import timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.http import HttpRequest
from authentication.models import UserType, UserSession
from authentication.session_utils import (
    AsyncSessionManager, create_user_session, validate_user_session,
    destroy_user_session, cleanup_expired_sessions
)

User = get_user_model()


class AsyncSessionManagerTest(TransactionTestCase):
    """Test AsyncSessionManager functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user_type = UserType.objects.create(
            name="User",
            slug="user",
            base_permissions={'pipelines': {'actions': ['read']}}
        )
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type=self.user_type
        )
    
    def test_create_session(self):
        """Test session creation"""
        async def run_test():
            session = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='127.0.0.1',
                user_agent='Test Browser',
                device_info={'browser': 'Chrome', 'os': 'Windows'}
            )
            
            self.assertIsNotNone(session)
            self.assertEqual(session.user, self.user)
            self.assertEqual(session.ip_address, '127.0.0.1')
            self.assertEqual(session.user_agent, 'Test Browser')
            self.assertEqual(session.device_info['browser'], 'Chrome')
            self.assertIsNotNone(session.session_key)
            self.assertEqual(len(session.session_key), 40)  # Should be 40 char hex
        
        asyncio.run(run_test())
    
    def test_create_session_with_request(self):
        """Test session creation with Django request object"""
        async def run_test():
            # Create mock request
            request = HttpRequest()
            request.META = {
                'HTTP_X_FORWARDED_FOR': '192.168.1.1, 127.0.0.1',
                'HTTP_USER_AGENT': 'Mozilla/5.0 Test Browser',
                'HTTP_SEC_CH_UA_PLATFORM': 'Windows',
                'HTTP_SEC_CH_UA': 'Chrome'
            }
            
            # Mock session
            class MockSession:
                def cycle_key(self):
                    pass
                def save(self):
                    pass
                session_key = 'mock_session_key_1234567890123456789012345'
            
            request.session = MockSession()
            
            session = await AsyncSessionManager.create_session(
                user=self.user,
                request=request
            )
            
            self.assertIsNotNone(session)
            self.assertEqual(session.user, self.user)
            self.assertEqual(session.ip_address, '192.168.1.1')  # Should use first IP
            self.assertEqual(session.user_agent, 'Mozilla/5.0 Test Browser')
        
        asyncio.run(run_test())
    
    def test_get_session(self):
        """Test session retrieval"""
        async def run_test():
            # Create session first
            created_session = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            
            # Retrieve session
            retrieved_session = await AsyncSessionManager.get_session(created_session.session_key)
            
            self.assertIsNotNone(retrieved_session)
            self.assertEqual(retrieved_session.id, created_session.id)
            self.assertEqual(retrieved_session.user, self.user)
        
        asyncio.run(run_test())
    
    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session"""
        async def run_test():
            session = await AsyncSessionManager.get_session('nonexistent_session_key_123456789012')
            self.assertIsNone(session)
        
        asyncio.run(run_test())
    
    def test_validate_session(self):
        """Test session validation"""
        async def run_test():
            # Create valid session
            created_session = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            
            # Validate session
            validated_user = await AsyncSessionManager.validate_session(created_session.session_key)
            
            self.assertIsNotNone(validated_user)
            self.assertEqual(validated_user, self.user)
        
        asyncio.run(run_test())
    
    def test_validate_expired_session(self):
        """Test validation of expired session"""
        async def run_test():
            from asgiref.sync import sync_to_async
            
            # Create expired session
            expired_session = await sync_to_async(UserSession.objects.create)(
                user=self.user,
                session_key='expired_session_key_1234567890123456789',
                expires_at=timezone.now() - timedelta(hours=1),
                ip_address='127.0.0.1'
            )
            
            # Validate session (should fail and cleanup)
            validated_user = await AsyncSessionManager.validate_session(expired_session.session_key)
            
            self.assertIsNone(validated_user)
            
            # Session should be deleted
            session_exists = await sync_to_async(
                UserSession.objects.filter(id=expired_session.id).exists
            )()
            self.assertFalse(session_exists)
        
        asyncio.run(run_test())
    
    def test_update_session_activity(self):
        """Test session activity update"""
        async def run_test():
            from asgiref.sync import sync_to_async
            
            # Create session
            session = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            
            original_activity = session.last_activity
            
            # Wait a moment
            import time
            time.sleep(0.1)
            
            # Update activity
            await AsyncSessionManager.update_session_activity(session)
            
            # Refresh from database
            refreshed_session = await sync_to_async(UserSession.objects.get)(id=session.id)
            
            self.assertGreater(refreshed_session.last_activity, original_activity)
        
        asyncio.run(run_test())
    
    def test_extend_session(self):
        """Test session extension"""
        async def run_test():
            # Create session
            session = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            
            original_expires = session.expires_at
            
            # Extend session
            success = await AsyncSessionManager.extend_session(
                session.session_key,
                additional_time=timedelta(hours=2)
            )
            
            self.assertTrue(success)
            
            # Check that expiration was extended
            extended_session = await AsyncSessionManager.get_session(session.session_key)
            self.assertGreater(extended_session.expires_at, original_expires)
        
        asyncio.run(run_test())
    
    def test_destroy_session(self):
        """Test session destruction"""
        async def run_test():
            from asgiref.sync import sync_to_async
            
            # Create session
            session = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            
            session_id = session.id
            
            # Destroy session
            success = await AsyncSessionManager.destroy_session(session.session_key)
            self.assertTrue(success)
            
            # Check that session was deleted
            session_exists = await sync_to_async(
                UserSession.objects.filter(id=session_id).exists
            )()
            self.assertFalse(session_exists)
        
        asyncio.run(run_test())
    
    def test_destroy_all_user_sessions(self):
        """Test destroying all sessions for a user"""
        async def run_test():
            from asgiref.sync import sync_to_async
            
            # Create multiple sessions
            session1 = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            session2 = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='192.168.1.1'
            )
            session3 = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='10.0.0.1'
            )
            
            # Destroy all sessions
            destroyed_count = await AsyncSessionManager.destroy_all_user_sessions(self.user)
            
            self.assertEqual(destroyed_count, 3)
            
            # Check that all sessions were deleted
            remaining_sessions = await sync_to_async(
                UserSession.objects.filter(user=self.user).count
            )()
            self.assertEqual(remaining_sessions, 0)
        
        asyncio.run(run_test())
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions"""
        async def run_test():
            from asgiref.sync import sync_to_async
            
            # Create mix of expired and active sessions
            expired1 = await sync_to_async(UserSession.objects.create)(
                user=self.user,
                session_key='expired1_key_1234567890123456789012345',
                expires_at=timezone.now() - timedelta(hours=1),
                ip_address='127.0.0.1'
            )
            
            expired2 = await sync_to_async(UserSession.objects.create)(
                user=self.user,
                session_key='expired2_key_1234567890123456789012345',
                expires_at=timezone.now() - timedelta(hours=2),
                ip_address='127.0.0.1'
            )
            
            active = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            
            # Cleanup expired sessions
            cleaned_count = await AsyncSessionManager.cleanup_expired_sessions()
            
            self.assertEqual(cleaned_count, 2)
            
            # Check that only active session remains
            remaining_sessions = await sync_to_async(
                UserSession.objects.filter(user=self.user).count
            )()
            self.assertEqual(remaining_sessions, 1)
            
            # Check that the remaining session is the active one
            remaining_session = await sync_to_async(
                UserSession.objects.filter(user=self.user).first
            )()
            self.assertEqual(remaining_session.id, active.id)
        
        asyncio.run(run_test())
    
    def test_get_user_sessions(self):
        """Test getting user sessions"""
        async def run_test():
            from asgiref.sync import sync_to_async
            
            # Create mix of expired and active sessions
            await sync_to_async(UserSession.objects.create)(
                user=self.user,
                session_key='expired_key_12345678901234567890123456',
                expires_at=timezone.now() - timedelta(hours=1),
                ip_address='127.0.0.1'
            )
            
            active1 = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            
            active2 = await AsyncSessionManager.create_session(
                user=self.user,
                ip_address='192.168.1.1'
            )
            
            # Get active sessions only
            active_sessions = await AsyncSessionManager.get_user_sessions(
                self.user, active_only=True
            )
            
            self.assertEqual(len(active_sessions), 2)
            
            # Get all sessions
            all_sessions = await AsyncSessionManager.get_user_sessions(
                self.user, active_only=False
            )
            
            self.assertEqual(len(all_sessions), 3)
        
        asyncio.run(run_test())
    
    def test_generate_session_key(self):
        """Test session key generation"""
        key1 = AsyncSessionManager.generate_session_key()
        key2 = AsyncSessionManager.generate_session_key()
        
        # Keys should be 40 characters (20 bytes hex)
        self.assertEqual(len(key1), 40)
        self.assertEqual(len(key2), 40)
        
        # Keys should be different
        self.assertNotEqual(key1, key2)
        
        # Keys should be hex
        try:
            int(key1, 16)
            int(key2, 16)
        except ValueError:
            self.fail("Generated keys should be valid hex")
    
    def test_extract_client_info(self):
        """Test client information extraction"""
        # Test with X-Forwarded-For header
        request = HttpRequest()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '192.168.1.1, 127.0.0.1',
            'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'REMOTE_ADDR': '10.0.0.1'
        }
        
        client_info = AsyncSessionManager.extract_client_info(request)
        
        self.assertEqual(client_info['ip_address'], '192.168.1.1')
        self.assertIn('Mozilla/5.0', client_info['user_agent'])
        self.assertEqual(client_info['device_info']['os'], 'Windows')
        self.assertEqual(client_info['device_info']['device_type'], 'Desktop')
        
        # Test without X-Forwarded-For header
        request.META = {
            'HTTP_USER_AGENT': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            'REMOTE_ADDR': '10.0.0.1'
        }
        
        client_info = AsyncSessionManager.extract_client_info(request)
        
        self.assertEqual(client_info['ip_address'], '10.0.0.1')
        self.assertEqual(client_info['device_info']['os'], 'iOS')
        self.assertEqual(client_info['device_info']['device_type'], 'Mobile')
    
    def test_parse_user_agent(self):
        """Test user agent parsing"""
        # Test Chrome on Windows
        chrome_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        device_info = AsyncSessionManager.parse_user_agent(chrome_ua)
        
        self.assertEqual(device_info['browser'], 'Chrome')
        self.assertEqual(device_info['os'], 'Windows')
        self.assertEqual(device_info['device_type'], 'Desktop')
        
        # Test Safari on iPhone
        safari_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        device_info = AsyncSessionManager.parse_user_agent(safari_ua)
        
        self.assertEqual(device_info['browser'], 'Safari')
        self.assertEqual(device_info['os'], 'iOS')
        self.assertEqual(device_info['device_type'], 'Mobile')
        
        # Test Firefox on Linux
        firefox_ua = 'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0'
        device_info = AsyncSessionManager.parse_user_agent(firefox_ua)
        
        self.assertEqual(device_info['browser'], 'Firefox')
        self.assertEqual(device_info['os'], 'Linux')
        self.assertEqual(device_info['device_type'], 'Desktop')


class SessionUtilityFunctionsTest(TransactionTestCase):
    """Test convenience utility functions"""
    
    def setUp(self):
        """Set up test data"""
        self.user_type = UserType.objects.create(
            name="User",
            slug="user",
            base_permissions={'pipelines': {'actions': ['read']}}
        )
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type=self.user_type
        )
    
    def test_create_user_session_function(self):
        """Test create_user_session convenience function"""
        async def run_test():
            session = await create_user_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            
            self.assertIsNotNone(session)
            self.assertEqual(session.user, self.user)
        
        asyncio.run(run_test())
    
    def test_validate_user_session_function(self):
        """Test validate_user_session convenience function"""
        async def run_test():
            # Create session
            session = await create_user_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            
            # Validate session
            validated_user = await validate_user_session(session.session_key)
            
            self.assertEqual(validated_user, self.user)
        
        asyncio.run(run_test())
    
    def test_destroy_user_session_function(self):
        """Test destroy_user_session convenience function"""
        async def run_test():
            # Create session
            session = await create_user_session(
                user=self.user,
                ip_address='127.0.0.1'
            )
            
            # Destroy session
            success = await destroy_user_session(session.session_key)
            
            self.assertTrue(success)
        
        asyncio.run(run_test())
    
    def test_cleanup_expired_sessions_function(self):
        """Test cleanup_expired_sessions convenience function"""
        async def run_test():
            from asgiref.sync import sync_to_async
            
            # Create expired session
            await sync_to_async(UserSession.objects.create)(
                user=self.user,
                session_key='expired_session_key_1234567890123456789',
                expires_at=timezone.now() - timedelta(hours=1),
                ip_address='127.0.0.1'
            )
            
            # Cleanup
            cleaned_count = await cleanup_expired_sessions()
            
            self.assertEqual(cleaned_count, 1)
        
        asyncio.run(run_test())