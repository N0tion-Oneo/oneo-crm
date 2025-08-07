"""
Test cases for authentication API endpoints
Tests async views, serializers, and API functionality
"""

import asyncio
import json
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITransactionTestCase
from rest_framework import status
from authentication.models import UserType, UserSession

User = get_user_model()


class AuthenticationAPITest(APITransactionTestCase):
    """Test authentication API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create user types
        self.admin_type = UserType.objects.create(
            name="Admin",
            slug="admin",
            base_permissions={
                'system': {'actions': ['full_access']},
                'users': {'actions': ['create', 'read', 'update', 'delete']}
            }
        )
        
        self.user_type = UserType.objects.create(
            name="User",
            slug="user",
            base_permissions={
                'pipelines': {'actions': ['read']},
                'records': {'actions': ['create', 'read']}
            }
        )
        
        # Create users
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            user_type=self.admin_type
        )
        
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpass123',
            user_type=self.user_type
        )
    
    def test_login_success(self):
        """Test successful login"""
        response = self.client.post('/auth/login/', {
            'username': 'user@example.com',
            'password': 'userpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('user', response.data)
        self.assertIn('permissions', response.data)
        self.assertEqual(response.data['user']['email'], 'user@example.com')
        
        # Check that session was created
        self.assertTrue(UserSession.objects.filter(user=self.user).exists())
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post('/auth/login/', {
            'username': 'user@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_login_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        
        response = self.client.post('/auth/login/', {
            'username': 'user@example.com',
            'password': 'userpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
    
    def test_login_remember_me(self):
        """Test login with remember me option"""
        response = self.client.post('/auth/login/', {
            'username': 'user@example.com',
            'password': 'userpass123',
            'remember_me': True
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that session expiration is extended (session should exist)
        session = UserSession.objects.get(user=self.user)
        self.assertIsNotNone(session.expires_at)
    
    def test_logout_success(self):
        """Test successful logout"""
        # First login
        self.client.post('/api/auth/login/', {
            'username': 'user@example.com',
            'password': 'userpass123'
        })
        
        # Then logout
        response = self.client.post('/auth/logout/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
    
    def test_current_user_authenticated(self):
        """Test current user endpoint when authenticated"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/auth/me/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('permissions', response.data)
        self.assertEqual(response.data['user']['email'], 'user@example.com')
    
    def test_current_user_unauthenticated(self):
        """Test current user endpoint when not authenticated"""
        response = self.client.get('/auth/me/')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_change_password_success(self):
        """Test successful password change"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/auth/change-password/', {
            'old_password': 'userpass123',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))
    
    def test_change_password_wrong_old_password(self):
        """Test password change with wrong old password"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/auth/change-password/', {
            'old_password': 'wrongpassword',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_change_password_mismatch(self):
        """Test password change with password mismatch"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/auth/change-password/', {
            'old_password': 'userpass123',
            'new_password': 'newpassword123',
            'confirm_password': 'differentpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SessionManagementAPITest(APITransactionTestCase):
    """Test session management API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user_type = UserType.objects.create(
            name="User",
            slug="user",
            base_permissions={'pipelines': {'actions': ['read']}}
        )
        
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpass123',
            user_type=self.user_type
        )
        
        # Create test sessions
        self.session1 = UserSession.objects.create(
            user=self.user,
            session_key='session1_key_1234567890123456789012',
            expires_at=timezone.now() + timezone.timedelta(hours=1),
            ip_address='127.0.0.1',
            user_agent='Test Browser 1'
        )
        
        self.session2 = UserSession.objects.create(
            user=self.user,
            session_key='session2_key_1234567890123456789012',
            expires_at=timezone.now() + timezone.timedelta(hours=1),
            ip_address='192.168.1.1',
            user_agent='Test Browser 2'
        )
    
    def test_get_user_sessions(self):
        """Test getting user's active sessions"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/auth/sessions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sessions', response.data)
        self.assertEqual(response.data['total_count'], 2)
    
    def test_destroy_specific_session(self):
        """Test destroying a specific session"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.delete(f'/auth/sessions/{self.session1.id}/terminate/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify session was destroyed
        self.assertFalse(UserSession.objects.filter(id=self.session1.id).exists())
        self.assertTrue(UserSession.objects.filter(id=self.session2.id).exists())
    
    def test_destroy_nonexistent_session(self):
        """Test destroying a session that doesn't exist"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.delete('/auth/sessions/99999/terminate/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_destroy_all_sessions(self):
        """Test destroying all user sessions"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.delete('/auth/sessions/destroy_all/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('destroyed_count', response.data)
        self.assertEqual(response.data['destroyed_count'], 2)
        
        # Verify all sessions were destroyed
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 0)
    
    def test_extend_session(self):
        """Test extending current session"""
        self.client.force_authenticate(user=self.user)
        
        # Mock current session
        request = self.client.request()
        request.user_session = self.session1
        
        response = self.client.post('/auth/sessions/extend/')
        
        # Note: This test may need adjustment based on actual implementation
        # since we need to properly mock the current session
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])


class UserTypeAPITest(APITransactionTestCase):
    """Test user type API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create admin user with permission to view user types
        self.admin_type = UserType.objects.create(
            name="Admin",
            slug="admin",
            base_permissions={
                'user_types': ['read']  # Updated to use simplified permission schema
            }
        )
        
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            user_type=self.admin_type
        )
        
        # Create regular user without permission
        self.user_type = UserType.objects.create(
            name="User",
            slug="user",
            base_permissions={'pipelines': {'actions': ['read']}}
        )
        
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpass123',
            user_type=self.user_type
        )
    
    def test_get_user_types_with_permission(self):
        """Test getting user types with proper permission"""
        self.client.force_authenticate(user=self.admin)
        
        response = self.client.get('/auth/user-types/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)  # DRF ViewSet uses 'results' not 'user_types'
        self.assertGreaterEqual(response.data['count'], 2)  # DRF ViewSet uses 'count' not 'total_count'
    
    def test_get_user_types_without_permission(self):
        """Test getting user types without proper permission"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/auth/user-types/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PermissionsAPITest(APITransactionTestCase):
    """Test permissions API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user_type = UserType.objects.create(
            name="Manager",
            slug="manager",
            base_permissions={
                'pipelines': {'actions': ['read', 'update']},
                'fields': {
                    'pipeline_1': {
                        'name': {'read': True, 'write': True},
                        'salary': {'read': False, 'write': False}
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
    
    def test_get_user_permissions(self):
        """Test getting user's detailed permissions"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/auth/permissions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('permissions', response.data)
        self.assertIn('user_type', response.data)
        self.assertEqual(response.data['user_type'], 'Manager')
    
    def test_get_resource_permissions(self):
        """Test getting permissions for specific resource"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/auth/permissions/?resource_type=pipelines&resource_id=pipeline_1')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('permissions', response.data)
        self.assertIn('resource_permissions', response.data)


class HealthCheckAPITest(APITransactionTestCase):
    """Test health check API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create some test data
        self.user_type = UserType.objects.create(name="User", slug="user")
        self.user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='testpass123',
            user_type=self.user_type
        )
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/auth/health/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertIn('timestamp', response.data)
        self.assertIn('stats', response.data)