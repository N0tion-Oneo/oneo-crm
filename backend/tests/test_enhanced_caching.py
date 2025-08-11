#!/usr/bin/env python
"""
Enhanced Caching Performance Test

This script tests the new layered caching system for permission management
and measures performance improvements.
"""
import os
import sys
import time
import django
from statistics import mean, median

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oneo_crm.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.cache import cache
from authentication.models import UserType
from authentication.cache_manager import PermissionCacheManager
from authentication.permissions_registry import (
    get_complete_permission_schema,
    get_permission_matrix_configuration
)
from authentication.permission_matrix import PermissionMatrixManager
from django_tenants.utils import get_tenant_model
from django.db import connection

User = get_user_model()

def clear_all_cache():
    """Clear all cache to start fresh"""
    cache.clear()
    print("🧹 Cleared all cache")

def test_cache_performance():
    """Test caching performance improvements"""
    
    print("🚀 ENHANCED CACHING PERFORMANCE TEST")
    print("=" * 60)
    
    # Get current tenant
    print(f"\n📍 Current Tenant: {connection.schema_name}")
    
    try:
        Tenant = get_tenant_model()
        tenant = Tenant.objects.get(schema_name=connection.schema_name)
        print(f"   Tenant Name: {tenant.name}")
    except Exception as e:
        print(f"   Error getting tenant: {e}")
        return
    
    # Initialize cache manager
    cache_manager = PermissionCacheManager(tenant.schema_name)
    
    # Test 1: Permission Schema Performance
    print(f"\n📋 TEST 1: PERMISSION SCHEMA PERFORMANCE")
    print("-" * 50)
    
    # Clear cache first
    clear_all_cache()
    
    # Test cold cache (first call)
    start_time = time.time()
    schema1, metrics1 = cache_manager.get_permission_schema(
        lambda: get_complete_permission_schema(tenant)
    )
    cold_time = time.time() - start_time
    
    print(f"   Cold cache: {cold_time * 1000:.2f}ms (cache_hit: {metrics1['cache_hit']})")
    print(f"   Data size: {metrics1['data_size_bytes']} bytes")
    print(f"   Categories: {len(schema1)}")
    
    # Test warm cache (second call)
    start_time = time.time()
    schema2, metrics2 = cache_manager.get_permission_schema(
        lambda: get_complete_permission_schema(tenant)
    )
    warm_time = time.time() - start_time
    
    print(f"   Warm cache: {warm_time * 1000:.2f}ms (cache_hit: {metrics2['cache_hit']})")
    print(f"   Speed improvement: {((cold_time - warm_time) / cold_time) * 100:.1f}%")
    
    # Test 2: Frontend Matrix Configuration Performance
    print(f"\n🎛️  TEST 2: FRONTEND MATRIX CONFIGURATION")
    print("-" * 50)
    
    matrix_manager = PermissionMatrixManager(tenant)
    
    # Clear cache
    cache_manager.invalidate_all_permissions()
    
    # Test cold cache
    start_time = time.time()
    config1 = matrix_manager.get_frontend_matrix_config()
    cold_matrix_time = time.time() - start_time
    
    print(f"   Cold cache: {cold_matrix_time * 1000:.2f}ms")
    print(f"   Cache info: {config1.get('cache_info', {})}")
    print(f"   Categories: {len(config1.get('categories', {}))}")
    print(f"   UI helpers: {len(config1.get('frontend_helpers', {}))}")
    
    # Test warm cache
    start_time = time.time()
    config2 = matrix_manager.get_frontend_matrix_config()
    warm_matrix_time = time.time() - start_time
    
    print(f"   Warm cache: {warm_matrix_time * 1000:.2f}ms")
    print(f"   Cache info: {config2.get('cache_info', {})}")
    print(f"   Speed improvement: {((cold_matrix_time - warm_matrix_time) / cold_matrix_time) * 100:.1f}%")
    
    # Test 3: User Permission Performance
    print(f"\n👥 TEST 3: USER PERMISSION PERFORMANCE")
    print("-" * 50)
    
    users = User.objects.all()[:3]  # Test with first 3 users
    
    if users:
        user_times_cold = []
        user_times_warm = []
        
        for user in users:
            # Clear user cache
            cache_manager.invalidate_user_permissions(user.id)
            
            # Cold cache
            start_time = time.time()
            perms1, metrics = cache_manager.get_user_permissions(
                user.id,
                lambda: {'test': 'permissions'}  # Simplified for testing
            )
            cold_user_time = time.time() - start_time
            user_times_cold.append(cold_user_time)
            
            # Warm cache
            start_time = time.time()
            perms2, metrics = cache_manager.get_user_permissions(
                user.id,
                lambda: {'test': 'permissions'}
            )
            warm_user_time = time.time() - start_time
            user_times_warm.append(warm_user_time)
            
            print(f"   User {user.id}: Cold {cold_user_time * 1000:.2f}ms, Warm {warm_user_time * 1000:.2f}ms")
        
        avg_cold = mean(user_times_cold)
        avg_warm = mean(user_times_warm)
        print(f"   Average cold: {avg_cold * 1000:.2f}ms")
        print(f"   Average warm: {avg_warm * 1000:.2f}ms")
        print(f"   Average improvement: {((avg_cold - avg_warm) / avg_cold) * 100:.1f}%")
    
    # Test 4: Cache Statistics
    print(f"\n📊 TEST 4: CACHE STATISTICS")
    print("-" * 50)
    
    stats = cache_manager.get_cache_statistics()
    
    if 'error' not in stats:
        print(f"   Total cache keys: {stats.get('total_keys', 0)}")
        print(f"   Cache hit rate: {stats.get('cache_hit_rate', 0)}%")
        print(f"   Average response time: {stats.get('average_response_time_ms', 0):.2f}ms")
        print(f"   Total requests: {stats.get('total_requests', 0)}")
        
        if stats.get('by_prefix'):
            print(f"   Performance by prefix:")
            for prefix, prefix_stats in stats['by_prefix'].items():
                print(f"     {prefix}: {prefix_stats['cache_hit_rate']}% hit rate, {prefix_stats['avg_response_time_ms']:.2f}ms avg")
    else:
        print(f"   Stats not available: {stats['error']}")
    
    # Test 5: Cache Warming Performance
    print(f"\n🔥 TEST 5: CACHE WARMING PERFORMANCE")
    print("-" * 50)
    
    # Clear cache
    cache_manager.invalidate_all_permissions()
    
    # Test cache warming
    compute_functions = {
        'permission_schema': lambda: get_complete_permission_schema(tenant),
        'matrix_config': lambda: get_permission_matrix_configuration(tenant),
        'frontend_config': lambda: PermissionMatrixManager(tenant).get_frontend_matrix_config()
    }
    
    start_time = time.time()
    warm_results = cache_manager.warm_cache(compute_functions)
    warm_total_time = time.time() - start_time
    
    print(f"   Total warming time: {warm_total_time * 1000:.2f}ms")
    print(f"   Warm results:")
    for cache_type, result in warm_results.items():
        if result.get('success'):
            print(f"     {cache_type}: ✅ {result['elapsed_time_ms']:.2f}ms (hit: {result['cache_hit']})")
        else:
            print(f"     {cache_type}: ❌ {result.get('error', 'Failed')}")
    
    # Test 6: Invalidation Performance
    print(f"\n🗑️  TEST 6: CACHE INVALIDATION")
    print("-" * 50)
    
    # Test selective invalidation
    start_time = time.time()
    cache_manager.invalidate_permission_schema()
    schema_invalidation_time = time.time() - start_time
    
    start_time = time.time()
    cache_manager.invalidate_pipeline_access()
    pipeline_invalidation_time = time.time() - start_time
    
    start_time = time.time()
    cache_manager.invalidate_all_permissions()
    full_invalidation_time = time.time() - start_time
    
    print(f"   Schema invalidation: {schema_invalidation_time * 1000:.2f}ms")
    print(f"   Pipeline invalidation: {pipeline_invalidation_time * 1000:.2f}ms")
    print(f"   Full invalidation: {full_invalidation_time * 1000:.2f}ms")
    
    # Summary
    print(f"\n🎯 PERFORMANCE SUMMARY")
    print("-" * 50)
    print(f"   Permission Schema Speed-up: {((cold_time - warm_time) / cold_time) * 100:.1f}%")
    print(f"   Frontend Matrix Speed-up: {((cold_matrix_time - warm_matrix_time) / cold_matrix_time) * 100:.1f}%")
    if users:
        print(f"   User Permissions Speed-up: {((avg_cold - avg_warm) / avg_cold) * 100:.1f}%")
    print(f"   Cache warming efficiency: {len([r for r in warm_results.values() if r.get('success')])}/{len(warm_results)} operations successful")
    
    # Final recommendation
    overall_improvement = mean([
        ((cold_time - warm_time) / cold_time) * 100,
        ((cold_matrix_time - warm_matrix_time) / cold_matrix_time) * 100
    ])
    
    print(f"\n💡 RECOMMENDATION")
    print("-" * 50)
    if overall_improvement > 70:
        print("   ✅ Excellent caching performance! System is production-ready.")
    elif overall_improvement > 50:
        print("   ⚡ Good caching performance. Consider additional optimizations.")
    elif overall_improvement > 30:
        print("   ⚠️  Moderate improvements. Review cache TTL settings.")
    else:
        print("   ⛔ Poor caching performance. Check Redis configuration.")
    
    print(f"   Overall cache performance improvement: {overall_improvement:.1f}%")
    print(f"   API endpoints available:")
    print(f"     - GET  /api/v1/auth/cache_statistics/")
    print(f"     - POST /api/v1/auth/warm_cache/")
    print(f"     - POST /api/v1/auth/clear_cache/")


if __name__ == "__main__":
    test_cache_performance()