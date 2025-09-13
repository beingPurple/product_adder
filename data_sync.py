"""
Data Synchronization Module for Product Adder
Handles syncing data between JDS API, Shopify API, and local database
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from database import db, get_sku_comparison_stats, clean_sku_for_comparison
from jds_client import JDSClient
from shopify_client import ShopifyClient
from pricing_calculator import pricing_calculator

logger = logging.getLogger(__name__)

class DataSyncManager:
    """Manages data synchronization between APIs and local database"""
    
    def __init__(self):
        # Ensure environment variables are loaded
        from dotenv import load_dotenv
        load_dotenv()
        
        self.jds_client = JDSClient()
        self.shopify_client = ShopifyClient()
        self.last_sync = None
        self.sync_errors = []
        self.jds_connected = None
        self.shopify_connected = None
        self.last_connection_test = None
    
    def sync_all_data(self, force: bool = False) -> Dict[str, Any]:
        """
        Sync all data from both APIs
        
        Args:
            force: Force sync even if recently synced
            
        Returns:
            Dictionary with sync results
        """
        sync_results = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'jds_sync': {},
            'shopify_sync': {},
            'comparison_stats': {},
            'errors': []
        }
        
        try:
            # Check if we should skip sync (unless forced)
            if not force and self._should_skip_sync():
                sync_results['message'] = 'Sync skipped - recently synced'
                return sync_results
            
            # Sync JDS data
            logger.info("Starting JDS data sync...")
            jds_result = self.sync_jds_data()
            sync_results['jds_sync'] = jds_result
            
            # Sync Shopify data
            logger.info("Starting Shopify data sync...")
            shopify_result = self.sync_shopify_data()
            sync_results['shopify_sync'] = shopify_result
            
            # Get comparison stats
            sync_results['comparison_stats'] = get_sku_comparison_stats()
            
            # Update last sync time
            self.last_sync = datetime.utcnow()
            
            # Check for any critical errors
            if not jds_result.get('success', False) and not shopify_result.get('success', False):
                sync_results['success'] = False
                sync_results['message'] = 'Both JDS and Shopify sync failed'
            elif not jds_result.get('success', False):
                sync_results['message'] = 'JDS sync failed, but Shopify sync succeeded'
            elif not shopify_result.get('success', False):
                sync_results['message'] = 'Shopify sync failed, but JDS sync succeeded'
            else:
                sync_results['message'] = 'All data synced successfully'
            
            logger.info(f"Data sync completed: {sync_results['message']}")
            
        except Exception as e:
            logger.error(f"Error during data sync: {e}")
            sync_results['success'] = False
            sync_results['message'] = f'Data sync failed: {str(e)}'
            sync_results['errors'].append(str(e))
        
        return sync_results
    
    def sync_jds_data(self, skus: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sync JDS data to local database
        
        Args:
            skus: Optional list of specific SKUs to sync
            
        Returns:
            Dictionary with sync results
        """
        try:
            result = self.jds_client.sync_products(skus)
            
            # Add validation
            if result.get('success', False):
                result['validated'] = self._validate_jds_data()
            
            return result
            
        except Exception as e:
            logger.error(f"Error syncing JDS data: {e}")
            return {
                'success': False,
                'message': f'JDS sync failed: {str(e)}',
                'count': 0
            }
    
    def sync_shopify_data(self, skus: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sync Shopify data to local database
        
        Args:
            skus: Optional list of specific SKUs to sync
            
        Returns:
            Dictionary with sync results
        """
        try:
            result = self.shopify_client.sync_products(skus)
            
            # Add validation
            if result.get('success', False):
                result['validated'] = self._validate_shopify_data()
            
            return result
            
        except Exception as e:
            logger.error(f"Error syncing Shopify data: {e}")
            return {
                'success': False,
                'message': f'Shopify sync failed: {str(e)}',
                'count': 0
            }
    
    def get_unmatched_products_with_pricing(self) -> List[Dict[str, Any]]:
        """
        Get unmatched JDS products with calculated Shopify prices
        
        Returns:
            List of unmatched products with pricing information
        """
        try:
            from database import get_unmatched_products
            
            unmatched_products = get_unmatched_products()
            products_with_pricing = []
            
            for product in unmatched_products:
                product_dict = product.to_dict()
                
                # Convert all price-related fields to float to handle string inputs from database
                price_fields = ['less_than_case_price', 'recommended_price', 'calculated_prices']
                
                for field in price_fields:
                    if field in product_dict:
                        try:
                            if field == 'calculated_prices' and isinstance(product_dict[field], dict):
                                # Handle calculated_prices dictionary
                                for tier, price in product_dict[field].items():
                                    if isinstance(price, (str, int, float)):
                                        product_dict[field][tier] = float(price) if price is not None else 0.0
                            else:
                                product_dict[field] = float(product_dict[field]) if product_dict[field] is not None else 0.0
                        except (ValueError, TypeError):
                            if field == 'calculated_prices':
                                product_dict[field] = {}
                            else:
                                product_dict[field] = 0.0
                
                # Calculate pricing
                pricing_validation = pricing_calculator.validate_pricing_data(product_dict)
                product_dict['calculated_prices'] = pricing_validation['calculated_prices']
                product_dict['recommended_price'] = pricing_validation['recommended_price']
                product_dict['pricing_valid'] = pricing_validation['is_valid']
                product_dict['pricing_warnings'] = pricing_validation['warnings']
                product_dict['pricing_errors'] = pricing_validation['errors']
                
                products_with_pricing.append(product_dict)
            
            return products_with_pricing
            
        except Exception as e:
            logger.error(f"Error getting unmatched products with pricing: {e}")
            return []
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """
        Validate data integrity across all systems
        
        Returns:
            Dictionary with validation results
        """
        validation = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'jds_validation': {},
            'shopify_validation': {},
            'comparison_validation': {},
            'errors': []
        }
        
        try:
            # Validate JDS data
            validation['jds_validation'] = self._validate_jds_data()
            
            # Validate Shopify data
            validation['shopify_validation'] = self._validate_shopify_data()
            
            # Validate comparison logic
            validation['comparison_validation'] = self._validate_comparison_logic()
            
            # Overall success
            validation['success'] = all([
                validation['jds_validation'].get('success', False),
                validation['shopify_validation'].get('success', False),
                validation['comparison_validation'].get('success', False)
            ])
            
        except Exception as e:
            logger.error(f"Error validating data integrity: {e}")
            validation['success'] = False
            validation['errors'].append(str(e))
        
        return validation
    
    def _should_skip_sync(self) -> bool:
        """Check if we should skip sync based on last sync time"""
        if not self.last_sync:
            return False
        
        # Skip if synced within last 5 minutes
        time_since_sync = datetime.utcnow() - self.last_sync
        return time_since_sync < timedelta(minutes=5)
    
    def _validate_jds_data(self) -> Dict[str, Any]:
        """Validate JDS data integrity"""
        conn = None
        try:
            conn = db.connect()
            cursor = conn.cursor()
            
            # Check for products with missing required fields
            cursor.execute('''
                SELECT COUNT(*) FROM jds_products 
                WHERE sku IS NULL OR sku = '' OR name IS NULL OR name = ''
            ''')
            invalid_products = cursor.fetchone()[0]
            
            # Check for products with no pricing data
            cursor.execute('''
                SELECT COUNT(*) FROM jds_products 
                WHERE less_than_case_price IS NULL 
                AND one_case IS NULL 
                AND five_cases IS NULL 
                AND ten_cases IS NULL 
                AND twenty_cases IS NULL 
                AND forty_cases IS NULL
            ''')
            no_pricing = cursor.fetchone()[0]
            
            # Get total count
            cursor.execute('SELECT COUNT(*) FROM jds_products')
            total_products = cursor.fetchone()[0]
            
            return {
                'success': invalid_products == 0,
                'total_products': total_products,
                'invalid_products': invalid_products,
                'no_pricing_products': no_pricing,
                'warnings': [
                    f"{invalid_products} products with missing required fields",
                    f"{no_pricing} products with no pricing data"
                ] if invalid_products > 0 or no_pricing > 0 else []
            }
            
        except Exception as e:
            logger.error(f"Error validating JDS data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if conn:
                conn.close()
    
    def _validate_shopify_data(self) -> Dict[str, Any]:
        """Validate Shopify data integrity"""
        conn = None
        try:
            conn = db.connect()
            cursor = conn.cursor()
            
            # Check for products with missing required fields
            cursor.execute('''
                SELECT COUNT(*) FROM shopify_products 
                WHERE sku IS NULL OR sku = '' OR product_id IS NULL OR product_id = ''
            ''')
            invalid_products = cursor.fetchone()[0]
            
            # Get total count
            cursor.execute('SELECT COUNT(*) FROM shopify_products')
            total_products = cursor.fetchone()[0]
            
            return {
                'success': invalid_products == 0,
                'total_products': total_products,
                'invalid_products': invalid_products,
                'warnings': [
                    f"{invalid_products} products with missing required fields"
                ] if invalid_products > 0 else []
            }
            
        except Exception as e:
            logger.error(f"Error validating Shopify data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if conn:
                conn.close()
    
    def _validate_shopify_data(self) -> Dict[str, Any]:
        """Validate Shopify data integrity"""
        try:
            conn = db.connect()
            cursor = conn.cursor()
            
            # Check for products with missing required fields
            cursor.execute('''
                SELECT COUNT(*) FROM shopify_products 
                WHERE sku IS NULL OR sku = '' OR product_id IS NULL OR product_id = ''
            ''')
            invalid_products = cursor.fetchone()[0]
            
            # Get total count
            cursor.execute('SELECT COUNT(*) FROM shopify_products')
            total_products = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'success': invalid_products == 0,
                'total_products': total_products,
                'invalid_products': invalid_products,
                'warnings': [
                    f"{invalid_products} products with missing required fields"
                ] if invalid_products > 0 else []
            }
            
        except Exception as e:
            logger.error(f"Error validating Shopify data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_comparison_logic(self) -> Dict[str, Any]:
        """Validate SKU comparison logic"""
        try:
            stats = get_sku_comparison_stats()
            
            # Check for reasonable match percentage
            match_percentage = stats.get('match_percentage', 0)
            
            warnings = []
            if match_percentage < 10:
                warnings.append(f"Very low match percentage: {match_percentage:.1f}%")
            elif match_percentage > 95:
                warnings.append(f"Very high match percentage: {match_percentage:.1f}%")
            
            return {
                'success': True,
                'stats': stats,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.error(f"Error validating comparison logic: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_connections(self) -> Dict[str, bool]:
        """Test and cache connection status for both APIs"""
        try:
            # Test connections
            jds_connected = self.jds_client.test_connection()
            shopify_connected = self.shopify_client.test_connection()
            
            # Cache the results
            self.jds_connected = jds_connected
            self.shopify_connected = shopify_connected
            self.last_connection_test = datetime.utcnow()
            
            return {
                'jds_api_connected': jds_connected,
                'shopify_api_connected': shopify_connected
            }
            
        except Exception as e:
            logger.error(f"Error testing connections: {e}")
            return {
                'jds_api_connected': False,
                'shopify_api_connected': False
            }
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get cached connection status, test if not available or stale"""
        from datetime import timedelta
        
        # Test connections if not cached or if cache is stale (older than 5 minutes)
        if (self.jds_connected is None or 
            self.shopify_connected is None or 
            self.last_connection_test is None or
            datetime.utcnow() - self.last_connection_test > timedelta(minutes=5)):
            
            return self.test_connections()
        
        return {
            'jds_api_connected': self.jds_connected,
            'shopify_api_connected': self.shopify_connected
        }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status and statistics"""
        try:
            stats = get_sku_comparison_stats()
            connection_status = self.get_connection_status()
            
            return {
                'last_sync': self.last_sync.isoformat() if self.last_sync else None,
                'jds_products': stats['jds_total'],
                'shopify_products': stats['shopify_total'],
                'matched_products': stats['matched'],
                'unmatched_products': stats['unmatched'],
                'match_percentage': stats['match_percentage'],
                'jds_api_connected': connection_status['jds_api_connected'],
                'shopify_api_connected': connection_status['shopify_api_connected']
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                'error': str(e)
            }

# Global sync manager instance
sync_manager = DataSyncManager()

def sync_all_data(force: bool = False) -> Dict[str, Any]:
    """Convenience function for syncing all data"""
    return sync_manager.sync_all_data(force)

def get_unmatched_products_with_pricing() -> List[Dict[str, Any]]:
    """Convenience function for getting unmatched products with pricing"""
    return sync_manager.get_unmatched_products_with_pricing()

def get_sync_status() -> Dict[str, Any]:
    """Convenience function for getting sync status"""
    return sync_manager.get_sync_status()

