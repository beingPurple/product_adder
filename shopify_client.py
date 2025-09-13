"""
Shopify API integration for Product Adder
Handles product data fetching from Shopify using GraphQL API
"""

import os
import requests
import logging
from typing import List, Dict, Any, Optional
from database import db, ShopifyProduct

logger = logging.getLogger(__name__)

class ShopifyClient:
    """Client for interacting with Shopify GraphQL API"""
    
    def __init__(self):
        self.store = os.getenv('SHOPIFY_STORE')
        self.api_version = os.getenv('SHOPIFY_API_VERSION', '2023-10')
        self.access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        
        if not self.store or not self.access_token:
            logger.warning("Shopify credentials not configured")
            return
        
        self.base_url = f"https://{self.store}/admin/api/{self.api_version}/graphql.json"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.access_token,
            'User-Agent': 'Product-Adder/1.0'
        })
    
    def test_connection(self) -> bool:
        """Test connection to Shopify API"""
        if not self.store or not self.access_token:
            return False
        
        try:
            # Test with a simple GraphQL query
            query = """
            query {
                shop {
                    name
                }
            }
            """
            
            response = self.session.post(
                self.base_url,
                json={'query': query},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Shopify API connection test failed: {e}")
            return False
    
    def fetch_all_products(self) -> List[Dict[str, Any]]:
        """
        Fetch all products from Shopify using GraphQL
        Uses pagination to handle large product catalogs
        """
        if not self.store or not self.access_token:
            logger.warning("Shopify credentials not configured")
            return []
        
        all_products = []
        cursor = None
        has_next_page = True
        
        while has_next_page:
            query = """
            query getProducts($cursor: String) {
                products(first: 250, after: $cursor) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    edges {
                        node {
                            id
                            title
                            variants(first: 100) {
                                edges {
                                    node {
                                        id
                                        sku
                                        price
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """
            
            variables = {"cursor": cursor} if cursor else {}
            
            try:
                response = self.session.post(
                    self.base_url,
                    json={'query': query, 'variables': variables},
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                
                if 'errors' in data:
                    logger.error(f"GraphQL errors: {data['errors']}")
                    break
                
                products_data = data.get('data', {}).get('products', {})
                edges = products_data.get('edges', [])
                
                for edge in edges:
                    product = edge['node']
                    product_id = product['id']
                    product_title = product['title']
                    
                    # Process variants
                    variants = product.get('variants', {}).get('edges', [])
                    for variant_edge in variants:
                        variant = variant_edge['node']
                        sku = variant.get('sku')
                        if sku:  # Only process variants with SKUs
                            all_products.append({
                                'product_id': product_id,
                                'product_title': product_title,
                                'variant_id': variant['id'],
                                'sku': sku,
                                'price': float(variant.get('price', 0))
                            })
                
                # Check pagination
                page_info = products_data.get('pageInfo', {})
                has_next_page = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor')
                
                logger.info(f"Fetched {len(edges)} products, has_next_page: {has_next_page}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for Shopify API: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error fetching Shopify products: {e}")
                break
        
        logger.info(f"Successfully fetched {len(all_products)} product variants from Shopify")
        return all_products
    
    def fetch_products_by_skus(self, skus: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch specific products by SKUs from Shopify
        
        Args:
            skus: List of SKUs to fetch
            
        Returns:
            List of product dictionaries
        """
        if not skus or not self.store or not self.access_token:
            return []
        
        # For now, fetch all products and filter
        # In a more efficient implementation, you might use a different query
        all_products = self.fetch_all_products()
        return [p for p in all_products if p['sku'] in skus]
    
    def sync_products(self, skus: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sync products from Shopify API to local database
        
        Args:
            skus: Optional list of specific SKUs to sync. If None, syncs all products.
            
        Returns:
            Dictionary with sync results
        """
        try:
            if skus:
                products = self.fetch_products_by_skus(skus)
            else:
                products = self.fetch_all_products()
            
            if not products:
                return {
                    'success': False,
                    'message': 'No products available to sync',
                    'count': 0
                }
            
            synced_count = 0
            errors = []
            
            for product_data in products:
                try:
                    self._save_product_to_db(product_data)
                    synced_count += 1
                except Exception as e:
                    error_msg = f"Error saving product {product_data.get('sku', 'unknown')}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            return {
                'success': True,
                'message': f'Successfully synced {synced_count} products',
                'count': synced_count,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Error syncing Shopify products: {e}")
            return {
                'success': False,
                'message': f'Error syncing Shopify products: {str(e)}',
                'count': 0
            }
    
    def _save_product_to_db(self, product_data: Dict[str, Any]) -> None:
        """Save a single product to the database"""
        try:
            sku = product_data.get('sku', '')
            if not sku:
                raise ValueError("Product SKU is required")
            
            # Check if product already exists
            existing_product = ShopifyProduct.query.filter_by(sku=sku).first()
            
            if existing_product:
                # Update existing product
                self._update_product_from_data(existing_product, product_data)
            else:
                # Create new product
                new_product = self._create_product_from_data(product_data)
                db.session.add(new_product)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    def _create_product_from_data(self, data: Dict[str, Any]) -> ShopifyProduct:
        """Create a new ShopifyProduct from API data"""
        return ShopifyProduct(
            sku=data.get('sku', ''),
            product_id=data.get('product_id', ''),
            variant_id=data.get('variant_id', ''),
            current_price=data.get('price', 0.0),
            product_title=data.get('product_title', '')
        )
    
    def _update_product_from_data(self, product: ShopifyProduct, data: Dict[str, Any]) -> None:
        """Update existing ShopifyProduct with new data"""
        product.product_id = data.get('product_id', product.product_id)
        product.variant_id = data.get('variant_id', product.variant_id)
        product.current_price = data.get('price', product.current_price)
        product.product_title = data.get('product_title', product.product_title)
    
    def get_products_count(self) -> int:
        """Get count of products in database"""
        try:
            return ShopifyProduct.query.count()
        except Exception as e:
            logger.error(f"Error getting Shopify products count: {e}")
            return 0
