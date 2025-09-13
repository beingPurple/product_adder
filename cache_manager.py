"""
Cache Manager for Product Adder
Implements in-memory caching for frequently accessed data
"""

import time
import threading
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'expired': 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            
            # Check if expired
            if time.time() > entry['expires_at']:
                del self.cache[key]
                self.stats['expired'] += 1
                self.stats['misses'] += 1
                return None
            
            self.stats['hits'] += 1
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        with self.lock:
            if ttl is None:
                ttl = self.default_ttl
            
            self.cache[key] = {
                'value': value,
                'expires_at': time.time() + ttl,
                'created_at': time.time()
            }
            self.stats['sets'] += 1
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.stats['deletes'] += 1
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.stats = {
                'hits': 0,
                'misses': 0,
                'sets': 0,
                'deletes': 0,
                'expired': 0
            }
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of cleaned entries"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.cache.items()
                if current_time > entry['expires_at']
            ]
            
            for key in expired_keys:
                del self.cache[key]
                self.stats['expired'] += 1
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': round(hit_rate, 2),
                'sets': self.stats['sets'],
                'deletes': self.stats['deletes'],
                'expired': self.stats['expired']
            }
    
    def get_info(self) -> Dict[str, Any]:
        """Get detailed cache information"""
        with self.lock:
            current_time = time.time()
            entries_info = []
            
            for key, entry in self.cache.items():
                entries_info.append({
                    'key': key,
                    'age': round(current_time - entry['created_at'], 2),
                    'ttl_remaining': round(entry['expires_at'] - current_time, 2),
                    'expired': current_time > entry['expires_at']
                })
            
            return {
                'stats': self.get_stats(),
                'entries': entries_info,
                'total_entries': len(self.cache)
            }

# Global cache instance
cache_manager = CacheManager()

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return cache_manager.get_stats()

def clear_cache() -> None:
    """Clear all cache entries"""
    cache_manager.clear()

def cache_key_for_products(prefix: str = "products") -> str:
    """Generate cache key for products"""
    return f"{prefix}:all"

def cache_key_for_unmatched_products() -> str:
    """Generate cache key for unmatched products"""
    return "products:unmatched"

def cache_key_for_matched_products() -> str:
    """Generate cache key for matched products"""
    return "products:matched"

def cache_key_for_sync_status() -> str:
    """Generate cache key for sync status"""
    return "sync:status"

def cache_key_for_comparison_stats() -> str:
    """Generate cache key for comparison stats"""
    return "comparison:stats"

def cache_key_for_connection_status() -> str:
    """Generate cache key for connection status"""
    return "connections:status"

def cache_key_for_pricing(sku: str) -> str:
    """Generate cache key for pricing data"""
    return f"pricing:{sku}"

def cache_key_for_product_details(sku: str) -> str:
    """Generate cache key for product details"""
    return f"product:{sku}"

# Cache decorator
def cached(ttl: int = 300, key_func: Optional[callable] = None):
    """Decorator to cache function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Simple key generation based on function name and arguments
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {cache_key}")
            return result
        
        return wrapper
    return decorator
