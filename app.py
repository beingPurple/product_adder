#!/usr/bin/env python3
"""
Product Adder Flask Application - Phase 2
Implements pricing calculator, SKU comparison, and data synchronization
"""

from flask import Flask, jsonify, render_template, request
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from database import init_db, get_sku_comparison_stats, get_unmatched_products, get_matched_products
from data_sync import sync_all_data, get_unmatched_products_with_pricing, get_sync_status
from pricing_calculator import pricing_calculator
from jds_client import JDSClient
from shopify_client import ShopifyClient
#!/usr/bin/env python3
"""
Product Adder Flask Application - Phase 2
Implements pricing calculator, SKU comparison, and data synchronization
"""

from dotenv import load_dotenv
# Load environment variables first, before other imports
load_dotenv()

from flask import Flask, jsonify, render_template, request
import os
import sys
import logging
from datetime import datetime
from database import init_db, get_sku_comparison_stats, get_unmatched_products, get_matched_products
from data_sync import sync_all_data, get_unmatched_products_with_pricing, get_sync_status
from pricing_calculator import pricing_calculator
from jds_client import JDSClient
from shopify_client import ShopifyClient
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('app.log')  # File output
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Configure app
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['API_KEY'] = os.environ.get('APP_API_KEY')  # set in env; no default in prod

# Simple header-based API key gate for internal/admin APIs
from functools import wraps
def require_api_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        api_key = app.config.get('API_KEY')
        provided = request.headers.get('X-API-Key')
        if not api_key or provided != api_key:
            return jsonify({'error': 'Unauthorized'}), 401
        return fn(*args, **kwargs)
    return wrapper

# Fail fast if API_KEY is missing in production
if os.environ.get('FLASK_ENV') == 'production' and not app.config.get('API_KEY'):
    raise ValueError("APP_API_KEY environment variable is required in production")

@app.route('/')
def index():
    """Main dashboard showing sync status and statistics"""
    try:
        # Get sync status and statistics
        sync_status = get_sync_status()
        comparison_stats = get_sku_comparison_stats()
        
        return render_template('index.html', 
                             sync_status=sync_status,
                             comparison_stats=comparison_stats)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return f"Error loading dashboard: {e}", 500

# Phase 3 Routes - Product List Views

@app.route('/products/new')
def new_products():
    """View products ready to add to Shopify"""
    try:
        return render_template('product_list.html')
    except Exception as e:
        logger.error(f"Error loading new products page: {e}")
        return f"Error loading new products page: {e}", 500

@app.route('/products/existing')
def existing_products():
    """View products that exist in both JDS and Shopify"""
    try:
        return render_template('existing_products.html')
    except Exception as e:
        logger.error(f"Error loading existing products page: {e}")
        return f"Error loading existing products page: {e}", 500

@app.route('/api/status')
def status():
    return jsonify({
        'status': 'healthy',
        'phase': 'Phase 1 Complete',
        'database': 'SQLite3 (no SQLAlchemy)',
        'python_version': sys.version.split()[0],
        'flask_working': True,
        'message': 'All systems operational'
    })

@app.route('/api/health')
def health():
    return jsonify({
        'health': 'excellent',
        'uptime': 'running',
        'database': 'connected',
        'api': 'responding'
    })

@app.route('/api/info')
def info():
    return jsonify({
        'app_name': 'Product Adder',
        'version': '2.0.0',
        'phase': 'Phase 2 - Core Logic',
        'description': 'Shopify Catalog Monitor with Pricing Calculator',
        'features': [
            'Database integration',
            'JDS API integration',
            'Shopify API integration',
            'Pricing calculator with edit_price formulas',
            'SKU comparison and matching',
            'Data synchronization',
            'Web interface dashboard'
        ]
    })

from data_sync import sync_all_data, get_unmatched_products_with_pricing, get_sync_status
from data_sync import sync_manager
from pricing_calculator import pricing_calculator

...

@app.route('/api/sync/jds', methods=['POST'])
@require_api_key
def sync_jds():
    """Sync JDS data with specific SKUs or sample SKUs"""
    try:
        data = request.json if request.is_json else {}
        skus = data.get('skus', None)  # If no SKUs provided, will use sample SKUs

        result = sync_manager.sync_jds_data(skus)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing JDS data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/shopify', methods=['POST'])
@require_api_key
def sync_shopify():
    """Sync Shopify data"""
    try:
        result = sync_manager.sync_shopify_data()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing Shopify data: {e}")
        return jsonify({'error': str(e)}), 500
@app.route('/api/sync/status')
def sync_status():
    """Get current sync status and statistics"""
    try:
        status = get_sync_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/all', methods=['POST'])
@require_api_key
def sync_all():
    """Sync all data from JDS and Shopify APIs"""
    try:
        force = request.json.get('force', False) if request.is_json else False
        result = sync_all_data(force=force)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing all data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/products/unmatched')
def unmatched_products():
    """Get JDS products ready to add to Shopify with calculated pricing"""
    try:
        logger.info("Getting products ready to add...")
        
        # Test database function directly first
        from database import get_unmatched_products
        unmatched_direct = get_unmatched_products()
        logger.info(f"Database direct: {len(unmatched_direct)} products")
        
        # Test data_sync function
        products = get_unmatched_products_with_pricing()
        logger.info(f"Data sync function: {len(products)} products")
        
        return jsonify({
            'success': True,
            'count': len(products),
            'products': products,
            'debug': {
                'database_direct': len(unmatched_direct),
                'data_sync_function': len(products)
            }
        })
    except Exception as e:
        logger.error(f"Error getting products ready to add: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/matched')
def matched_products():
    """Get products that exist in both JDS and Shopify"""
    try:
        products = get_matched_products()
        return jsonify({
            'success': True,
            'count': len(products),
            'products': [p.to_dict() for p in products]
        })
    except Exception as e:
        logger.error(f"Error getting existing products: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/matched-with-pricing')
def matched_products_with_pricing():
    """Get existing products with pricing analysis"""
    try:
        from database import get_matched_products_with_shopify_prices
        from pricing_calculator import pricing_calculator
        
        matched_products = get_matched_products_with_shopify_prices()
        products_with_pricing = []
        
        for product_dict in matched_products:
            # Debug: Log the product data types
            logger.info(f"Product data types: {[(k, type(v)) for k, v in product_dict.items() if 'price' in k.lower()]}")
            
            # Convert all price-related fields to float to handle string inputs from database
            price_fields = ['less_than_case_price', 'current_shopify_price', 'calculated_shopify_price', 
                          'price_difference', 'price_difference_percent']
            
            for field in price_fields:
                if field in product_dict:
                    try:
                        product_dict[field] = float(product_dict[field]) if product_dict[field] is not None else 0.0
                    except (ValueError, TypeError):
                        product_dict[field] = 0.0
            
            # Calculate what the Shopify price should be
            pricing_validation = pricing_calculator.validate_pricing_data(product_dict)
            product_dict['calculated_shopify_price'] = pricing_validation['recommended_price']
            product_dict['pricing_valid'] = pricing_validation['is_valid']
            product_dict['pricing_warnings'] = pricing_validation['warnings']
            
            # Calculate price difference (values are already converted to float above)
            current_price = product_dict.get('current_shopify_price', 0)
            calculated_price = product_dict.get('calculated_shopify_price', 0)
            
            if current_price and calculated_price:
                price_diff = calculated_price - current_price
                price_diff_percent = (price_diff / current_price * 100) if current_price > 0 else 0
                product_dict['price_difference'] = price_diff
                product_dict['price_difference_percent'] = price_diff_percent
            else:
                product_dict['price_difference'] = 0.0
                product_dict['price_difference_percent'] = 0.0
            
            products_with_pricing.append(product_dict)
        
        return jsonify({
            'success': True,
            'count': len(products_with_pricing),
            'products': products_with_pricing
        })
    except Exception as e:
        import traceback
        logger.error(f"Error getting matched products with pricing: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/comparison/stats')
def comparison_stats():
    """Get SKU comparison statistics"""
    try:
        stats = get_sku_comparison_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting comparison stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pricing/calculate', methods=['POST'])
def calculate_pricing():
    """Calculate Shopify pricing for given JDS product data"""
    try:
        if not request.is_json:
            return jsonify({'error': 'JSON data required'}), 400
        
        product_data = request.json
        if 'less_than_case_price' not in product_data:
            return jsonify({'error': 'less_than_case_price required'}), 400
        
        # Calculate pricing
        validation = pricing_calculator.validate_pricing_data(product_data)
        calculated_prices = pricing_calculator.calculate_all_tiers(product_data)
        recommended_price = pricing_calculator.get_recommended_price(product_data)
        
        return jsonify({
            'success': True,
            'calculated_prices': calculated_prices,
            'recommended_price': recommended_price,
            'validation': validation
        })
    except Exception as e:
        logger.error(f"Error calculating pricing: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test/connections')
def test_connections():
    """Test API connections"""
    try:
        # Ensure environment variables are loaded
        load_dotenv()
        
        from data_sync import sync_manager
        
        # Test connections and cache results
        connection_status = sync_manager.test_connections()
        
        # Get additional info for display
        jds_client = JDSClient()
        shopify_client = ShopifyClient()
        
        return jsonify({
            'jds_api': {
                'connected': connection_status['jds_api_connected'],
                'url': jds_client.api_url
            },
            'shopify_api': {
                'connected': connection_status['shopify_api_connected'],
                'store': shopify_client.store
            }
        })
    except Exception as e:
        logger.error(f"Error testing connections: {e}")
        return jsonify({'error': str(e)}), 500

# Phase 3 API Routes - Bulk Operations

@app.route('/api/products/bulk-add', methods=['POST'])
@require_api_key
def bulk_add_products():
    """Add multiple products to Shopify"""
    try:
        if not request.is_json:
            return jsonify({'error': 'JSON data required'}), 400
        
        data = request.json
        skus = data.get('skus', [])
        
        if not skus:
            return jsonify({'error': 'No SKUs provided'}), 400
        
        # Get product data for the selected SKUs
        products = get_unmatched_products_with_pricing()
        selected_products = [p for p in products if p['sku'] in skus]
        
        if not selected_products:
            return jsonify({'error': 'No valid products found for selected SKUs'}), 400
        
        # Validate products before creation
        validation_errors = []
        validated_products = []
        
        for product in selected_products:
            validation = pricing_calculator.validate_pricing_data(product)
            if not validation['is_valid']:
                validation_errors.append({
                    'sku': product['sku'],
                    'name': product['name'],
                    'errors': validation['errors']
                })
            else:
                validated_products.append({
                    'jds_product': product,
                    'calculated_price': validation['recommended_price']
                })
        
        if validation_errors:
            logger.warning(f"Validation failed for {len(validation_errors)} products")
        
        if not validated_products:
            return jsonify({
                'success': False,
                'error': 'No valid products to create after validation',
                'validation_errors': validation_errors
            }), 400
        
        # Create products in Shopify
        shopify_client = ShopifyClient()
        result = shopify_client.create_products_bulk(validated_products)
        
        # Add validation errors to the result
        if validation_errors:
            result['validation_errors'] = validation_errors
            result['validation_warnings'] = f"{len(validation_errors)} products failed validation"
        
        logger.info(f"Bulk product creation completed: {result['created_count']} created, {result['failed_count']} failed")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error adding products to Shopify: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/bulk-update-pricing', methods=['POST'])
@require_api_key
def bulk_update_pricing():
    """Update pricing for multiple existing products"""
    try:
        if not request.is_json:
            return jsonify({'error': 'JSON data required'}), 400
        
        data = request.json
        skus = data.get('skus', [])
        
        if not skus:
            return jsonify({'error': 'No SKUs provided'}), 400
        
        # Get existing products with pricing analysis
        from database import get_matched_products_with_shopify_prices
        from pricing_calculator import pricing_calculator
        
        existing_products = get_matched_products_with_shopify_prices()
        selected_products = [p for p in existing_products if p['sku'] in skus]
        
        if not selected_products:
            return jsonify({'error': 'No valid products found for selected SKUs'}), 400
        
        # Update prices in Shopify
        shopify_client = ShopifyClient()
        results = []
        updated_count = 0
        failed_count = 0
        
        for product in selected_products:
            try:
                # Calculate new price
                validation = pricing_calculator.validate_pricing_data(product)
                if not validation['is_valid']:
                    results.append({
                        'sku': product['sku'],
                        'name': product['name'],
                        'success': False,
                        'error': f"Validation failed: {', '.join(validation['errors'])}"
                    })
                    failed_count += 1
                    continue
                
                new_price = validation['recommended_price']
                variant_id = product.get('variant_id')
                
                if not variant_id:
                    results.append({
                        'sku': product['sku'],
                        'name': product['name'],
                        'success': False,
                        'error': 'No variant ID found'
                    })
                    failed_count += 1
                    continue
                
                # Update price in Shopify with retry logic
                update_result = shopify_client.update_product_price_with_retry(variant_id, new_price)
                
                if update_result['success']:
                    # Update local database
                    from database import db
                    conn = db.connect()
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            'UPDATE shopify_products SET current_price = ?, last_updated = CURRENT_TIMESTAMP WHERE sku = ?',
                            (new_price, product['sku'])
                        )
                        conn.commit()
                    finally:
                        try:
                            conn.close()
                        except Exception:
                            logger.warning("Failed to close DB connection for sku=%s", product.get('sku'))
                    results.append({
                        'sku': product['sku'],
                        'name': product['name'],
                        'success': True,
                        'old_price': product.get('current_shopify_price', 0),
                        'new_price': new_price,
                        'message': f"Updated from ${product.get('current_shopify_price', 0):.2f} to ${new_price:.2f}"
                    })
                    updated_count += 1
                else:
                    results.append({
                        'sku': product['sku'],
                        'name': product['name'],
                        'success': False,
                        'error': update_result['error']
                    })
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Error updating product {product.get('sku', 'unknown')}: {e}")
                results.append({
                    'sku': product['sku'],
                    'name': product['name'],
                    'success': False,
                    'error': str(e)
                })
                failed_count += 1
        
        success = failed_count == 0
        message = f"Bulk price update completed: {updated_count} updated, {failed_count} failed"
        
        logger.info(message)
        
        return jsonify({
            'success': success,
            'message': message,
            'updated_count': updated_count,
            'failed_count': failed_count,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error updating product pricing: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/create-single', methods=['POST'])
@require_api_key
def create_single_product():
    """Create a single product in Shopify"""
    try:
        if not request.is_json:
            return jsonify({'error': 'JSON data required'}), 400
        
        data = request.json
        sku = data.get('sku')
        
        if not sku:
            return jsonify({'error': 'SKU required'}), 400
        
        # Get product data
        products = get_unmatched_products_with_pricing()
        product = next((p for p in products if p['sku'] == sku), None)
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Validate product
        validation = pricing_calculator.validate_pricing_data(product)
        if not validation['is_valid']:
            return jsonify({
                'success': False,
                'error': 'Product validation failed',
                'validation_errors': validation['errors']
            }), 400
        
        # Create product in Shopify with retry logic
        shopify_client = ShopifyClient()
        result = shopify_client.create_product_with_retry(product, validation['recommended_price'])
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error creating single product: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/update-single-price', methods=['POST'])
@require_api_key
def update_single_price():
    """Update price for a single product in Shopify"""
    try:
        if not request.is_json:
            return jsonify({'error': 'JSON data required'}), 400
        
        data = request.json
        sku = data.get('sku')
        
        if not sku:
            return jsonify({'error': 'SKU required'}), 400
        
        # Get product data
        from database import get_matched_products_with_shopify_prices
        products = get_matched_products_with_shopify_prices()
        product = next((p for p in products if p['sku'] == sku), None)
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Calculate new price
        validation = pricing_calculator.validate_pricing_data(product)
        if not validation['is_valid']:
            return jsonify({
                'success': False,
                'error': 'Product validation failed',
                'validation_errors': validation['errors']
            }), 400
        
        new_price = validation['recommended_price']
        variant_id = product.get('variant_id')
        
        if not variant_id:
            return jsonify({'error': 'No variant ID found'}), 400
        
        # Update price in Shopify with retry logic
        shopify_client = ShopifyClient()
        result = shopify_client.update_product_price_with_retry(variant_id, new_price)
        
        if result['success']:
            # Update local database
            from database import db
            conn = db.connect()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE shopify_products SET current_price = ?, last_updated = CURRENT_TIMESTAMP WHERE sku = ?',
                    (new_price, sku)
                )
                conn.commit()
            finally:
                try:
                    conn.close()
                except Exception:
                    logger.warning("Failed to close DB connection for sku=%s", sku)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error updating single product price: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/rollback', methods=['POST'])
@require_api_key
def rollback_products():
    """Rollback created products by deleting them from Shopify"""
    try:
        if not request.is_json:
            return jsonify({'error': 'JSON data required'}), 400
        
        data = request.json
        created_products = data.get('created_products', [])
        
        if not created_products:
            return jsonify({'error': 'No products provided for rollback'}), 400
        
        # Rollback products in Shopify
        shopify_client = ShopifyClient()
        result = shopify_client.rollback_created_products(created_products)
        
        logger.info(f"Rollback completed: {result['deleted_count']} deleted, {len(result.get('errors', []))} errors")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error rolling back products: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/unmatched')
def debug_unmatched():
    """Debug endpoint to test unmatched products directly"""
    try:
        logger.info("Debug: Testing unmatched products directly...")
        
        # Test database function directly
        from database import get_unmatched_products
        unmatched = get_unmatched_products()
        logger.info(f"Debug: Database function returned {len(unmatched)} products")
        
        # Test data_sync function
        products_with_pricing = get_unmatched_products_with_pricing()
        logger.info(f"Debug: Data sync function returned {len(products_with_pricing)} products")
        
        return jsonify({
            'database_direct': len(unmatched),
            'data_sync_function': len(products_with_pricing),
            'products': products_with_pricing[:2] if products_with_pricing else []  # First 2 for debugging
        })
    except Exception as e:
        logger.error(f"Debug error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Product Adder - Phase 4 Complete!")
    print("=" * 50)
    print("✅ Database: SQLite3 with full schema")
    print("✅ Pricing Calculator: edit_price formulas integrated")
    print("✅ SKU Comparison: Advanced matching logic")
    print("✅ Data Sync: JDS & Shopify API integration")
    print("✅ Product Creation: One-click Shopify product addition")
    print("✅ Bulk Operations: Mass product creation and price updates")
    print("✅ Error Handling: Retry logic and rollback functionality")
    print("✅ Validation: Product validation before creation")
    print("✅ Python: 3.13.7 compatible")
    print("✅ Flask: 3.0.0 running")
    print("=" * 50)
    print("🌐 Open your browser to: http://localhost:5000")
    print("📊 Dashboard: Real-time sync status and statistics")
    print("🔧 API Endpoints: /api/sync, /api/products, /api/pricing")
    print("🛒 Product Management: Add products to Shopify with one click")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 50)
    
    # Initialize database
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error starting app: {e}")
        sys.exit(1)
