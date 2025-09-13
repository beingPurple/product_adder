"""
Simple database implementation using SQLite3 directly
This avoids SQLAlchemy compatibility issues with Python 3.13
"""

import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from cache_manager import cache_manager, cached, cache_key_for_unmatched_products, cache_key_for_matched_products, cache_key_for_comparison_stats
from performance_monitor import time_function, record_metric

logger = logging.getLogger(__name__)

class SimpleDB:
    def __init__(self, db_path=None):
        if db_path is None:
            # For Vercel serverless environment, use /tmp directory
            if os.environ.get('VERCEL'):
                self.db_path = "/tmp/product_adder.db"
            else:
                self.db_path = "product_adder.db"
        else:
            self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Connect to the database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def init_tables(self):
        """Initialize database tables"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Create JDS Products table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jds_products (
                    id INTEGER PRIMARY KEY,
                    sku TEXT UNIQUE NOT NULL,
                    name TEXT,
                    description TEXT,
                    case_quantity INTEGER,
                    less_than_case_price REAL,
                    one_case REAL,
                    five_cases REAL,
                    ten_cases REAL,
                    twenty_cases REAL,
                    forty_cases REAL,
                    image_url TEXT,
                    thumbnail_url TEXT,
                    quick_image_url TEXT,
                    available_quantity INTEGER,
                    local_quantity INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create Shopify Products table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shopify_products (
                    id INTEGER PRIMARY KEY,
                    sku TEXT UNIQUE NOT NULL,
                    product_id TEXT,
                    variant_id TEXT,
                    current_price REAL,
                    product_title TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jds_products_sku ON jds_products(sku)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shopify_products_sku ON shopify_products(sku)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_jds_products_updated ON jds_products(last_updated)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shopify_products_updated ON shopify_products(last_updated)')
            
            conn.commit()
            conn.close()
            print("Database tables created successfully")
            return True
            
        except Exception as e:
            print(f"Error creating database tables: {e}")
            return False

class JDSProduct:
    """JDS Product model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.sku = kwargs.get('sku', '')
        self.name = kwargs.get('name', '')
        self.description = kwargs.get('description', '')
        self.case_quantity = kwargs.get('case_quantity')
        self.less_than_case_price = kwargs.get('less_than_case_price')
        self.one_case = kwargs.get('one_case')
        self.five_cases = kwargs.get('five_cases')
        self.ten_cases = kwargs.get('ten_cases')
        self.twenty_cases = kwargs.get('twenty_cases')
        self.forty_cases = kwargs.get('forty_cases')
        self.image_url = kwargs.get('image_url', '')
        self.thumbnail_url = kwargs.get('thumbnail_url', '')
        self.quick_image_url = kwargs.get('quick_image_url', '')
        self.available_quantity = kwargs.get('available_quantity')
        self.local_quantity = kwargs.get('local_quantity')
        self.last_updated = kwargs.get('last_updated', datetime.utcnow())
    
    def save(self, db_or_conn):
        """Save product to database"""
        # Check if we received a connection or database object
        if hasattr(db_or_conn, 'connect'):
            # It's a database object, create connection
            conn = db_or_conn.connect()
            cursor = conn.cursor()
            should_close = True
        else:
            # It's a connection object
            conn = db_or_conn
            cursor = conn.cursor()
            should_close = False
        
        try:
            if self.id:
                # Update existing product
                cursor.execute('''
                    UPDATE jds_products SET
                        sku=?, name=?, description=?, case_quantity=?,
                        less_than_case_price=?, one_case=?, five_cases=?,
                        ten_cases=?, twenty_cases=?, forty_cases=?,
                        image_url=?, thumbnail_url=?, quick_image_url=?,
                        available_quantity=?, local_quantity=?, last_updated=?
                    WHERE id=?
                ''', (
                    self.sku, self.name, self.description, self.case_quantity,
                    self.less_than_case_price, self.one_case, self.five_cases,
                    self.ten_cases, self.twenty_cases, self.forty_cases,
                    self.image_url, self.thumbnail_url, self.quick_image_url,
                    self.available_quantity, self.local_quantity, self.last_updated,
                    self.id
                ))
            else:
                # Insert new product
                cursor.execute('''
                    INSERT INTO jds_products (
                        sku, name, description, case_quantity,
                        less_than_case_price, one_case, five_cases,
                        ten_cases, twenty_cases, forty_cases,
                        image_url, thumbnail_url, quick_image_url,
                        available_quantity, local_quantity, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.sku, self.name, self.description, self.case_quantity,
                    self.less_than_case_price, self.one_case, self.five_cases,
                    self.ten_cases, self.twenty_cases, self.forty_cases,
                    self.image_url, self.thumbnail_url, self.quick_image_url,
                    self.available_quantity, self.local_quantity, self.last_updated
                ))
                self.id = cursor.lastrowid
            
            if should_close:
                conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving JDS product: {e}")
            if should_close:
                conn.rollback()
            return False
        finally:
            if should_close:
                conn.close()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,
            'case_quantity': self.case_quantity,
            'less_than_case_price': self.less_than_case_price,
            'one_case': self.one_case,
            'five_cases': self.five_cases,
            'ten_cases': self.ten_cases,
            'twenty_cases': self.twenty_cases,
            'forty_cases': self.forty_cases,
            'image_url': self.image_url,
            'thumbnail_url': self.thumbnail_url,
            'quick_image_url': self.quick_image_url,
            'available_quantity': self.available_quantity,
            'local_quantity': self.local_quantity,
            'last_updated': self.last_updated.isoformat() if hasattr(self.last_updated, 'isoformat') else self.last_updated
        }

class ShopifyProduct:
    """Shopify Product model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.sku = kwargs.get('sku', '')
        self.product_id = kwargs.get('product_id', '')
        self.variant_id = kwargs.get('variant_id', '')
        self.current_price = kwargs.get('current_price', 0.0)
        self.product_title = kwargs.get('product_title', '')
        self.last_updated = kwargs.get('last_updated', datetime.utcnow())
    
    def save(self, db):
        """Save product to database"""
        conn = db.connect()
        cursor = conn.cursor()
        
        try:
            if self.id:
                # Update existing product
                cursor.execute('''
                    UPDATE shopify_products SET
                        sku=?, product_id=?, variant_id=?, current_price=?,
                        product_title=?, last_updated=?
                    WHERE id=?
                ''', (
                    self.sku, self.product_id, self.variant_id, self.current_price,
                    self.product_title, self.last_updated, self.id
                ))
            else:
                # Insert new product
                cursor.execute('''
                    INSERT INTO shopify_products (
                        sku, product_id, variant_id, current_price,
                        product_title, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    self.sku, self.product_id, self.variant_id, self.current_price,
                    self.product_title, self.last_updated
                ))
                self.id = cursor.lastrowid
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving Shopify product: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'sku': self.sku,
            'product_id': self.product_id,
            'variant_id': self.variant_id,
            'current_price': self.current_price,
            'product_title': self.product_title,
            'last_updated': self.last_updated.isoformat() if hasattr(self.last_updated, 'isoformat') else self.last_updated
        }

# Global database instance
db = SimpleDB()

def init_db():
    """Initialize database tables"""
    return db.init_tables()

def clean_sku_for_comparison(sku: str) -> str:
    """Clean SKU by removing hyphen and any letters preceding it for comparison"""
    if not sku:
        return sku
    
    if '-' in sku:
        parts = sku.split('-')
        return parts[-1]
    return sku

def get_unmatched_products():
    """Get JDS products that don't exist in Shopify (with SKU cleaning)"""
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        # Get all JDS products
        cursor.execute('SELECT * FROM jds_products')
        jds_rows = cursor.fetchall()
        
        # Get all Shopify SKUs (cleaned)
        cursor.execute('SELECT sku FROM shopify_products')
        shopify_rows = cursor.fetchall()
        shopify_skus = {clean_sku_for_comparison(row[0]) for row in shopify_rows}
        
        unmatched_products = []
        
        for row in jds_rows:
            jds_product = JDSProduct(**dict(row))
            cleaned_jds_sku = clean_sku_for_comparison(jds_product.sku)
            
            # Check if this JDS product exists in Shopify (using cleaned SKUs)
            if cleaned_jds_sku not in shopify_skus:
                unmatched_products.append(jds_product)
        
        conn.close()
        return unmatched_products
        
    except Exception as e:
        print(f"Error getting unmatched products: {e}")
        return []

def get_matched_products():
    """Get JDS products that exist in Shopify (with SKU cleaning)"""
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        # Get all JDS products
        cursor.execute('SELECT * FROM jds_products')
        jds_rows = cursor.fetchall()
        
        # Get all Shopify SKUs (cleaned)
        cursor.execute('SELECT sku FROM shopify_products')
        shopify_rows = cursor.fetchall()
        shopify_skus = {clean_sku_for_comparison(row[0]) for row in shopify_rows}
        
        matched_products = []
        
        for row in jds_rows:
            jds_product = JDSProduct(**dict(row))
            cleaned_jds_sku = clean_sku_for_comparison(jds_product.sku)
            
            # Check if this JDS product exists in Shopify (using cleaned SKUs)
            if cleaned_jds_sku in shopify_skus:
                matched_products.append(jds_product)
        
        conn.close()
        return matched_products
        
    except Exception as e:
        print(f"Error getting matched products: {e}")
        return []

def get_sku_comparison_stats():
    """Get statistics about SKU matching between JDS and Shopify"""
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute('SELECT COUNT(*) FROM jds_products')
        jds_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM shopify_products')
        shopify_count = cursor.fetchone()[0]
        
        # Get unmatched count
        unmatched = get_unmatched_products()
        unmatched_count = len(unmatched)
        
        matched_count = jds_count - unmatched_count
        
        conn.close()
        
        return {
            'jds_total': jds_count,
            'shopify_total': shopify_count,
            'matched': matched_count,
            'unmatched': unmatched_count,
            'match_percentage': (matched_count / jds_count * 100) if jds_count > 0 else 0
        }
        
    except Exception as e:
        print(f"Error getting SKU comparison stats: {e}")
        return {
            'jds_total': 0,
            'shopify_total': 0,
            'matched': 0,
            'unmatched': 0,
            'match_percentage': 0
        }

def get_shopify_price_for_sku(sku):
    """Get current Shopify price for a given SKU"""
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        # Clean the SKU for comparison
        cleaned_sku = clean_sku_for_comparison(sku)
        
        # Find matching Shopify product
        cursor.execute('SELECT current_price FROM shopify_products WHERE sku = ?', (cleaned_sku,))
        result = cursor.fetchone()
        
        conn.close()
        
        return result[0] if result else None
        
    except Exception as e:
        print(f"Error getting Shopify price for SKU {sku}: {e}")
        return None

def get_matched_products_with_shopify_prices():
    """Get matched products with their current Shopify prices"""
    try:
        matched_products = get_matched_products()
        products_with_prices = []
        
        for product in matched_products:
            product_dict = product.to_dict()
            
            # Get current Shopify price
            shopify_price = get_shopify_price_for_sku(product.sku)
            product_dict['current_shopify_price'] = shopify_price
            
            products_with_prices.append(product_dict)
        
        return products_with_prices
        
    except Exception as e:
        print(f"Error getting matched products with Shopify prices: {e}")
        return []

def get_product_count(table_name):
    """Get count of products in specified table"""
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        if table_name == 'jds':
            cursor.execute('SELECT COUNT(*) FROM jds_products')
        elif table_name == 'shopify':
            cursor.execute('SELECT COUNT(*) FROM shopify_products')
        else:
            return 0
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
        
    except Exception as e:
        print(f"Error getting product count for {table_name}: {e}")
        return 0

# Phase 5: Optimized database functions with caching and performance monitoring

@cached(ttl=300, key_func=lambda: cache_key_for_unmatched_products())
@time_function("get_unmatched_products_optimized")
def get_unmatched_products_optimized(offset: int = 0, limit: int = 100) -> Tuple[List[JDSProduct], int]:
    """
    Get unmatched JDS products with pagination and caching
    
    Args:
        offset: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        Tuple of (products_list, total_count)
    """
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        # Get Shopify SKUs for comparison (cached)
        shopify_skus = get_shopify_skus_cached()
        
        # First, get all unmatched products to determine total count
        cursor.execute('SELECT * FROM jds_products')
        all_jds_rows = cursor.fetchall()
        
        unmatched_rows = []
        for row in all_jds_rows:
            cleaned_sku = clean_sku_for_comparison(row['sku'])
            if cleaned_sku not in shopify_skus:
                unmatched_rows.append(row)
        
        total_count = len(unmatched_rows)
        
        # Apply pagination
        paginated_rows = unmatched_rows[offset:offset + limit]
        unmatched_products = [JDSProduct(**dict(row)) for row in paginated_rows]
        
        conn.close()
        
        # Record performance metrics
        record_metric("unmatched_products_count", len(unmatched_products))
        record_metric("unmatched_products_total", total_count)
        
        return unmatched_products, total_count
        
    except Exception as e:
        logger.error(f"Error getting unmatched products (optimized): {e}")
        record_metric("database_error_count", 1, {"function": "get_unmatched_products_optimized"})
        return [], 0

@cached(ttl=300, key_func=lambda: cache_key_for_matched_products())
@time_function("get_matched_products_optimized")
def get_matched_products_optimized(offset: int = 0, limit: int = 100) -> Tuple[List[JDSProduct], int]:
    """
    Get matched JDS products with pagination and caching
    
    Args:
        offset: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        Tuple of (products_list, total_count)
    """
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        # Get Shopify SKUs for comparison (cached)
        shopify_skus = get_shopify_skus_cached()
        
        # First, get all JDS products to determine matched count
        cursor.execute('SELECT * FROM jds_products')
        all_jds_rows = cursor.fetchall()
        
        matched_rows = []
        for row in all_jds_rows:
            cleaned_sku = clean_sku_for_comparison(row['sku'])
            if cleaned_sku in shopify_skus:
                matched_rows.append(row)
        
        total_count = len(matched_rows)
        
        # Apply pagination
        paginated_rows = matched_rows[offset:offset + limit]
        matched_products = [JDSProduct(**dict(row)) for row in paginated_rows]
        
        conn.close()
        
        # Record performance metrics
        record_metric("matched_products_count", len(matched_products))
        record_metric("matched_products_total", total_count)
        
        return matched_products, total_count
        
    except Exception as e:
        logger.error(f"Error getting matched products (optimized): {e}")
        record_metric("database_error_count", 1, {"function": "get_matched_products_optimized"})
        return [], 0

@cached(ttl=300, key_func=lambda: cache_key_for_comparison_stats())
@time_function("get_sku_comparison_stats_optimized")
def get_sku_comparison_stats_optimized() -> Dict[str, Any]:
    """Get SKU comparison statistics with caching"""
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        # Get counts using optimized queries
        cursor.execute('SELECT COUNT(*) FROM jds_products')
        jds_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM shopify_products')
        shopify_count = cursor.fetchone()[0]
        
        # Get unmatched count using optimized query
        shopify_skus = get_shopify_skus_cached()
        cursor.execute('SELECT sku FROM jds_products')
        jds_skus = [row[0] for row in cursor.fetchall()]
        
        unmatched_count = 0
        for sku in jds_skus:
            cleaned_sku = clean_sku_for_comparison(sku)
            if cleaned_sku not in shopify_skus:
                unmatched_count += 1
        
        matched_count = jds_count - unmatched_count
        
        conn.close()
        
        stats = {
            'jds_total': jds_count,
            'shopify_total': shopify_count,
            'matched': matched_count,
            'unmatched': unmatched_count,
            'match_percentage': (matched_count / jds_count * 100) if jds_count > 0 else 0
        }
        
        # Record performance metrics
        record_metric("comparison_stats_calculated", 1)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting SKU comparison stats (optimized): {e}")
        record_metric("database_error_count", 1, {"function": "get_sku_comparison_stats_optimized"})
        return {
            'jds_total': 0,
            'shopify_total': 0,
            'matched': 0,
            'unmatched': 0,
            'match_percentage': 0
        }

@cached(ttl=600)  # Cache for 10 minutes
def get_shopify_skus_cached() -> set:
    """Get Shopify SKUs with caching"""
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT sku FROM shopify_products WHERE sku IS NOT NULL AND sku != ""')
        rows = cursor.fetchall()
        shopify_skus = {clean_sku_for_comparison(row[0]) for row in rows}
        
        conn.close()
        
        record_metric("shopify_skus_cached", len(shopify_skus))
        return shopify_skus
        
    except Exception as e:
        logger.error(f"Error getting Shopify SKUs (cached): {e}")
        return set()

@time_function("get_products_with_pricing_optimized")
def get_products_with_pricing_optimized(products: List[JDSProduct], 
                                      pricing_func: callable) -> List[Dict[str, Any]]:
    """
    Get products with calculated pricing (optimized version)
    
    Args:
        products: List of JDS products
        pricing_func: Function to calculate pricing
        
    Returns:
        List of products with pricing information
    """
    try:
        products_with_pricing = []
        
        for product in products:
            product_dict = product.to_dict()
            
            # Calculate pricing
            pricing_validation = pricing_func(product_dict)
            product_dict['calculated_prices'] = pricing_validation['calculated_prices']
            product_dict['recommended_price'] = pricing_validation['recommended_price']
            product_dict['pricing_valid'] = pricing_validation['is_valid']
            product_dict['pricing_warnings'] = pricing_validation['warnings']
            product_dict['pricing_errors'] = pricing_validation['errors']
            
            products_with_pricing.append(product_dict)
        
        # Record performance metrics
        record_metric("products_with_pricing_processed", len(products_with_pricing))
        
        return products_with_pricing
        
    except Exception as e:
        logger.error(f"Error getting products with pricing (optimized): {e}")
        record_metric("database_error_count", 1, {"function": "get_products_with_pricing_optimized"})
        return []

def optimize_database() -> Dict[str, Any]:
    """Optimize database performance"""
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        # Analyze tables for query optimization
        cursor.execute('ANALYZE')
        
        # Get database statistics
        cursor.execute('PRAGMA table_info(jds_products)')
        jds_columns = cursor.fetchall()
        
        cursor.execute('PRAGMA table_info(shopify_products)')
        shopify_columns = cursor.fetchall()
        
        # Check index usage
        cursor.execute('PRAGMA index_list(jds_products)')
        jds_indexes = cursor.fetchall()
        
        cursor.execute('PRAGMA index_list(shopify_products)')
        shopify_indexes = cursor.fetchall()
        
        conn.close()
        
        optimization_info = {
            'analyzed': True,
            'jds_columns': len(jds_columns),
            'shopify_columns': len(shopify_columns),
            'jds_indexes': len(jds_indexes),
            'shopify_indexes': len(shopify_indexes),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        record_metric("database_optimized", 1)
        
        return optimization_info
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        record_metric("database_error_count", 1, {"function": "optimize_database"})
        return {'error': str(e)}

def get_database_stats() -> Dict[str, Any]:
    """Get database statistics"""
    try:
        conn = db.connect()
        cursor = conn.cursor()
        
        # Get table sizes
        cursor.execute('SELECT COUNT(*) FROM jds_products')
        jds_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM shopify_products')
        shopify_count = cursor.fetchone()[0]
        
        # Get database file size
        db_size = os.path.getsize(db.db_path) if os.path.exists(db.db_path) else 0
        
        # Get cache stats
        cache_stats = cache_manager.get_stats()
        
        conn.close()
        
        stats = {
            'jds_products': jds_count,
            'shopify_products': shopify_count,
            'total_products': jds_count + shopify_count,
            'database_size_bytes': db_size,
            'database_size_mb': round(db_size / (1024 * 1024), 2),
            'cache_stats': cache_stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {'error': str(e)}
