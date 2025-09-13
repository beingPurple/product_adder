"""
Simple database implementation using SQLite3 directly
This avoids SQLAlchemy compatibility issues with Python 3.13
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class SimpleDB:
    def __init__(self, db_path="product_adder.db"):
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
