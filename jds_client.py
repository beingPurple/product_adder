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
        try:
            # Test with a simple request
            response = self.session.get(
                self.api_url,
                params={'token': self.api_token},
                timeout=10
            )
            return response.status_code in [200, 400]  # 400 might be expected for missing SKUs
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
        Fetch all available SKUs from JDS
        This is a placeholder - in practice, you might need to implement
        a different endpoint or pagination strategy
        """
        # For now, return an empty list
        # In a real implementation, you might have a separate endpoint
        # or need to maintain a list of known SKUs
        logger.warning("fetch_all_skus not implemented - returning empty list")
        return []
    
    def sync_products(self, skus: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sync products from JDS API to local database
        
        Args:
            skus: Optional list of specific SKUs to sync. If None, syncs all available.
            
        Returns:
            Dictionary with sync results
        """
        try:
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
        try:
            sku = product_data.get('sku', '')
            if not sku:
                raise ValueError("Product SKU is required")
            
            # Check if product already exists
            existing_product = JDSProduct.query.filter_by(sku=sku).first()
            
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
            image_url=data.get('imageUrl', ''),
            thumbnail_url=data.get('thumbnailUrl', ''),
            quick_image_url=data.get('quickImageUrl', ''),
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
        product.image_url = data.get('imageUrl', product.image_url)
        product.thumbnail_url = data.get('thumbnailUrl', product.thumbnail_url)
        product.quick_image_url = data.get('quickImageUrl', product.quick_image_url)
        product.available_quantity = data.get('availableQuantity', product.available_quantity)
        product.local_quantity = data.get('localQuantity', product.local_quantity)
    
    def get_products_count(self) -> int:
        """Get count of products in database"""
        try:
            return JDSProduct.query.count()
        except Exception as e:
            logger.error(f"Error getting JDS products count: {e}")
            return 0
