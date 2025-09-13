#!/usr/bin/env python3
"""
Quick Phase 5 Test Script
Tests the core Phase 5 features without running the full test suite
"""

import sys
import time
from datetime import datetime

def test_cache_manager():
    """Test cache manager functionality"""
    print("Testing Cache Manager...")
    
    try:
        from cache_manager import cache_manager, get_cache_stats, clear_cache
        
        # Clear cache
        clear_cache()
        
        # Test basic operations
        cache_manager.set('test_key', 'test_value', ttl=60)
        value = cache_manager.get('test_key')
        assert value == 'test_value', "Cache get/set failed"
        
        # Test statistics
        stats = get_cache_stats()
        assert stats['hits'] >= 1, "Cache hit not recorded"
        assert stats['sets'] >= 1, "Cache set not recorded"
        
        print("✅ Cache Manager: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Cache Manager: FAILED - {e}")
        return False

def test_performance_monitor():
    """Test performance monitor functionality"""
    print("Testing Performance Monitor...")
    
    try:
        from performance_monitor import record_metric, record_api_call, get_performance_summary, get_performance_health
        
        # Record some metrics
        record_metric('test_metric', 42.5)
        record_api_call('/test', 'GET', 0.5, 200)
        
        # Get summary
        summary = get_performance_summary()
        assert summary['total_metrics'] > 0, "Metrics not recorded"
        assert summary['total_api_calls'] > 0, "API calls not recorded"
        
        # Get health
        health = get_performance_health()
        assert 'overall_health' in health, "Health data missing"
        assert 'status' in health, "Status missing"
        
        print("✅ Performance Monitor: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Performance Monitor: FAILED - {e}")
        return False

def test_pagination():
    """Test pagination functionality"""
    print("Testing Pagination...")
    
    try:
        from pagination import paginate_data, validate_pagination_params
        
        # Test pagination
        data = list(range(100))
        result = paginate_data(data, page=1, per_page=20)
        
        assert result['page'] == 1, "Page number incorrect"
        assert result['per_page'] == 20, "Per page incorrect"
        assert result['total'] == 100, "Total count incorrect"
        assert len(result['data']) == 20, "Data length incorrect"
        assert result['has_next'] == True, "Has next incorrect"
        assert result['has_prev'] == False, "Has prev incorrect"
        
        # Test parameter validation
        page, per_page = validate_pagination_params(1, 20, max_per_page=100)
        assert page == 1, "Page validation failed"
        assert per_page == 20, "Per page validation failed"
        
        print("✅ Pagination: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Pagination: FAILED - {e}")
        return False

def test_database_optimization():
    """Test database optimization features"""
    print("Testing Database Optimization...")
    
    try:
        from database import get_database_stats, optimize_database
        
        # Test database stats
        stats = get_database_stats()
        assert 'jds_products' in stats, "JDS products count missing"
        assert 'shopify_products' in stats, "Shopify products count missing"
        assert 'total_products' in stats, "Total products count missing"
        assert 'database_size_bytes' in stats, "Database size missing"
        
        # Test database optimization
        result = optimize_database()
        assert 'analyzed' in result, "Optimization result missing"
        
        print("✅ Database Optimization: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Database Optimization: FAILED - {e}")
        return False

def test_integration():
    """Test integration between components"""
    print("Testing Integration...")
    
    try:
        from cache_manager import cache_manager, get_cache_stats
        from performance_monitor import record_metric
        
        # Test cache with performance monitoring
        cache_manager.set('integration_test', 'value')
        record_metric('cache_operation', 1)
        
        value = cache_manager.get('integration_test')
        assert value == 'value', "Cache integration failed"
        
        # Test performance monitoring
        from performance_monitor import get_performance_summary
        summary = get_performance_summary()
        assert summary['total_metrics'] > 0, "Performance monitoring integration failed"
        
        print("✅ Integration: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Integration: FAILED - {e}")
        return False

def run_performance_benchmark():
    """Run a quick performance benchmark"""
    print("\nRunning Performance Benchmark...")
    
    try:
        from cache_manager import cache_manager, get_cache_stats, clear_cache
        from performance_monitor import record_metric, record_api_call
        from pagination import paginate_data
        
        # Clear cache
        clear_cache()
        
        # Cache performance test
        start_time = time.time()
        for i in range(100):
            cache_manager.set(f'key_{i}', f'value_{i}')
        cache_set_time = time.time() - start_time
        
        start_time = time.time()
        for i in range(100):
            cache_manager.get(f'key_{i}')
        cache_get_time = time.time() - start_time
        
        # Pagination performance test
        large_data = list(range(1000))
        start_time = time.time()
        for page in range(1, 6):  # Test 5 pages
            result = paginate_data(large_data, page=page, per_page=100)
        pagination_time = time.time() - start_time
        
        # Performance monitoring test
        start_time = time.time()
        for i in range(100):
            record_metric(f'metric_{i}', i * 1.5)
            record_api_call(f'/test/{i}', 'GET', 0.1, 200)
        monitoring_time = time.time() - start_time
        
        # Get final stats
        cache_stats = get_cache_stats()
        
        print(f"Cache Set (100 ops): {cache_set_time:.4f}s")
        print(f"Cache Get (100 ops): {cache_get_time:.4f}s")
        print(f"Cache Hit Rate: {cache_stats['hit_rate']}%")
        print(f"Pagination (5 pages): {pagination_time:.4f}s")
        print(f"Monitoring (200 ops): {monitoring_time:.4f}s")
        
        print("✅ Performance Benchmark: COMPLETED")
        return True
        
    except Exception as e:
        print(f"❌ Performance Benchmark: FAILED - {e}")
        return False

def main():
    """Run all Phase 5 tests"""
    print("Phase 5 Quick Test Suite")
    print("=" * 50)
    print(f"Started at: {datetime.now().isoformat()}")
    print()
    
    tests = [
        test_cache_manager,
        test_performance_monitor,
        test_pagination,
        test_database_optimization,
        test_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    # Run performance benchmark
    run_performance_benchmark()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    print(f"Completed at: {datetime.now().isoformat()}")
    
    if passed == total:
        print("🎉 All Phase 5 tests PASSED!")
        return 0
    else:
        print("❌ Some tests FAILED!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
