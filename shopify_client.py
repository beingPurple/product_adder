"""
Shopify API integration for Product Adder
Handles product data fetching from Shopify using GraphQL API
"""

import os
import requests
import logging
import time
from typing import List, Dict, Any, Optional
from database import db, ShopifyProduct

logger = logging.getLogger(__name__)

class ShopifyClient:
    """Client for interacting with Shopify GraphQL API"""
    
    def __init__(self):
        self.store = os.getenv('SHOPIFY_STORE')
        self.api_version = os.getenv('SHOPIFY_API_VERSION', '2023-10')
        # Force a compatible API version if the one in env is too new
        if self.api_version:
            # Parse version string (format: YYYY-MM)
            try:
                year, month = map(int, self.api_version.split('-'))
                if year > 2024 or (year == 2024 and month > 1):
                    self.api_version = '2023-10'
            except (ValueError, AttributeError):
                # If parsing fails, default to safe version
                logger.warning(f"Invalid API version format: {self.api_version}, using default")
                self.api_version = '2023-10'
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
        Fetch all products from Shopify using REST API
        Uses pagination to handle large product catalogs
        """
        if not self.store or not self.access_token:
            logger.warning("Shopify credentials not configured")
            return []

        all_products = []
        limit = 250  # Maximum products per page
        since_id = None
        
        while True:
            # Use REST API instead of GraphQL
            rest_url = f"https://{self.store}/admin/api/{self.api_version}/products.json"
            params = {
                'limit': limit
            }
            if since_id:
                params['since_id'] = since_id
            
            try:
                response = self.session.get(
                    rest_url,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                products = data.get('products', [])
                
                if not products:
                    break  # No more products
                
                for product in products:
                    product_id = product.get('id')
                    product_title = product.get('title', '')
                    
                    # Process variants
                    variants = product.get('variants', [])
                    for variant in variants:
                        sku = variant.get('sku')
                        if sku:  # Only process variants with SKUs
                            all_products.append({
                                'product_id': f"gid://shopify/Product/{product_id}",
                                'product_title': product_title,
                                'variant_id': f"gid://shopify/ProductVariant/{variant.get('id')}",
                                'sku': sku,
                                'price': float(variant.get('price', 0))
                            })
                
                logger.info(f"Fetched {len(products)} products")
                
                # Check if we got fewer products than the limit (last page)
                if len(products) < limit:
                    break
                
                # Set since_id to the last product's ID for next iteration
                if products:
                    since_id = products[-1].get('id')
                else:
                    break
                
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
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM shopify_products WHERE sku = ?', (sku,))
            existing_row = cursor.fetchone()
            
            if existing_row:
                # Update existing product
                # Convert Row to dict properly
                columns = [description[0] for description in cursor.description]
                existing_dict = dict(zip(columns, existing_row))
                existing_product = ShopifyProduct(**existing_dict)
                self._update_product_from_data(existing_product, product_data)
                existing_product.save(db)
            else:
                # Create new product
                new_product = self._create_product_from_data(product_data)
                new_product.save(db)
            
            conn.close()
            
        except Exception as e:
            if conn:
                conn.close()
            raise e
    
    def _save_product_to_db(self, product_data: Dict[str, Any]) -> None:
        """Save a single product to the database"""
        conn = None
        try:
            sku = product_data.get('sku', '')
            if not sku:
                raise ValueError("Product SKU is required")
            
            # Check if product already exists
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM shopify_products WHERE sku = ?', (sku,))
            existing_row = cursor.fetchone()
            
            if existing_row:
                # Update existing product
                # Convert Row to dict properly
                columns = [description[0] for description in cursor.description]
                existing_dict = dict(zip(columns, existing_row))
                existing_product = ShopifyProduct(**existing_dict)
                self._update_product_from_data(existing_product, product_data)
                existing_product.save(db)
            else:
                # Create new product
                new_product = self._create_product_from_data(product_data)
                new_product.save(db)
            
            conn.close()
            
        except Exception as e:
            if conn:
                conn.close()
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
        conn = None
        try:
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM shopify_products')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting Shopify products count: {e}")
            if conn:
                conn.close()
            return 0
    
    def create_product(self, jds_product: Dict[str, Any], calculated_price: float) -> Dict[str, Any]:
        """
        Create a single product in Shopify
        
        Args:
            jds_product: JDS product data dictionary
            calculated_price: Calculated Shopify price
            
        Returns:
            Dictionary with creation results
        """
        if not self.store or not self.access_token:
            return {
                'success': False,
                'error': 'Shopify credentials not configured',
                'product_id': None
            }
        
        try:
            # Prepare product data for Shopify
            product_data = self._prepare_product_data(jds_product, calculated_price)
            
            # Create product using REST API
            response = self.session.post(
                f"https://{self.store}/admin/api/{self.api_version}/products.json",
                json=product_data,
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                product = result.get('product', {})
                
                # Save to local database
                self._save_created_product_to_db(jds_product, product, calculated_price)
                
                return {
                    'success': True,
                    'product_id': product.get('id'),
                    'variant_id': product.get('variants', [{}])[0].get('id'),
                    'shopify_title': product.get('title'),
                    'message': f"Successfully created product: {product.get('title')}"
                }
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get('errors', {}).get('base', ['Unknown error'])[0]
                return {
                    'success': False,
                    'error': f"Shopify API error: {error_message}",
                    'product_id': None
                }
                
        except Exception as e:
            logger.error(f"Error creating product {jds_product.get('sku', 'unknown')}: {e}")
            return {
                'success': False,
                'error': f"Error creating product: {str(e)}",
                'product_id': None
            }
    
    def create_products_bulk(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple products in Shopify with progress tracking and rollback
        
        Args:
            products: List of product dictionaries with JDS data and calculated prices
            
        Returns:
            Dictionary with bulk creation results
        """
        if not products:
            return {
                'success': True,
                'message': 'No products to create',
                'created_count': 0,
                'failed_count': 0,
                'results': []
            }
        
        results = []
        created_count = 0
        failed_count = 0
        created_products = []  # Track created products for rollback
        
        logger.info(f"Starting bulk creation of {len(products)} products")
        
        for i, product_data in enumerate(products):
            try:
                jds_product = product_data.get('jds_product', {})
                calculated_price = product_data.get('calculated_price', 0)
                
                result = self.create_product_with_retry(jds_product, calculated_price)
                results.append({
                    'sku': jds_product.get('sku', 'unknown'),
                    'name': jds_product.get('name', 'Unknown'),
                    'success': result['success'],
                    'product_id': result.get('product_id'),
                    'error': result.get('error')
                })
                
                if result['success']:
                    created_count += 1
                    created_products.append({
                        'sku': jds_product.get('sku', 'unknown'),
                        'product_id': result.get('product_id'),
                        'variant_id': result.get('variant_id')
                    })
                else:
                    failed_count += 1
                
                # Add small delay to avoid rate limiting
                if i < len(products) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error processing product {i}: {e}")
                results.append({
                    'sku': product_data.get('jds_product', {}).get('sku', 'unknown'),
                    'name': product_data.get('jds_product', {}).get('name', 'Unknown'),
                    'success': False,
                    'product_id': None,
                    'error': str(e)
                })
                failed_count += 1
        
        # If there were failures and we have created products, offer rollback
        if failed_count > 0 and created_count > 0:
            logger.warning(f"Bulk creation had {failed_count} failures. {created_count} products were created.")
            # Note: In a production environment, you might want to implement automatic rollback
            # For now, we'll just log the created products for manual cleanup if needed
        
        success = failed_count == 0
        message = f"Bulk creation completed: {created_count} created, {failed_count} failed"
        
        logger.info(message)
        
        return {
            'success': success,
            'message': message,
            'created_count': created_count,
            'failed_count': failed_count,
            'results': results,
            'created_products': created_products  # For potential rollback
        }
    
    def _prepare_product_data(self, jds_product: Dict[str, Any], calculated_price: float) -> Dict[str, Any]:
        """Prepare JDS product data for Shopify product creation"""
        
        # Clean and prepare the product title
        title = jds_product.get('name', 'Unnamed Product')
        if len(title) > 255:  # Shopify title limit
            title = title[:252] + "..."
        
        # Prepare description
        description = jds_product.get('description', '')
        if not description:
            description = f"Product SKU: {jds_product.get('sku', 'N/A')}"
        
        # Prepare images
        images = []
        image_urls = [
            jds_product.get('image_url'),
            jds_product.get('thumbnail_url'),
            jds_product.get('quick_image_url')
        ]
        
        for url in image_urls:
            if url and url.strip():
                images.append({'src': url.strip()})
                break  # Only use the first valid image
        
        # Create product data structure
        product_data = {
            'product': {
                'title': title,
                'body_html': f"<p>{description}</p>",
                'vendor': 'JDS Wholesale',
                'product_type': 'General',
                'tags': ['JDS', 'Wholesale', jds_product.get('sku', '')],
                'variants': [{
                    'sku': jds_product.get('sku', ''),
                    'price': str(calculated_price),
                    'inventory_management': 'shopify',
                    'inventory_quantity': jds_product.get('available_quantity', 0),
                    'requires_shipping': True,
                    'taxable': True,
                    'weight': '0.1',  # Default weight
                    'weight_unit': 'kg'
                }],
                'options': [{
                    'name': 'Title',
                    'values': ['Default Title']
                }]
            }
        }
        
        # Add images if available
        if images:
            product_data['product']['images'] = images
        
        return product_data
    
    def _save_created_product_to_db(self, jds_product: Dict[str, Any], shopify_product: Dict[str, Any], calculated_price: float) -> None:
        """Save created Shopify product to local database"""
        try:
            sku = jds_product.get('sku', '')
            product_id = f"gid://shopify/Product/{shopify_product.get('id')}"
            variant_id = f"gid://shopify/ProductVariant/{shopify_product.get('variants', [{}])[0].get('id')}"
            product_title = shopify_product.get('title', '')
            
            # Create new ShopifyProduct record
            new_product = ShopifyProduct(
                sku=sku,
                product_id=product_id,
                variant_id=variant_id,
                current_price=calculated_price,
                product_title=product_title
            )
            
            new_product.save(db)
            logger.info(f"Saved created product to database: {sku}")
            
        except Exception as e:
            logger.error(f"Error saving created product to database: {e}")
    
    def update_product_price(self, variant_id: str, new_price: float) -> Dict[str, Any]:
        """
        Update product price in Shopify
        
        Args:
            variant_id: Shopify variant ID
            new_price: New price to set
            
        Returns:
            Dictionary with update results
        """
        if not self.store or not self.access_token:
            return {
                'success': False,
                'error': 'Shopify credentials not configured'
            }
        
        try:
            # Extract numeric ID from GID
            if variant_id.startswith('gid://shopify/ProductVariant/'):
                variant_id = variant_id.split('/')[-1]
            
            update_data = {
                'variant': {
                    'id': int(variant_id),
                    'price': str(new_price)
                }
            }
            
            response = self.session.put(
                f"https://{self.store}/admin/api/{self.api_version}/variants/{variant_id}.json",
                json=update_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': f"Successfully updated price to ${new_price}"
                }
            else:
                error_data = response.json() if response.content else {}
                error_message = error_data.get('errors', {}).get('base', ['Unknown error'])[0]
                return {
                    'success': False,
                    'error': f"Shopify API error: {error_message}"
                }
                
        except Exception as e:
            logger.error(f"Error updating product price: {e}")
            return {
                'success': False,
                'error': f"Error updating price: {str(e)}"
            }
    
    def create_product_with_retry(self, jds_product: Dict[str, Any], calculated_price: float, max_retries: int = 3) -> Dict[str, Any]:
        """
        Create a single product with retry logic
        
        Args:
            jds_product: JDS product data dictionary
            calculated_price: Calculated Shopify price
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with creation results
        """
        for attempt in range(max_retries + 1):
            try:
                result = self.create_product(jds_product, calculated_price)
                
                # If successful or it's a validation error (not retryable), return immediately
                if result['success'] or 'validation' in result.get('error', '').lower():
                    return result
                
                # If it's a rate limit error and we have retries left, wait and retry
                if 'rate limit' in result.get('error', '').lower() and attempt < max_retries:
                    wait_time = (2 ** attempt) + 1  # Exponential backoff: 2, 4, 8 seconds
                    logger.warning(f"Rate limited, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                
                # For other errors, don't retry
                return result
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 1
                    logger.warning(f"Exception during product creation, retrying in {wait_time} seconds: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        'success': False,
                        'error': f"Error creating product after {max_retries} retries: {str(e)}",
                        'product_id': None
                    }
        
        return {
            'success': False,
            'error': 'Max retries exceeded',
            'product_id': None
        }
    
    def update_product_price_with_retry(self, variant_id: str, new_price: float, max_retries: int = 3) -> Dict[str, Any]:
        """
        Update product price with retry logic
        
        Args:
            variant_id: Shopify variant ID
            new_price: New price to set
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with update results
        """
        for attempt in range(max_retries + 1):
            try:
                result = self.update_product_price(variant_id, new_price)
                
                # If successful or it's a validation error (not retryable), return immediately
                if result['success'] or 'validation' in result.get('error', '').lower():
                    return result
                
                # If it's a rate limit error and we have retries left, wait and retry
                if 'rate limit' in result.get('error', '').lower() and attempt < max_retries:
                    wait_time = (2 ** attempt) + 1  # Exponential backoff
                    logger.warning(f"Rate limited, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                
                # For other errors, don't retry
                return result
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = (2 ** attempt) + 1
                    logger.warning(f"Exception during price update, retrying in {wait_time} seconds: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        'success': False,
                        'error': f"Error updating price after {max_retries} retries: {str(e)}"
                    }
        
        return {
            'success': False,
            'error': 'Max retries exceeded'
        }
    
    def rollback_created_products(self, created_products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Rollback created products by deleting them from Shopify
        
        Args:
            created_products: List of created product dictionaries with product_id
            
        Returns:
            Dictionary with rollback results
        """
        if not created_products:
            return {
                'success': True,
                'message': 'No products to rollback',
                'deleted_count': 0
            }
        
        deleted_count = 0
        errors = []
        
        logger.info(f"Starting rollback of {len(created_products)} products")
        
        for product in created_products:
            try:
                product_id = product.get('product_id')
                if not product_id:
                    errors.append(f"No product ID for SKU {product.get('sku', 'unknown')}")
                    continue
                
                # Extract numeric ID from GID
                if product_id.startswith('gid://shopify/Product/'):
                    product_id = product_id.split('/')[-1]
                
                # Delete product from Shopify
                response = self.session.delete(
                    f"https://{self.store}/admin/api/{self.api_version}/products/{product_id}.json",
                    timeout=30
                )
                
                if response.status_code == 200:
                    # Remove from local database
                    sku = product.get('sku', '')
                    conn = db.connect()
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM shopify_products WHERE sku = ?', (sku,))
                    conn.commit()
                    conn.close()
                    
                    deleted_count += 1
                    logger.info(f"Successfully rolled back product: {sku}")
                else:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get('errors', {}).get('base', ['Unknown error'])[0]
                    errors.append(f"Failed to delete {product.get('sku', 'unknown')}: {error_message}")
                
            except Exception as e:
                error_msg = f"Error rolling back product {product.get('sku', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        success = len(errors) == 0
        message = f"Rollback completed: {deleted_count} deleted, {len(errors)} errors"
        
        logger.info(message)
        
        return {
            'success': success,
            'message': message,
            'deleted_count': deleted_count,
            'errors': errors
        }
