"""
Comprehensive performance tests for Oneo CRM
"""

import time
import threading
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.db import connection
from django.core.cache import cache
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import schema_context
from tenants.models import Tenant, Domain
from core.models import TenantSettings
from core.cache import tenant_cache_key, cache_tenant_data
from core.monitoring import monitor_performance, get_database_stats


class DatabasePerformanceTest(TestCase):
    """Test database performance and connection handling"""
    
    def test_tenant_creation_performance(self):
        """Test tenant creation performance benchmark"""
        start_time = time.time()
        
        tenants_created = []
        for i in range(10):
            tenant = Tenant.objects.create(
                name=f"Performance Test Tenant {i}",
                schema_name=f"perf_test_{i}"
            )
            tenants_created.append(tenant)
            
            # Also create domain
            Domain.objects.create(
                domain=f"perf{i}.localhost",
                tenant=tenant,
                is_primary=True
            )
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create 10 tenants in under 5 seconds
        self.assertLess(creation_time, 5.0, 
                       f"Tenant creation took {creation_time:.2f}s, expected < 5s")
        
        # Average time per tenant should be under 500ms
        avg_time = creation_time / 10
        self.assertLess(avg_time, 0.5,
                       f"Average tenant creation time {avg_time:.2f}s, expected < 0.5s")
        
        # Cleanup
        for tenant in tenants_created:
            tenant.delete()
    
    def test_database_connection_efficiency(self):
        """Test database connection pool efficiency"""
        initial_queries = len(connection.queries)
        
        # Perform multiple database operations
        for i in range(50):
            Tenant.objects.filter(name=f"test_tenant_{i}").exists()
        
        final_queries = len(connection.queries)
        queries_executed = final_queries - initial_queries
        
        # Should reuse connections efficiently
        self.assertEqual(queries_executed, 50, 
                        f"Expected 50 queries, got {queries_executed}")
    
    def test_jsonb_query_performance(self):
        """Test JSONB field query performance"""
        # Create tenant with JSONB data
        tenant = Tenant.objects.create(
            name="JSONB Performance Test",
            schema_name="jsonb_perf_test",
            features_enabled={
                "feature1": True,
                "feature2": False,
                "feature3": {"nested": "value"},
                "feature4": [1, 2, 3, 4, 5]
            }
        )
        
        start_time = time.time()
        
        # Perform JSONB queries
        for i in range(100):
            # Query by JSONB field
            Tenant.objects.filter(
                features_enabled__feature1=True
            ).exists()
            
            # Query nested JSONB
            Tenant.objects.filter(
                features_enabled__feature3__nested="value"
            ).exists()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # JSONB queries should be reasonably fast
        self.assertLess(query_time, 2.0,
                       f"JSONB queries took {query_time:.2f}s, expected < 2s")
        
        tenant.delete()


class CachePerformanceTest(TestCase):
    """Test cache performance and isolation"""
    
    def setUp(self):
        cache.clear()
    
    def test_cache_performance(self):
        """Test cache operation performance"""
        start_time = time.time()
        
        # Test cache set operations
        for i in range(1000):
            cache.set(f"test_key_{i}", f"test_value_{i}", 60)
        
        set_time = time.time() - start_time
        
        # Test cache get operations
        start_time = time.time()
        
        for i in range(1000):
            value = cache.get(f"test_key_{i}")
            self.assertEqual(value, f"test_value_{i}")
        
        get_time = time.time() - start_time
        
        # Cache operations should be very fast
        self.assertLess(set_time, 1.0, 
                       f"Cache set operations took {set_time:.2f}s, expected < 1s")
        self.assertLess(get_time, 0.5,
                       f"Cache get operations took {get_time:.2f}s, expected < 0.5s")
    
    def test_tenant_cache_isolation(self):
        """Test tenant cache key isolation performance"""
        start_time = time.time()
        
        # Test tenant cache operations
        for i in range(500):
            key1 = tenant_cache_key(f"test_{i}", "tenant1")
            key2 = tenant_cache_key(f"test_{i}", "tenant2")
            
            cache.set(key1, f"tenant1_value_{i}", 60)
            cache.set(key2, f"tenant2_value_{i}", 60)
        
        # Verify isolation
        for i in range(500):
            key1 = tenant_cache_key(f"test_{i}", "tenant1")
            key2 = tenant_cache_key(f"test_{i}", "tenant2")
            
            value1 = cache.get(key1)
            value2 = cache.get(key2)
            
            self.assertEqual(value1, f"tenant1_value_{i}")
            self.assertEqual(value2, f"tenant2_value_{i}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Tenant cache operations should be efficient
        self.assertLess(total_time, 2.0,
                       f"Tenant cache operations took {total_time:.2f}s, expected < 2s")
    
    def test_cache_decorator_performance(self):
        """Test cache decorator performance"""
        call_count = 0
        
        @cache_tenant_data(timeout=60)
        def expensive_operation(arg1, arg2):
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate expensive operation
            return f"result_{arg1}_{arg2}"
        
        start_time = time.time()
        
        # First calls should execute function
        for i in range(10):
            result = expensive_operation("test", i)
            self.assertEqual(result, f"result_test_{i}")
        
        # Second calls should use cache
        for i in range(10):
            result = expensive_operation("test", i)
            self.assertEqual(result, f"result_test_{i}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should only call function 10 times (not 20)
        self.assertEqual(call_count, 10)
        
        # Cached calls should be much faster than 0.2s (10 * 0.01 * 2)
        self.assertLess(total_time, 0.15,
                       f"Cache decorator test took {total_time:.2f}s, expected < 0.15s")


class ConcurrencyPerformanceTest(TransactionTestCase):
    """Test system performance under concurrent load"""
    
    def test_concurrent_tenant_operations(self):
        """Test concurrent tenant creation and operations"""
        results = []
        
        def create_tenant_worker(thread_id):
            start_time = time.time()
            try:
                tenant = Tenant.objects.create(
                    name=f"Concurrent Test Tenant {thread_id}",
                    schema_name=f"concurrent_test_{thread_id}"
                )
                
                # Perform some operations
                Domain.objects.create(
                    domain=f"concurrent{thread_id}.localhost",
                    tenant=tenant,
                    is_primary=True
                )
                
                # Test cache operations
                cache.set(f"concurrent_test_{thread_id}", "test_value", 60)
                value = cache.get(f"concurrent_test_{thread_id}")
                
                end_time = time.time()
                results.append({
                    'thread_id': thread_id,
                    'success': True,
                    'duration': end_time - start_time,
                    'tenant_id': tenant.id
                })
                
            except Exception as e:
                end_time = time.time()
                results.append({
                    'thread_id': thread_id,
                    'success': False,
                    'duration': end_time - start_time,
                    'error': str(e)
                })
        
        # Create 5 concurrent threads
        threads = []
        start_time = time.time()
        
        for i in range(5):
            thread = threading.Thread(target=create_tenant_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all operations succeeded
        successful_operations = [r for r in results if r['success']]
        self.assertEqual(len(successful_operations), 5,
                        f"Expected 5 successful operations, got {len(successful_operations)}")
        
        # Concurrent operations should complete reasonably quickly
        self.assertLess(total_time, 10.0,
                       f"Concurrent operations took {total_time:.2f}s, expected < 10s")
        
        # Average operation time should be reasonable
        avg_duration = sum(r['duration'] for r in successful_operations) / len(successful_operations)
        self.assertLess(avg_duration, 5.0,
                       f"Average operation duration {avg_duration:.2f}s, expected < 5s")


class MonitoringPerformanceTest(TestCase):
    """Test performance monitoring functionality"""
    
    def test_performance_monitoring_overhead(self):
        """Test that performance monitoring doesn't add significant overhead"""
        
        @monitor_performance("test_operation")
        def test_operation():
            time.sleep(0.01)  # Simulate work
            return "result"
        
        # Test without monitoring
        start_time = time.time()
        for i in range(100):
            time.sleep(0.01)
        unmonitored_time = time.time() - start_time
        
        # Test with monitoring
        start_time = time.time()
        for i in range(100):
            result = test_operation()
            self.assertEqual(result, "result")
        monitored_time = time.time() - start_time
        
        # Monitoring overhead should be minimal (< 10% increase)
        overhead = (monitored_time - unmonitored_time) / unmonitored_time
        self.assertLess(overhead, 0.1,
                       f"Monitoring overhead {overhead:.2%}, expected < 10%")
    
    def test_database_stats_performance(self):
        """Test database stats collection performance"""
        start_time = time.time()
        
        for i in range(50):
            stats = get_database_stats()
            self.assertIn('queries_count', stats)
            self.assertIn('total_time', stats)
            self.assertIn('tenant', stats)
        
        end_time = time.time()
        collection_time = end_time - start_time
        
        # Stats collection should be fast
        self.assertLess(collection_time, 1.0,
                       f"Database stats collection took {collection_time:.2f}s, expected < 1s")


class ScalabilityTest(TenantTestCase):
    """Test system scalability with multiple tenants"""
    
    def test_multi_tenant_performance(self):
        """Test performance with multiple active tenants"""
        tenants = []
        
        # Create multiple tenants
        for i in range(5):
            tenant = Tenant.objects.create(
                name=f"Scale Test Tenant {i}",
                schema_name=f"scale_test_{i}"
            )
            tenants.append(tenant)
        
        start_time = time.time()
        
        # Perform operations across all tenants
        for tenant in tenants:
            with schema_context(tenant.schema_name):
                # Create tenant settings
                for j in range(10):
                    TenantSettings.objects.create(
                        setting_key=f"setting_{j}",
                        setting_value={"value": f"test_value_{j}"},
                        is_public=False
                    )
                
                # Query tenant settings
                settings_count = TenantSettings.objects.count()
                self.assertEqual(settings_count, 10)
                
                # Test JSONB queries
                settings = TenantSettings.objects.filter(
                    setting_value__value__startswith="test_value"
                )
                self.assertEqual(settings.count(), 10)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Multi-tenant operations should complete efficiently
        self.assertLess(total_time, 5.0,
                       f"Multi-tenant operations took {total_time:.2f}s, expected < 5s")
        
        # Cleanup
        for tenant in tenants:
            tenant.delete()


class MemoryPerformanceTest(TestCase):
    """Test memory usage and efficiency"""
    
    def test_memory_usage_stability(self):
        """Test that memory usage remains stable under load"""
        try:
            import psutil
            import os
        except ImportError:
            self.skipTest("psutil not installed")
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive operations
        large_data = []
        for i in range(1000):
            # Create some data
            data = {
                'id': i,
                'name': f'Test Object {i}',
                'metadata': {'key': 'value', 'number': i}
            }
            large_data.append(data)
            
            # Cache operations
            cache.set(f"memory_test_{i}", data, 60)
            
            # Database operations
            Tenant.objects.filter(name=f"nonexistent_{i}").exists()
        
        # Clear data
        large_data.clear()
        cache.clear()
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Memory increase should be reasonable (< 50MB)
        self.assertLess(memory_increase, 50,
                       f"Memory increased by {memory_increase:.2f}MB, expected < 50MB")