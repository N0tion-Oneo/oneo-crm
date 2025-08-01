#!/usr/bin/env python
"""
Phase 1 Basic Functionality Test
Tests that don't require database or Redis connections
"""

import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        from tenants.models import Tenant, Domain
        from core.models import TenantSettings, AuditLog
        from core.cache import tenant_cache_key, cache_tenant_data
        from core.monitoring import health_check, monitor_performance
        print("✅ All models and utilities imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_model_definitions():
    """Test that models are properly defined"""
    print("🧪 Testing model definitions...")
    
    from tenants.models import Tenant, Domain
    from core.models import TenantSettings, AuditLog
    
    # Test Tenant model
    tenant_fields = [f.name for f in Tenant._meta.fields]
    required_tenant_fields = ['name', 'schema_name', 'max_users', 'features_enabled', 'billing_settings']
    
    for field in required_tenant_fields:
        if field not in tenant_fields:
            print(f"❌ Missing Tenant field: {field}")
            return False
    
    # Test Domain model
    domain_fields = [f.name for f in Domain._meta.fields]
    required_domain_fields = ['domain', 'tenant', 'is_primary']
    
    for field in required_domain_fields:
        if field not in domain_fields:
            print(f"❌ Missing Domain field: {field}")
            return False
    
    # Test TenantSettings model
    settings_fields = [f.name for f in TenantSettings._meta.fields]
    required_settings_fields = ['setting_key', 'setting_value', 'is_public']
    
    for field in required_settings_fields:
        if field not in settings_fields:
            print(f"❌ Missing TenantSettings field: {field}")
            return False
    
    print("✅ All model fields defined correctly")
    return True

def test_admin_registration():
    """Test that models are registered with admin"""
    print("🧪 Testing admin registration...")
    
    from django.contrib import admin
    from tenants.models import Tenant, Domain
    
    if Tenant not in admin.site._registry:
        print("❌ Tenant model not registered with admin")
        return False
    
    if Domain not in admin.site._registry:
        print("❌ Domain model not registered with admin")
        return False
    
    print("✅ All models registered with admin")
    return True

def test_cache_utilities():
    """Test cache utility functions"""
    print("🧪 Testing cache utilities...")
    
    from core.cache import tenant_cache_key, cache_tenant_data
    
    # Test tenant cache key generation
    key1 = tenant_cache_key("test_key", "tenant1")
    key2 = tenant_cache_key("test_key", "tenant2")
    
    if not key1.startswith("tenant1:"):
        print(f"❌ Tenant cache key incorrect: {key1}")
        return False
    
    if not key2.startswith("tenant2:"):
        print(f"❌ Tenant cache key incorrect: {key2}")
        return False
    
    if key1 == key2:
        print("❌ Tenant cache keys not isolated")
        return False
    
    # Test cache decorator exists
    if not callable(cache_tenant_data):
        print("❌ Cache decorator not callable")
        return False
    
    print("✅ Cache utilities working correctly")
    return True

def test_monitoring_utilities():
    """Test monitoring utility functions"""
    print("🧪 Testing monitoring utilities...")
    
    from core.monitoring import health_check, monitor_performance, get_database_stats
    
    # Test functions are callable
    if not callable(health_check):
        print("❌ health_check not callable")
        return False
    
    if not callable(monitor_performance):
        print("❌ monitor_performance not callable")
        return False
    
    if not callable(get_database_stats):
        print("❌ get_database_stats not callable")
        return False
    
    # Test monitor_performance decorator
    @monitor_performance("test_operation")
    def test_func():
        return "test_result"
    
    try:
        result = test_func()
        if result != "test_result":
            print("❌ Monitoring decorator changed function result")
            return False
    except Exception as e:
        print(f"❌ Monitoring decorator error: {e}")
        return False
    
    print("✅ Monitoring utilities working correctly")
    return True

def test_settings_configuration():
    """Test Django settings are properly configured"""
    print("🧪 Testing settings configuration...")
    
    from django.conf import settings
    
    # Test multi-tenant settings
    if settings.TENANT_MODEL != "tenants.Tenant":
        print(f"❌ TENANT_MODEL incorrect: {settings.TENANT_MODEL}")
        return False
    
    if settings.TENANT_DOMAIN_MODEL != "tenants.Domain":
        print(f"❌ TENANT_DOMAIN_MODEL incorrect: {settings.TENANT_DOMAIN_MODEL}")
        return False
    
    # Test database routing
    if 'django_tenants.routers.TenantSyncRouter' not in settings.DATABASE_ROUTERS:
        print("❌ Database router not configured")
        return False
    
    # Test middleware
    required_middleware = [
        'django_tenants.middleware.main.TenantMainMiddleware',
        'core.monitoring.PerformanceMiddleware'
    ]
    
    for middleware in required_middleware:
        if middleware not in settings.MIDDLEWARE:
            print(f"❌ Missing middleware: {middleware}")
            return False
    
    # Test security settings
    if not settings.SECURE_BROWSER_XSS_FILTER:
        print("❌ SECURE_BROWSER_XSS_FILTER not enabled")
        return False
    
    if not settings.SESSION_COOKIE_HTTPONLY:
        print("❌ SESSION_COOKIE_HTTPONLY not enabled")
        return False
    
    print("✅ Settings configured correctly")
    return True

def test_url_configuration():
    """Test URL configuration"""
    print("🧪 Testing URL configuration...")
    
    from django.conf import settings
    
    # Test URL configurations are set
    if not hasattr(settings, 'ROOT_URLCONF'):
        print("❌ ROOT_URLCONF not set")
        return False
    
    if not hasattr(settings, 'PUBLIC_SCHEMA_URLCONF'):
        print("❌ PUBLIC_SCHEMA_URLCONF not set")
        return False
    
    if settings.ROOT_URLCONF != 'oneo_crm.urls_tenants':
        print(f"❌ ROOT_URLCONF incorrect: {settings.ROOT_URLCONF}")
        return False
    
    if settings.PUBLIC_SCHEMA_URLCONF != 'oneo_crm.urls_public':
        print(f"❌ PUBLIC_SCHEMA_URLCONF incorrect: {settings.PUBLIC_SCHEMA_URLCONF}")
        return False
    
    # Test URL files exist
    import os
    base_dir = settings.BASE_DIR
    
    urls_tenant_path = os.path.join(base_dir, 'oneo_crm', 'urls_tenants.py')
    urls_public_path = os.path.join(base_dir, 'oneo_crm', 'urls_public.py')
    
    if not os.path.exists(urls_tenant_path):
        print(f"❌ Tenant URLs file missing: {urls_tenant_path}")
        return False
    
    if not os.path.exists(urls_public_path):
        print(f"❌ Public URLs file missing: {urls_public_path}")
        return False
    
    print("✅ URL configuration correct")
    return True

def test_file_structure():
    """Test that all required files exist"""
    print("🧪 Testing file structure...")
    
    from django.conf import settings
    base_dir = settings.BASE_DIR
    
    required_files = [
        'requirements.txt',
        'Dockerfile',
        'docker-compose.yml',
        '.env.example',
        '.gitignore',
        'setup.sh',
        'docs/api/README.md',
        'docs/ARCHITECTURE.md',
        'docs/DEPLOYMENT.md',
        'docs/TROUBLESHOOTING.md',
        'docs/SECURITY.md',
    ]
    
    for file_path in required_files:
        full_path = os.path.join(base_dir, file_path)
        if not os.path.exists(full_path):
            print(f"❌ Missing file: {file_path}")
            return False
    
    print("✅ All required files exist")
    return True

def run_all_tests():
    """Run all tests and return summary"""
    print("🚀 Starting Phase 1 Basic Functionality Tests\n")
    
    tests = [
        ("Imports", test_imports),
        ("Model Definitions", test_model_definitions),
        ("Admin Registration", test_admin_registration),
        ("Cache Utilities", test_cache_utilities),
        ("Monitoring Utilities", test_monitoring_utilities),
        ("Settings Configuration", test_settings_configuration),
        ("URL Configuration", test_url_configuration),
        ("File Structure", test_file_structure),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
        print()  # Add blank line between tests
    
    # Summary
    print("=" * 50)
    print("PHASE 1 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL PHASE 1 BASIC TESTS PASSED!")
        print("✅ Phase 1 foundation is working correctly (without database/Redis)")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        print("❌ Phase 1 foundation has issues that need to be fixed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)