"""
Test cases for authentication models
Tests CustomUser, UserType, UserSession, and related models
"""

import asyncio
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from authentication.models import UserType, UserSession, ExtendedPermission, UserTypePermission

User = get_user_model()


class UserModelTest(TestCase):
    """Test CustomUser model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user_type = UserType.objects.create(
            name="Test Type",
            slug="test_type",
            base_permissions={
                'pipelines': {'actions': ['read', 'update']},
                'records': {'actions': ['create', 'read']}
            }
        )
    
    def test_user_creation(self):
        """Test custom user creation"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type=self.user_type
        )
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.user_type, self.user_type)
        self.assertTrue(user.check_password('testpass123'))
        self.assertIsNotNone(user.created_at)
        self.assertEqual(str(user), 'test@example.com ( )')
    
    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.assertEqual(str(user), 'test@example.com (Test User)')
    
    def test_user_metadata_field(self):
        """Test user metadata JSONB field"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            metadata={'preference': 'dark_mode', 'language': 'en'}
        )
        
        self.assertEqual(user.metadata['preference'], 'dark_mode')
        self.assertEqual(user.metadata['language'], 'en')
    
    def test_permission_overrides_field(self):
        """Test permission overrides JSONB field"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            permission_overrides={
                'records': {'actions': ['read']}  # Override to remove create permission
            }
        )
        
        self.assertEqual(user.permission_overrides['records']['actions'], ['read'])


class AsyncUserModelTest(TransactionTestCase):
    """Test async methods on CustomUser model"""
    
    def setUp(self):
        """Set up test data"""
        self.user_type = UserType.objects.create(
            name="Test Type",
            slug="test_type",
            base_permissions={
                'pipelines': {'actions': ['read', 'update']},
                'records': {'actions': ['create', 'read']}
            }
        )
    
    def test_async_update_last_activity(self):
        """Test async last activity update"""
        async def run_test():
            user = await sync_to_async(User.objects.create_user)(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            
            self.assertIsNone(user.last_activity)
            
            await user.aupdate_last_activity()
            self.assertIsNotNone(user.last_activity)
            
            # Check that it was actually saved to database
            refreshed_user = await User.objects.aget(id=user.id)
            self.assertIsNotNone(refreshed_user.last_activity)
        
        asyncio.run(run_test())


class UserTypeModelTest(TestCase):
    """Test UserType model functionality"""
    
    def test_user_type_creation(self):
        """Test user type creation"""
        user_type = UserType.objects.create(
            name="Manager",
            slug="manager",
            description="Management access",
            base_permissions={
                'pipelines': {'actions': ['read', 'update', 'create']},
                'users': {'actions': ['read', 'update']}
            }
        )
        
        self.assertEqual(user_type.name, "Manager")
        self.assertEqual(user_type.slug, "manager")
        self.assertTrue(user_type.is_custom)
        self.assertFalse(user_type.is_system_default)
        self.assertEqual(str(user_type), "Manager")
    
    def test_user_type_ordering(self):
        """Test user type ordering by name"""
        UserType.objects.create(name="Zebra", slug="zebra")
        UserType.objects.create(name="Admin", slug="admin")
        UserType.objects.create(name="Manager", slug="manager")
        
        user_types = list(UserType.objects.all())
        names = [ut.name for ut in user_types]
        
        self.assertEqual(names, ['Admin', 'Manager', 'Zebra'])


class AsyncUserTypeTest(TransactionTestCase):
    """Test async methods on UserType model"""
    
    def test_async_create_default_types(self):
        """Test async creation of default user types"""
        async def run_test():
            # Ensure no user types exist initially
            await sync_to_async(UserType.objects.all().delete)()
            
            await UserType.acreate_default_types()
            
            # Check that all default types were created
            admin_type = await UserType.objects.aget(slug='admin')
            manager_type = await UserType.objects.aget(slug='manager')
            user_type = await UserType.objects.aget(slug='user')
            viewer_type = await UserType.objects.aget(slug='viewer')
            
            self.assertEqual(admin_type.name, 'Admin')
            self.assertTrue(admin_type.is_system_default)
            self.assertFalse(admin_type.is_custom)
            
            self.assertEqual(manager_type.name, 'Manager')
            self.assertTrue(manager_type.is_system_default)
            
            self.assertEqual(user_type.name, 'User')
            self.assertEqual(viewer_type.name, 'Viewer')
            
            # Check permissions structure
            self.assertIn('system', admin_type.base_permissions)
            self.assertIn('full_access', admin_type.base_permissions['system']['actions'])
        
        asyncio.run(run_test())


class UserSessionModelTest(TestCase):
    """Test UserSession model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_session_creation(self):
        """Test user session creation"""
        session = UserSession.objects.create(
            user=self.user,
            session_key='test_session_key_12345678901234567890',
            expires_at=timezone.now() + timezone.timedelta(hours=24),
            ip_address='127.0.0.1',
            user_agent='Test User Agent',
            device_info={'browser': 'Chrome', 'os': 'Windows'}
        )
        
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.session_key, 'test_session_key_12345678901234567890')
        self.assertEqual(session.ip_address, '127.0.0.1')
        self.assertEqual(session.device_info['browser'], 'Chrome')
        self.assertIn('testuser', str(session))
    
    def test_session_expiry_check(self):
        """Test session expiry checking"""
        # Create expired session
        expired_session = UserSession.objects.create(
            user=self.user,
            session_key='expired_session_key_1234567890123456',
            expires_at=timezone.now() - timezone.timedelta(hours=1)
        )
        
        # Create active session
        active_session = UserSession.objects.create(
            user=self.user,
            session_key='active_session_key_12345678901234567',
            expires_at=timezone.now() + timezone.timedelta(hours=1)
        )
        
        self.assertTrue(expired_session.is_expired())
        self.assertFalse(active_session.is_expired())


class AsyncUserSessionTest(TransactionTestCase):
    """Test async methods on UserSession model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_async_cleanup_expired_sessions(self):
        """Test async cleanup of expired sessions"""
        async def run_test():
            # Create expired session
            await sync_to_async(UserSession.objects.create)(
                user=self.user,
                session_key='expired_session_key_1234567890123456',
                expires_at=timezone.now() - timezone.timedelta(hours=1)
            )
            
            # Create active session
            await sync_to_async(UserSession.objects.create)(
                user=self.user,
                session_key='active_session_key_12345678901234567',
                expires_at=timezone.now() + timezone.timedelta(hours=1)
            )
            
            # Check initial count
            initial_count = await sync_to_async(UserSession.objects.count)()
            self.assertEqual(initial_count, 2)
            
            # Clean up expired sessions
            cleaned_count = await UserSession.acleanup_expired_sessions()
            self.assertEqual(cleaned_count, 1)
            
            # Check remaining sessions
            remaining_count = await sync_to_async(UserSession.objects.count)()
            self.assertEqual(remaining_count, 1)
            
            # Ensure the remaining session is the active one
            remaining_session = await UserSession.objects.aget()
            self.assertEqual(remaining_session.session_key, 'active_session_key_12345678901234567')
        
        asyncio.run(run_test())


class ExtendedPermissionModelTest(TestCase):
    """Test ExtendedPermission model functionality"""
    
    def test_permission_creation(self):
        """Test extended permission creation"""
        from django.contrib.contenttypes.models import ContentType
        
        # Get or create a content type for testing
        content_type = ContentType.objects.get_for_model(User)
        
        permission = ExtendedPermission.objects.create(
            name='Can manage users',
            codename='manage_users',
            content_type=content_type,
            permission_type='action',
            resource_type='system',
            description='Allows user management'
        )
        
        self.assertEqual(permission.name, 'Can manage users')
        self.assertEqual(permission.permission_type, 'action')
        self.assertEqual(permission.resource_type, 'system')
        self.assertFalse(permission.is_system)
        self.assertEqual(str(permission), 'Can manage users (action)')


class UserTypePermissionModelTest(TestCase):
    """Test UserTypePermission model functionality"""
    
    def setUp(self):
        """Set up test data"""
        from django.contrib.contenttypes.models import ContentType
        
        self.user_type = UserType.objects.create(
            name="Manager",
            slug="manager"
        )
        
        content_type = ContentType.objects.get_for_model(User)
        self.permission = ExtendedPermission.objects.create(
            name='Can manage users',
            codename='manage_users',
            content_type=content_type,
            permission_type='action',
            resource_type='system'
        )
    
    def test_user_type_permission_creation(self):
        """Test user type permission relationship creation"""
        utp = UserTypePermission.objects.create(
            user_type=self.user_type,
            permission=self.permission,
            is_granted=True,
            conditions={'department': 'sales'},
            traversal_depth=2,
            field_restrictions={'salary': {'read': False}}
        )
        
        self.assertEqual(utp.user_type, self.user_type)
        self.assertEqual(utp.permission, self.permission)
        self.assertTrue(utp.is_granted)
        self.assertEqual(utp.conditions['department'], 'sales')
        self.assertEqual(utp.traversal_depth, 2)
        self.assertFalse(utp.field_restrictions['salary']['read'])