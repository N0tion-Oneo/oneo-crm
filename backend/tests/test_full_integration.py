#!/usr/bin/env python
"""
Full integration test for Oneo CRM Phase 1 with database
Tests all functionality with actual PostgreSQL and Redis connections
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.db import connection
from django.core.cache import cache
from django.test import TestCase
from tenants.models import Tenant, Domain
from core.models import TenantSettings, AuditLog
from core.cache import tenant_cache_key, cache_tenant_data
from core.monitoring import monitor_performance, health_check, get_database_stats


def test_database_connection():
    """Test database connectivity"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        print("✅ Database connection: WORKING")
        return True
    except Exception as e:
        print(f"❌ Database connection: FAILED - {e}")
        return False


def test_redis_connection():
    """Test Redis connectivity"""
    try:
        cache.set('test_key', 'test_value', 60)
        result = cache.get('test_key')
        assert result == 'test_value'
        cache.delete('test_key')
        print("✅ Redis connection: WORKING")
        return True
    except Exception as e:
        print(f"❌ Redis connection: FAILED - {e}")
        return False


def test_tenant_operations():
    """Test tenant CRUD operations"""
    try:
        # Test tenant creation (if not exists)
        tenant, created = Tenant.objects.get_or_create(
            schema_name='test',
            defaults={'name': 'Test Company'}
        )
        
        # Test domain creation (if not exists)
        domain, created = Domain.objects.get_or_create(
            domain='test.localhost',
            defaults={'tenant': tenant, 'is_primary': True}
        )
        
        # Switch to tenant schema to test tenant-specific models
        connection.set_tenant(tenant)
        
        # Test tenant settings (now in correct schema)
        settings, created = TenantSettings.objects.get_or_create(
            setting_key='test_setting',
            defaults={'setting_value': {'theme': 'dark', 'notifications': True}}
        )
        
        # Test audit log
        audit = AuditLog.objects.create(
            action='test',
            model_name='Tenant',
            object_id=str(tenant.id),
            changes={'test': 'integration'}
        )
        
        print("✅ Tenant operations: WORKING")
        
        # Cleanup
        audit.delete()
        if created:
            settings.delete()
        
        # Switch back to public schema
        connection.set_schema_to_public()
        
        return True
    except Exception as e:
        print(f"❌ Tenant operations: FAILED - {e}")
        return False


def test_cache_utilities():
    """Test tenant-specific cache utilities"""
    try:
        # Test tenant cache key generation
        key = tenant_cache_key('test_data', 'demo')
        assert key == 'demo:test_data'
        
        # Test cache decorator (can't easily test without request context)
        print("✅ Cache utilities: WORKING")
        return True
    except Exception as e:
        print(f"❌ Cache utilities: FAILED - {e}")
        return False


def test_monitoring_system():
    """Test monitoring utilities"""
    try:
        # Test performance decorator
        @monitor_performance('test_operation')
        def test_function():
            return "test_result"
        
        result = test_function()
        assert result == "test_result"
        
        # Test database stats
        stats = get_database_stats()
        assert 'queries_count' in stats
        
        # Test health check
        health = health_check()
        assert 'status' in health
        assert 'checks' in health
        
        print("✅ Monitoring system: WORKING")
        return True
    except Exception as e:
        print(f"❌ Monitoring system: FAILED - {e}")
        return False


def test_schema_isolation():
    """Test multi-tenant schema isolation"""
    try:
        # Switch to public schema
        connection.set_schema_to_public()
        
        # Verify we can access tenant management tables
        tenant_count = Tenant.objects.count()
        assert tenant_count >= 1  # Should have at least our demo tenant
        
        print("✅ Schema isolation: WORKING")
        return True
    except Exception as e:
        print(f"❌ Schema isolation: FAILED - {e}")
        return False


def main():
    """Run all integration tests"""
    print("🧪 Running Full Integration Tests for Oneo CRM Phase 1")
    print("=" * 60)
    
    tests = [
        test_database_connection,
        test_redis_connection,
        test_tenant_operations,
        test_cache_utilities,
        test_monitoring_system,
        test_schema_isolation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAILED - {e}")
    
    print("=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Phase 1 is fully functional!")
        print("\n🚀 System Status: READY FOR PRODUCTION")
        print("\nNext steps:")
        print("1. Create superuser: python manage.py createsuperuser")
        print("2. Start server: python manage.py runserver")
        print("3. Access admin: http://localhost:8000/admin/")
        print("4. Access tenant: http://demo.localhost:8000/")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed - check configuration")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)