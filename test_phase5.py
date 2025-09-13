#!/usr/bin/env python3
"""
Phase 5 Test Suite for Product Adder
Tests optimization, monitoring, and performance features
"""

import unittest
import time
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Import the modules to test
from cache_manager import cache_manager, get_cache_stats, clear_cache
from performance_monitor import performance_monitor, get_performance_summary, get_performance_health
from pagination import paginate_data, Paginator, validate_pagination_params
from database import get_database_stats, optimize_database

class TestCacheManager(unittest.TestCase):
    """Test cache manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        clear_cache()
    
    def test_cache_basic_operations(self):
        """Test basic cache operations"""
        # Test set and get
        cache_manager.set('test_key', 'test_value', ttl=60)
        self.assertEqual(cache_manager.get('test_key'), 'test_value')
        
        # Test delete
        self.assertTrue(cache_manager.delete('test_key'))
        self.assertIsNone(cache_manager.get('test_key'))
        
        # Test non-existent key
        self.assertFalse(cache_manager.delete('non_existent'))
    
    def test_cache_ttl(self):
        """Test cache TTL functionality"""
        # Set with short TTL
        cache_manager.set('ttl_key', 'ttl_value', ttl=1)
        self.assertEqual(cache_manager.get('ttl_key'), 'ttl_value')
        
        # Wait for expiration
        time.sleep(1.1)
        self.assertIsNone(cache_manager.get('ttl_key'))
    
    def test_cache_stats(self):
        """Test cache statistics"""
        # Clear cache first
        clear_cache()
        
        # Perform operations
        cache_manager.set('key1', 'value1')
        cache_manager.set('key2', 'value2')
        cache_manager.get('key1')  # Hit
        cache_manager.get('key3')  # Miss
        cache_manager.delete('key1')
        
        stats = get_cache_stats()
        self.assertEqual(stats['hits'], 1)
        self.assertEqual(stats['misses'], 1)
        self.assertEqual(stats['sets'], 2)
        self.assertEqual(stats['deletes'], 1)
        self.assertEqual(stats['size'], 1)  # Only key2 remains
    
    def test_cache_cleanup(self):
        """Test cache cleanup of expired entries"""
        # Set entries with different TTLs
        cache_manager.set('short_ttl', 'value1', ttl=1)
        cache_manager.set('long_ttl', 'value2', ttl=300)
        
        # Wait for short TTL to expire
        time.sleep(1.1)
        
        # Cleanup should remove expired entries
        cleaned_count = cache_manager.cleanup_expired()
        self.assertEqual(cleaned_count, 1)
        self.assertIsNone(cache_manager.get('short_ttl'))
        self.assertEqual(cache_manager.get('long_ttl'), 'value2')

class TestPerformanceMonitor(unittest.TestCase):
    """Test performance monitoring functionality"""
    
    def setUp(self):
        """Set up test environment"""
        performance_monitor.reset_metrics()
    
    def test_metric_recording(self):
        """Test metric recording"""
        from performance_monitor import record_metric, record_api_call, record_error
        
        # Test metric recording
        record_metric('test_metric', 42.5, {'tag': 'value'})
        record_metric('test_counter', 1)
        
        # Test API call recording
        record_api_call('/test/endpoint', 'GET', 0.5, 200)
        record_api_call('/test/endpoint', 'POST', 1.2, 500, 'Server error')
        
        # Test error recording
        record_error('test_error', 'Something went wrong', {'context': 'test'})
        
        # Get summary
        summary = get_performance_summary()
        self.assertGreater(summary['total_metrics'], 0)
        self.assertGreater(summary['total_api_calls'], 0)
        self.assertGreater(summary['total_errors'], 0)
    
    def test_performance_health(self):
        """Test performance health calculation"""
        from performance_monitor import record_api_call, record_error
        
        # Record some API calls with errors
        record_api_call('/test', 'GET', 0.1, 200)
        record_api_call('/test', 'GET', 0.1, 200)
        record_api_call('/test', 'GET', 0.1, 500, 'Error')
        
        # Record some errors
        record_error('test_error', 'Test error message')
        
        health = get_performance_health()
        self.assertIn('overall_health', health)
        self.assertIn('health_scores', health)
        self.assertIn('status', health)
        self.assertIn(health['status'], ['healthy', 'degraded', 'unhealthy'])
    
    def test_recent_metrics(self):
        """Test recent metrics retrieval"""
        from performance_monitor import record_metric, record_api_call
        
        # Record some metrics
        record_metric('recent_test', 1.0)
        record_api_call('/recent', 'GET', 0.5, 200)
        
        # Get recent metrics
        recent_metrics = performance_monitor.get_recent_metrics(minutes=5)
        recent_calls = performance_monitor.get_recent_api_calls(minutes=5)
        
        self.assertGreater(len(recent_metrics), 0)
        self.assertGreater(len(recent_calls), 0)

class TestPagination(unittest.TestCase):
    """Test pagination functionality"""
    
    def test_paginate_data(self):
        """Test data pagination"""
        # Create test data
        data = list(range(100))  # 0 to 99
        
        # Test first page
        result = paginate_data(data, page=1, per_page=20)
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['per_page'], 20)
        self.assertEqual(result['total'], 100)
        self.assertEqual(result['total_pages'], 5)
        self.assertTrue(result['has_next'])
        self.assertFalse(result['has_prev'])
        self.assertEqual(len(result['data']), 20)
        self.assertEqual(result['data'][0], 0)
        self.assertEqual(result['data'][-1], 19)
        
        # Test middle page
        result = paginate_data(data, page=3, per_page=20)
        self.assertEqual(result['page'], 3)
        self.assertTrue(result['has_next'])
        self.assertTrue(result['has_prev'])
        self.assertEqual(result['data'][0], 40)
        self.assertEqual(result['data'][-1], 59)
        
        # Test last page
        result = paginate_data(data, page=5, per_page=20)
        self.assertEqual(result['page'], 5)
        self.assertFalse(result['has_next'])
        self.assertTrue(result['has_prev'])
        self.assertEqual(len(result['data']), 20)
        self.assertEqual(result['data'][0], 80)
        self.assertEqual(result['data'][-1], 99)
    
    def test_paginator_class(self):
        """Test Paginator class"""
        data = list(range(50))
        paginator = Paginator(data, page=2, per_page=10)
        
        # Test pagination info
        info = paginator.get_pagination_info()
        self.assertEqual(info.page, 2)
        self.assertEqual(info.per_page, 10)
        self.assertEqual(info.total, 50)
        self.assertEqual(info.total_pages, 5)
        self.assertTrue(info.has_next)
        self.assertTrue(info.has_prev)
        self.assertEqual(info.next_page, 3)
        self.assertEqual(info.prev_page, 1)
        
        # Test page data
        page_data = paginator.get_page_data()
        self.assertEqual(len(page_data), 10)
        self.assertEqual(page_data[0], 10)
        self.assertEqual(page_data[-1], 19)
    
    def test_validate_pagination_params(self):
        """Test pagination parameter validation"""
        # Test valid parameters
        page, per_page = validate_pagination_params(1, 20, max_per_page=100)
        self.assertEqual(page, 1)
        self.assertEqual(per_page, 20)
        
        # Test invalid page
        page, per_page = validate_pagination_params(0, 20, max_per_page=100)
        self.assertEqual(page, 1)  # Should be corrected to 1
        
        # Test per_page exceeding max
        page, per_page = validate_pagination_params(1, 150, max_per_page=100)
        self.assertEqual(per_page, 100)  # Should be limited to max
        
        # Test negative per_page
        page, per_page = validate_pagination_params(1, -5, max_per_page=100)
        self.assertEqual(per_page, 1)  # Should be corrected to 1

class TestDatabaseOptimization(unittest.TestCase):
    """Test database optimization features"""
    
    def test_database_stats(self):
        """Test database statistics"""
        stats = get_database_stats()
        
        # Check that stats contain expected keys
        expected_keys = ['jds_products', 'shopify_products', 'total_products', 
                        'database_size_bytes', 'database_size_mb', 'cache_stats', 'timestamp']
        for key in expected_keys:
            self.assertIn(key, stats)
        
        # Check that counts are non-negative
        self.assertGreaterEqual(stats['jds_products'], 0)
        self.assertGreaterEqual(stats['shopify_products'], 0)
        self.assertGreaterEqual(stats['total_products'], 0)
        self.assertGreaterEqual(stats['database_size_bytes'], 0)
    
    def test_optimize_database(self):
        """Test database optimization"""
        result = optimize_database()
        
        # Check that optimization completed
        self.assertIn('analyzed', result)
        self.assertTrue(result['analyzed'])
        self.assertIn('timestamp', result)

class TestIntegration(unittest.TestCase):
    """Test integration between Phase 5 components"""
    
    def test_cache_with_performance_monitoring(self):
        """Test cache operations with performance monitoring"""
        from performance_monitor import record_metric
        
        # Clear cache
        clear_cache()
        
        # Record cache operations
        cache_manager.set('integration_test', 'value')
        record_metric('cache_operation', 1)
        
        # Get value
        value = cache_manager.get('integration_test')
        self.assertEqual(value, 'value')
        
        # Check that metrics were recorded
        summary = get_performance_summary()
        self.assertGreater(summary['total_metrics'], 0)
    
    def test_pagination_with_performance_monitoring(self):
        """Test pagination with performance monitoring"""
        from performance_monitor import record_metric
        
        # Create test data
        data = list(range(1000))
        
        # Paginate with performance monitoring
        start_time = time.time()
        result = paginate_data(data, page=1, per_page=50)
        duration = time.time() - start_time
        
        # Record performance metric
        record_metric('pagination_duration', duration)
        
        # Verify pagination worked
        self.assertEqual(len(result['data']), 50)
        self.assertEqual(result['total'], 1000)
        
        # Verify performance metric was recorded
        summary = get_performance_summary()
        self.assertGreater(summary['total_metrics'], 0)

def run_performance_benchmark():
    """Run performance benchmark tests"""
    print("Running Performance Benchmarks...")
    print("=" * 50)
    
    # Cache performance test
    print("Testing Cache Performance...")
    clear_cache()
    
    start_time = time.time()
    for i in range(1000):
        cache_manager.set(f'key_{i}', f'value_{i}')
    set_time = time.time() - start_time
    
    start_time = time.time()
    for i in range(1000):
        cache_manager.get(f'key_{i}')
    get_time = time.time() - start_time
    
    print(f"Cache Set Operations: {set_time:.4f}s for 1000 operations")
    print(f"Cache Get Operations: {get_time:.4f}s for 1000 operations")
    print(f"Cache Hit Rate: {get_cache_stats()['hit_rate']}%")
    
    # Pagination performance test
    print("\nTesting Pagination Performance...")
    large_data = list(range(10000))
    
    start_time = time.time()
    for page in range(1, 11):  # Test 10 pages
        result = paginate_data(large_data, page=page, per_page=100)
    pagination_time = time.time() - start_time
    
    print(f"Pagination: {pagination_time:.4f}s for 10 pages of 100 items each")
    
    # Performance monitoring test
    print("\nTesting Performance Monitoring...")
    from performance_monitor import record_metric, record_api_call
    
    start_time = time.time()
    for i in range(1000):
        record_metric(f'metric_{i}', i * 1.5)
        record_api_call(f'/test/{i}', 'GET', 0.1, 200)
    monitoring_time = time.time() - start_time
    
    print(f"Performance Monitoring: {monitoring_time:.4f}s for 2000 operations")
    
    # Get final performance summary
    summary = get_performance_summary()
    health = get_performance_health()
    
    print(f"\nFinal Performance Summary:")
    print(f"Total Metrics: {summary['total_metrics']}")
    print(f"Total API Calls: {summary['total_api_calls']}")
    print(f"Overall Health: {health['overall_health']}%")
    print(f"Status: {health['status']}")

if __name__ == '__main__':
    print("Phase 5 Test Suite for Product Adder")
    print("=" * 50)
    
    # Run unit tests
    print("Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "=" * 50)
    
    # Run performance benchmarks
    run_performance_benchmark()
    
    print("\n" + "=" * 50)
    print("Phase 5 Testing Complete!")
