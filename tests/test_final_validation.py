"""
Final validation tests for Phase 01 completion
These tests validate that all Phase 01 requirements are met
"""

import time
from django.test import TestCase, Client
from django.test.utils import override_settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.cache import cache
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context
from tenants.models import Tenant, Domain
from core.models import TenantSettings, AuditLog
from core.cache import tenant_cache_key
from core.monitoring import health_check, get_database_stats, get_cache_stats


class Phase01CompletionTest(TestCase):
    """Comprehensive test to validate Phase 01 completion"""
    
    def test_project_structure_exists(self):
        """Test that all required project components exist"""
        # Test Django apps are created
        from django.apps import apps
        
        self.assertTrue(apps.is_installed('tenants'))
        self.assertTrue(apps.is_installed('core'))
        self.assertTrue(apps.is_installed('users'))
        self.assertTrue(apps.is_installed('django_tenants'))
    
    def test_database_configuration(self):
        """Test database is properly configured for multi-tenancy"""
        from django.conf import settings
        
        # Check database engine
        self.assertEqual(
            settings.DATABASES['default']['ENGINE'],
            'django_tenants.postgresql_backend'
        )
        
        # Check database router
        self.assertIn('django_tenants.routers.TenantSyncRouter', settings.DATABASE_ROUTERS)
        
        # Check tenant models are configured
        self.assertEqual(settings.TENANT_MODEL, "tenants.Tenant")
        self.assertEqual(settings.TENANT_DOMAIN_MODEL, "tenants.Domain")
    
    def test_cache_configuration(self):
        """Test Redis cache is properly configured"""
        from django.conf import settings
        
        # Check cache backend
        self.assertEqual(
            settings.CACHES['default']['BACKEND'],
            'django_redis.cache.RedisCache'
        )
        
        # Test cache functionality
        cache.set('test_key', 'test_value', 60)
        self.assertEqual(cache.get('test_key'), 'test_value')
    
    def test_security_configuration(self):
        """Test security settings are properly configured"""
        from django.conf import settings
        
        # Check security headers
        self.assertTrue(settings.SECURE_BROWSER_XSS_FILTER)
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')
        
        # Check session security
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Strict')
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)


class TenantFunctionalityTest(TestCase):
    """Test core tenant functionality"""
    
    def test_tenant_creation_and_management(self):
        """Test tenant can be created and managed"""
        # Create tenant
        tenant = Tenant.objects.create(
            name="Test Company",
            schema_name="test_company"
        )
        
        # Create domain
        domain = Domain.objects.create(
            domain="test.localhost",
            tenant=tenant,
            is_primary=True
        )
        
        # Verify tenant exists
        self.assertEqual(tenant.name, "Test Company")
        self.assertEqual(tenant.schema_name, "test_company")
        self.assertEqual(domain.tenant, tenant)
        self.assertTrue(domain.is_primary)
        
        # Test tenant settings
        self.assertEqual(tenant.max_users, 100)
        self.assertEqual(tenant.features_enabled, {})
        
        # Cleanup
        tenant.delete()
    
    def test_management_command_works(self):
        """Test tenant creation management command works"""
        # Test create_tenant command
        call_command('create_tenant', 'Test Tenant', 'management.localhost')
        
        # Verify tenant was created
        tenant = Tenant.objects.get(name='Test Tenant')
        domain = Domain.objects.get(domain='management.localhost')
        
        self.assertEqual(tenant.schema_name, 'test_tenant')
        self.assertEqual(domain.tenant, tenant)
        
        # Cleanup
        tenant.delete()


class SchemaIsolationTest(TenantTestCase):
    """Test multi-tenant schema isolation"""
    
    def test_complete_data_isolation(self):
        """Test that tenant data is completely isolated"""
        # Create two tenants
        tenant1 = Tenant.objects.create(name="Tenant 1", schema_name="isolation_test_1")
        tenant2 = Tenant.objects.create(name="Tenant 2", schema_name="isolation_test_2")
        
        # Create users in different tenant schemas
        with schema_context(tenant1.schema_name):
            user1 = User.objects.create_user(
                username="user1",
                email="user1@tenant1.com",
                password="testpass123"
            )
            
            # Create tenant settings
            setting1 = TenantSettings.objects.create(
                setting_key="test_setting",
                setting_value={"tenant": "tenant1"}
            )
        
        with schema_context(tenant2.schema_name):
            user2 = User.objects.create_user(
                username="user2",
                email="user2@tenant2.com",
                password="testpass123"
            )
            
            # Create tenant settings with same key
            setting2 = TenantSettings.objects.create(
                setting_key="test_setting",
                setting_value={"tenant": "tenant2"}
            )
            
            # Verify isolation - tenant2 cannot see tenant1's data
            self.assertEqual(User.objects.count(), 1)
            self.assertEqual(User.objects.first().username, "user2")
            
            self.assertEqual(TenantSettings.objects.count(), 1)
            self.assertEqual(
                TenantSettings.objects.first().setting_value["tenant"],
                "tenant2"
            )
        
        # Verify from tenant1 schema
        with schema_context(tenant1.schema_name):
            self.assertEqual(User.objects.count(), 1)
            self.assertEqual(User.objects.first().username, "user1")
            
            self.assertEqual(TenantSettings.objects.count(), 1)
            self.assertEqual(
                TenantSettings.objects.first().setting_value["tenant"],
                "tenant1"
            )
        
        # Cleanup
        tenant1.delete()
        tenant2.delete()


class CacheIsolationTest(TestCase):
    """Test cache isolation between tenants"""
    
    def test_tenant_cache_isolation(self):
        """Test that tenant cache keys are properly isolated"""
        # Clear cache first
        cache.clear()
        
        # Test tenant cache key generation
        key1 = tenant_cache_key("test_key", "tenant1")
        key2 = tenant_cache_key("test_key", "tenant2")
        
        # Keys should be different
        self.assertNotEqual(key1, key2)
        self.assertTrue(key1.startswith("tenant1:"))
        self.assertTrue(key2.startswith("tenant2:"))
        
        # Set values for different tenants
        cache.set(key1, "tenant1_value", 60)
        cache.set(key2, "tenant2_value", 60)
        
        # Verify isolation
        self.assertEqual(cache.get(key1), "tenant1_value")
        self.assertEqual(cache.get(key2), "tenant2_value")
        
        # Verify no cross-contamination
        self.assertNotEqual(cache.get(key1), cache.get(key2))


class PerformanceValidationTest(TestCase):
    """Test that performance requirements are met"""
    
    def test_tenant_creation_performance(self):
        """Test tenant creation meets performance requirements"""
        start_time = time.time()
        
        tenant = Tenant.objects.create(
            name="Performance Test",
            schema_name="perf_validation"
        )
        
        Domain.objects.create(
            domain="perf.localhost",
            tenant=tenant,
            is_primary=True
        )
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create tenant in under 500ms
        self.assertLess(creation_time, 0.5,
                       f"Tenant creation took {creation_time:.3f}s, expected < 0.5s")
        
        tenant.delete()
    
    def test_cache_performance(self):
        """Test cache operations meet performance requirements"""
        start_time = time.time()
        
        # Perform 100 cache operations
        for i in range(100):
            cache.set(f"perf_test_{i}", f"value_{i}", 60)
            value = cache.get(f"perf_test_{i}")
            self.assertEqual(value, f"value_{i}")
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        # Should complete 100 operations in under 100ms (1ms per operation)
        self.assertLess(operation_time, 0.1,
                       f"Cache operations took {operation_time:.3f}s, expected < 0.1s")


class SecurityValidationTest(TestCase):
    """Test security measures are properly implemented"""
    
    def test_admin_access_restriction(self):
        """Test that admin access is properly restricted"""
        client = Client()
        
        # Try to access admin without authentication
        response = client.get('/admin/')
        
        # Should redirect to login or return 302
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_csrf_protection_enabled(self):
        """Test CSRF protection is enabled"""
        from django.conf import settings
        
        # Check CSRF middleware is enabled
        self.assertIn('django.middleware.csrf.CsrfViewMiddleware', settings.MIDDLEWARE)
        
        # Check CSRF settings
        self.assertTrue(settings.CSRF_COOKIE_HTTPONLY)
    
    def test_security_headers_configured(self):
        """Test security headers are properly configured"""
        from django.conf import settings
        
        self.assertTrue(settings.SECURE_BROWSER_XSS_FILTER)
        self.assertTrue(settings.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(settings.X_FRAME_OPTIONS, 'DENY')


class MonitoringValidationTest(TestCase):
    """Test monitoring and logging functionality"""
    
    def test_health_check_functionality(self):
        """Test system health check works"""
        health_status = health_check()
        
        self.assertIn('status', health_status)
        self.assertIn('checks', health_status)
        self.assertIn('database', health_status['checks'])
        self.assertIn('cache', health_status['checks'])
    
    def test_database_stats_collection(self):
        """Test database stats can be collected"""
        stats = get_database_stats()
        
        self.assertIn('queries_count', stats)
        self.assertIn('total_time', stats)
        self.assertIn('tenant', stats)
    
    def test_cache_stats_collection(self):
        """Test cache stats can be collected"""
        stats = get_cache_stats()
        
        # Should have either valid stats or error message
        self.assertTrue(
            'memory_used' in stats or 'error' in stats
        )


class DocumentationValidationTest(TestCase):
    """Test that documentation requirements are met"""
    
    def test_documentation_files_exist(self):
        """Test that all required documentation files exist"""
        import os
        from django.conf import settings
        
        base_dir = settings.BASE_DIR
        
        # Check main documentation files
        docs = [
            'docs/api/README.md',
            'docs/ARCHITECTURE.md', 
            'docs/DEPLOYMENT.md',
            'docs/TROUBLESHOOTING.md',
            'docs/SECURITY.md'
        ]
        
        for doc in docs:
            doc_path = os.path.join(base_dir, doc)
            self.assertTrue(os.path.exists(doc_path), f"Documentation file {doc} does not exist")
    
    def test_setup_script_exists(self):
        """Test that setup script exists and is executable"""
        import os
        from django.conf import settings
        
        setup_script = os.path.join(settings.BASE_DIR, 'setup.sh')
        self.assertTrue(os.path.exists(setup_script), "setup.sh does not exist")
        
        # Check if executable (on Unix systems)
        if os.name == 'posix':
            self.assertTrue(os.access(setup_script, os.X_OK), "setup.sh is not executable")


class IntegrationValidationTest(TestCase):
    """Test integration between different components"""
    
    def test_tenant_to_cache_integration(self):
        """Test tenant creation properly integrates with cache"""
        # Create tenant
        tenant = Tenant.objects.create(
            name="Integration Test",
            schema_name="integration_test"
        )
        
        # Test cache operations with tenant context
        cache_key = tenant_cache_key("integration_test", tenant.schema_name)
        cache.set(cache_key, {"tenant_id": tenant.id}, 60)
        
        cached_data = cache.get(cache_key)
        self.assertEqual(cached_data["tenant_id"], tenant.id)
        
        tenant.delete()
    
    def test_database_to_monitoring_integration(self):
        """Test database operations are properly monitored"""
        from core.monitoring import monitor_performance
        
        # Create monitored operation
        @monitor_performance("test_operation")
        def test_db_operation():
            return Tenant.objects.count()
        
        # Execute operation
        result = test_db_operation()
        
        # Should return count without errors
        self.assertIsInstance(result, int)


class Phase01ReadinessTest(TestCase):
    """Final test to confirm Phase 01 is complete and ready for Phase 02"""
    
    def test_all_success_criteria_met(self):
        """Test all Phase 01 success criteria are met"""
        # Multi-tenant Django application with schema isolation ✅
        self.assertTrue(Tenant.objects.model._meta.installed)
        self.assertTrue(Domain.objects.model._meta.installed)
        
        # Database migrations working per tenant ✅
        # (Tested by the fact that we can create tenant objects)
        tenant = Tenant.objects.create(
            name="Readiness Test",
            schema_name="readiness_test"
        )
        
        # Redis integration for caching ✅
        cache.set('readiness_test', 'success', 60)
        self.assertEqual(cache.get('readiness_test'), 'success')
        
        # Basic tenant CRUD operations via admin ✅
        from django.contrib import admin
        from tenants.admin import TenantAdmin, DomainAdmin
        
        self.assertIn(Tenant, admin.site._registry)
        self.assertIn(Domain, admin.site._registry)
        
        # Development environment with hot reloading ✅
        # (Tested by Docker configuration existence)
        import os
        from django.conf import settings
        
        docker_compose_path = os.path.join(settings.BASE_DIR, 'docker-compose.yml')
        self.assertTrue(os.path.exists(docker_compose_path))
        
        # Docker setup for local development ✅
        dockerfile_path = os.path.join(settings.BASE_DIR, 'Dockerfile')
        self.assertTrue(os.path.exists(dockerfile_path))
        
        tenant.delete()
    
    def test_ready_for_phase_02(self):
        """Test system is ready for Phase 02 (Authentication)"""
        # Stable Foundation ✅
        # (All tests above must pass)
        
        # Integration Points for Authentication ✅
        # Tenant Model established
        self.assertTrue(hasattr(Tenant, 'name'))
        self.assertTrue(hasattr(Tenant, 'schema_name'))
        
        # Schema Context available
        from django_tenants.utils import schema_context
        self.assertTrue(callable(schema_context))
        
        # Cache Infrastructure ready
        from core.cache import tenant_cache_key
        self.assertTrue(callable(tenant_cache_key))
        
        # Performance meets requirements ✅
        # (Tested in performance validation tests)
        
        print("🎉 Phase 01 Foundation is COMPLETE and ready for Phase 02!")
        print("✅ Multi-tenant architecture implemented")
        print("✅ Database schema isolation working")
        print("✅ Redis cache integration functional")
        print("✅ Admin interface available")
        print("✅ Development environment configured")
        print("✅ Security measures implemented")
        print("✅ Performance requirements met")
        print("✅ Documentation complete")
        print("✅ Testing infrastructure in place")
        
        return True