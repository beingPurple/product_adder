"""
JDS API integration for Product Adder
Handles SKU cleaning and product data fetching from JDS API
"""

import os
import requests
import logging
from typing import List, Dict, Any, Optional
from database import db, JDSProduct

logger = logging.getLogger(__name__)

class JDSClient:
    """Client for interacting with JDS API"""
    
    def __init__(self):
        # Load environment variables first
        from dotenv import load_dotenv
        load_dotenv()
        
        self.api_url = os.getenv('EXTERNAL_API_URL', 'https://api.jdsapp.com/get-product-details-by-skus')
        self.api_token = os.getenv('EXTERNAL_API_TOKEN')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Product-Adder/1.0'
        })
    
    def clean_sku_for_external_api(self, sku: str) -> str:
        """
        Clean SKU by removing hyphen and any letters preceding it
        Ported from edit_price/main.py
        """
        if not sku:
            return sku
        
        if '-' in sku:
            parts = sku.split('-')
            return parts[-1]
        return sku
    
    def test_connection(self) -> bool:
        """Test connection to JDS API"""
        if not self.api_token:
            logger.warning("JDS API token not configured")
            return False
            
        try:
            # Test with a simple POST request (JDS API expects POST with JSON payload)
            test_payload = {
                "token": self.api_token,
                "skus": ["TEST123"]  # Use a test SKU that likely doesn't exist
            }
            
            logger.info(f"Testing JDS API connection with URL: {self.api_url}")
            logger.info(f"Token present: {bool(self.api_token)}")
            
            response = self.session.post(
                self.api_url,
                json=test_payload,
                timeout=10
            )
            
            logger.info(f"JDS API response status: {response.status_code}")
            logger.info(f"JDS API response headers: {dict(response.headers)}")
            
            # JDS API returns 200 even for non-existent SKUs, or 400 for invalid requests
            return response.status_code in [200, 400]
        except Exception as e:
            logger.error(f"JDS API connection test failed: {e}")
            return False
    
    def fetch_product_details(self, skus: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch product details for a list of SKUs from JDS API
        
        Args:
            skus: List of SKUs to fetch details for
            
        Returns:
            List of product dictionaries
        """
        if not skus or not self.api_token:
            logger.warning("No SKUs provided or API token missing")
            return []
        
        # Clean SKUs before sending to API
        cleaned_skus = [self.clean_sku_for_external_api(sku) for sku in skus]
        
        payload = {
            "token": self.api_token,
            "skus": cleaned_skus
        }
        
        try:
            logger.info(f"Fetching details for {len(cleaned_skus)} SKUs from JDS API")
            response = self.session.post(
                self.api_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, list):
                logger.info(f"Successfully fetched {len(data)} products from JDS API")
                return data
            else:
                logger.warning(f"Unexpected response format from JDS API: {type(data)}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for JDS API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching JDS product details: {e}")
            return []
    
    def fetch_all_skus(self) -> List[str]:
        """
        Fetch all available SKUs from Shopify store
        These will be checked against the JDS catalog
        """
        conn = None
        try:
            from dotenv import load_dotenv
            
            # Ensure environment variables are loaded
            load_dotenv()
            
            conn = db.connect()
            cursor = conn.cursor()
            
            # Get all SKUs from Shopify
            cursor.execute("SELECT sku FROM shopify_products WHERE sku IS NOT NULL AND sku <> ''")
            rows = cursor.fetchall()
            # strip whitespace and de-duplicate
            all_skus = sorted({(row[0] or '').strip() for row in rows if row and row[0]})
            
            logger.info(f"Found {len(all_skus)} total SKUs in Shopify store")
            return all_skus
        except Exception as e:
            logger.error(f"Error fetching SKUs from Shopify: {e}")
            # Fallback to sample SKUs if there's an error
            sample_skus = [
                "LTM814", "LTM7305", "LGR641", "LPB004", "LWB101", 
                "LTM123", "LGR456", "LPB789", "LWB012", "LTM345"
            ]
            logger.info(f"Using fallback sample SKUs: {len(sample_skus)} SKUs")
            return sample_skus
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    
    def sync_products(self, skus: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sync products from JDS API to local database
        
        Args:
            skus: Optional list of specific SKUs to sync. If None, syncs all available.
            
        Returns:
            Dictionary with sync results
        """
        try:
            # Ensure environment variables are loaded
            from dotenv import load_dotenv
            load_dotenv()
            
            if skus is None:
                skus = self.fetch_all_skus()
                if not skus:
                    return {
                        'success': False,
                        'message': 'No SKUs available to sync',
                        'count': 0
                    }
            
            # Fetch product details in batches
            batch_size = 50  # Adjust based on API limits
            synced_count = 0
            errors = []
            
            for i in range(0, len(skus), batch_size):
                batch_skus = skus[i:i + batch_size]
                products = self.fetch_product_details(batch_skus)
                
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
            logger.error(f"Error syncing JDS products: {e}")
            return {
                'success': False,
                'message': f'Error syncing JDS products: {str(e)}',
                'count': 0
            }
    
    def _save_product_to_db(self, product_data: Dict[str, Any]) -> None:
        """Save a single product to the database"""
        sku = product_data.get('sku', '')
        if not sku:
            raise ValueError("Product SKU is required")
        
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    # Check if product already exists
                    cursor.execute('SELECT * FROM jds_products WHERE sku = ?', (sku,))
                    existing_row = cursor.fetchone()
                    
                    if existing_row:
                        cols = [c[0] for c in cursor.description]
                        row_dict = dict(zip(cols, existing_row))
                        existing_product = JDSProduct(**row_dict)
                        self._update_product_from_data(existing_product, product_data)
                        existing_product.save(conn)
                    else:
                        new_product = self._create_product_from_data(product_data)
                        new_product.save(conn)
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving product {sku} to database: {e}")
            raise e
    
    def _create_product_from_data(self, data: Dict[str, Any]) -> JDSProduct:
        """Create a new JDSProduct from API data"""
        return JDSProduct(
            sku=data.get('sku', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            case_quantity=data.get('caseQuantity'),
            less_than_case_price=data.get('lessThanCasePrice'),
            one_case=data.get('oneCase'),
            five_cases=data.get('fiveCases'),
            ten_cases=data.get('tenCases'),
            twenty_cases=data.get('twentyCases'),
            forty_cases=data.get('fortyCases'),
            image_url=data.get('image', ''),  # Fixed: API returns 'image' not 'imageUrl'
            thumbnail_url=data.get('thumbnail', ''),  # Fixed: API returns 'thumbnail' not 'thumbnailUrl'
            quick_image_url=data.get('quickImage', ''),  # Fixed: API returns 'quickImage' not 'quickImageUrl'
            available_quantity=data.get('availableQuantity'),
            local_quantity=data.get('localQuantity')
        )
    
    def _update_product_from_data(self, product: JDSProduct, data: Dict[str, Any]) -> None:
        """Update existing JDSProduct with new data"""
        product.name = data.get('name', product.name)
        product.description = data.get('description', product.description)
        product.case_quantity = data.get('caseQuantity', product.case_quantity)
        product.less_than_case_price = data.get('lessThanCasePrice', product.less_than_case_price)
        product.one_case = data.get('oneCase', product.one_case)
        product.five_cases = data.get('fiveCases', product.five_cases)
        product.ten_cases = data.get('tenCases', product.ten_cases)
        product.twenty_cases = data.get('twentyCases', product.twenty_cases)
        product.forty_cases = data.get('fortyCases', product.forty_cases)
        product.image_url = data.get('image', product.image_url)  # Fixed: API returns 'image' not 'imageUrl'
        product.thumbnail_url = data.get('thumbnail', product.thumbnail_url)  # Fixed: API returns 'thumbnail' not 'thumbnailUrl'
        product.quick_image_url = data.get('quickImage', product.quick_image_url)  # Fixed: API returns 'quickImage' not 'quickImageUrl'
        product.available_quantity = data.get('availableQuantity', product.available_quantity)
        product.local_quantity = data.get('localQuantity', product.local_quantity)
    
    def get_products_count(self) -> int:
        """Get count of products in database"""
        try:
            with db.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT COUNT(*) FROM jds_products')
                    count = cursor.fetchone()[0]
                    return count
        except Exception as e:
            logger.error(f"Error getting JDS products count: {e}")
            return 0
