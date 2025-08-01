from django.test import TestCase
from django.core.cache import cache
from core.cache import tenant_cache_key, cache_tenant_data
from core.models import TenantSettings


class CacheIsolationTest(TestCase):
    def test_tenant_cache_keys(self):
        """Test tenant-specific cache key generation"""
        key1 = tenant_cache_key("test_key", "tenant1")
        key2 = tenant_cache_key("test_key", "tenant2")
        
        self.assertNotEqual(key1, key2)
        self.assertTrue(key1.startswith("tenant1:"))
        self.assertTrue(key2.startswith("tenant2:"))
        
        # Test cache isolation
        cache.set(key1, "value1")
        cache.set(key2, "value2")
        
        self.assertEqual(cache.get(key1), "value1")
        self.assertEqual(cache.get(key2), "value2")

    def test_cache_decorator(self):
        """Test the cache_tenant_data decorator"""
        call_count = 0
        
        @cache_tenant_data(timeout=60)
        def test_function(arg1, arg2=None):
            nonlocal call_count
            call_count += 1
            return f"result-{arg1}-{arg2}"
        
        # First call should execute the function
        result1 = test_function("test", arg2="value")
        self.assertEqual(call_count, 1)
        self.assertEqual(result1, "result-test-value")
        
        # Second call should use cache
        result2 = test_function("test", arg2="value")
        self.assertEqual(call_count, 1)  # Should not increment
        self.assertEqual(result2, "result-test-value")


class TenantSettingsTest(TestCase):
    def test_tenant_settings_creation(self):
        """Test creating tenant settings"""
        setting = TenantSettings.objects.create(
            setting_key="test_setting",
            setting_value={"option1": "value1", "option2": True},
            is_public=False
        )
        
        self.assertEqual(setting.setting_key, "test_setting")
        self.assertEqual(setting.setting_value["option1"], "value1")
        self.assertFalse(setting.is_public)
