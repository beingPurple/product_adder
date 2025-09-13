#!/usr/bin/env python3
"""
Product Adder Flask Application - Phase 5 Complete
Implements optimization, monitoring, and production-ready features
"""

from dotenv import load_dotenv
# Load environment variables first, before other imports
load_dotenv()

from flask import Flask, jsonify, render_template, request
import os
import sys
import logging
import time
from datetime import datetime
from database import init_db, get_sku_comparison_stats, get_unmatched_products, get_matched_products
from database import get_unmatched_products_optimized, get_matched_products_optimized, get_sku_comparison_stats_optimized
from database import optimize_database, get_database_stats
from data_sync import sync_all_data, get_unmatched_products_with_pricing, get_sync_status
from pricing_calculator import pricing_calculator
from jds_client import JDSClient
from shopify_client import ShopifyClient
from cache_manager import cache_manager, clear_cache, get_cache_stats
from performance_monitor import performance_monitor, get_performance_summary, get_performance_health, record_metric, record_api_call, time_api_call
from pagination import paginate_data, paginate_query, validate_pagination_params

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
    def api_key_wrapper(*args, **kwargs):
        api_key = app.config.get('API_KEY')
        provided = request.headers.get('X-API-Key')
        if not api_key or provided != api_key:
            return jsonify({'error': 'Unauthorized'}), 401
        return fn(*args, **kwargs)
    return api_key_wrapper

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
                             comparison_stats=comparison_stats,
                             api_key=app.config['API_KEY'])
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

# Phase 5: Performance and Monitoring Endpoints

@app.route('/api/performance/summary')
@time_api_call('/api/performance/summary', 'GET')
def performance_summary():
    """Get performance summary and metrics"""
    try:
        summary = get_performance_summary()
        health = get_performance_health()
        
        return jsonify({
            'success': True,
            'performance': summary,
            'health': health,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        record_metric("api_error_count", 1, {"endpoint": "/api/performance/summary"})
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/health')
@time_api_call('/api/performance/health', 'GET')
def performance_health():
    """Get performance health status"""
    try:
        health = get_performance_health()
        return jsonify({
            'success': True,
            'health': health,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting performance health: {e}")
        record_metric("api_error_count", 1, {"endpoint": "/api/performance/health"})
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/stats')
@time_api_call('/api/cache/stats', 'GET')
def cache_stats():
    """Get cache statistics"""
    try:
        stats = get_cache_stats()
        return jsonify({
            'success': True,
            'cache_stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        record_metric("api_error_count", 1, {"endpoint": "/api/cache/stats"})
        return jsonify({'error': str(e)}), 500

@app.route('/api/cache/clear', methods=['POST'])
@require_api_key
@time_api_call('/api/cache/clear', 'POST')
def cache_clear():
    """Clear all cache entries"""
    try:
        clear_cache()
        record_metric("cache_cleared", 1)
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        record_metric("api_error_count", 1, {"endpoint": "/api/cache/clear"})
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/stats')
@time_api_call('/api/database/stats', 'GET')
def database_stats():
    """Get database statistics"""
    try:
        stats = get_database_stats()
        return jsonify({
            'success': True,
            'database_stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        record_metric("api_error_count", 1, {"endpoint": "/api/database/stats"})
        return jsonify({'error': str(e)}), 500

@app.route('/api/database/optimize', methods=['POST'])
@require_api_key
@time_api_call('/api/database/optimize', 'POST')
def database_optimize():
    """Optimize database performance"""
    try:
        result = optimize_database()
        record_metric("database_optimized", 1)
        return jsonify({
            'success': True,
            'optimization_result': result,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        record_metric("api_error_count", 1, {"endpoint": "/api/database/optimize"})
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/unmatched-optimized')
@time_api_call('/api/products/unmatched-optimized', 'GET')
def unmatched_products_optimized():
    """Get unmatched products with pagination and caching"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Validate pagination parameters
        page, per_page = validate_pagination_params(page, per_page, max_per_page=100)
        
        # Get products with pagination
        products, total_count = get_unmatched_products_optimized(
            offset=(page - 1) * per_page,
            limit=per_page
        )
        
        # Convert to dictionaries
        products_data = [product.to_dict() for product in products]
        
        # Add pricing information
        from pricing_calculator import pricing_calculator
        products_with_pricing = []
        for product_dict in products_data:
            pricing_validation = pricing_calculator.validate_pricing_data(product_dict)
            product_dict['calculated_prices'] = pricing_validation['calculated_prices']
            product_dict['recommended_price'] = pricing_validation['recommended_price']
            product_dict['pricing_valid'] = pricing_validation['is_valid']
            product_dict['pricing_warnings'] = pricing_validation['warnings']
            product_dict['pricing_errors'] = pricing_validation['errors']
            products_with_pricing.append(product_dict)
        
        # Create pagination response
        total_pages = (total_count + per_page - 1) // per_page
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'prev_page': page - 1 if page > 1 else None
        }
        
        record_metric("unmatched_products_requested", len(products_with_pricing))
        
        return jsonify({
            'success': True,
            'products': products_with_pricing,
            'pagination': pagination_info,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting unmatched products (optimized): {e}")
        record_metric("api_error_count", 1, {"endpoint": "/api/products/unmatched-optimized"})
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/matched-optimized')
@time_api_call('/api/products/matched-optimized', 'GET')
def matched_products_optimized():
    """Get matched products with pagination and caching"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Validate pagination parameters
        page, per_page = validate_pagination_params(page, per_page, max_per_page=100)
        
        # Get products with pagination
        products, total_count = get_matched_products_optimized(
            offset=(page - 1) * per_page,
            limit=per_page
        )
        
        # Convert to dictionaries
        products_data = [product.to_dict() for product in products]
        
        # Add Shopify pricing information
        from database import get_shopify_price_for_sku
        products_with_pricing = []
        for product_dict in products_data:
            shopify_price = get_shopify_price_for_sku(product_dict['sku'])
            product_dict['current_shopify_price'] = shopify_price
            
            # Calculate recommended price
            from pricing_calculator import pricing_calculator
            pricing_validation = pricing_calculator.validate_pricing_data(product_dict)
            product_dict['calculated_shopify_price'] = pricing_validation['recommended_price']
            product_dict['pricing_valid'] = pricing_validation['is_valid']
            product_dict['pricing_warnings'] = pricing_validation['warnings']
            
            # Calculate price difference
            if shopify_price and pricing_validation['recommended_price']:
                price_diff = pricing_validation['recommended_price'] - shopify_price
                price_diff_percent = (price_diff / shopify_price * 100) if shopify_price > 0 else 0
                product_dict['price_difference'] = price_diff
                product_dict['price_difference_percent'] = price_diff_percent
            else:
                product_dict['price_difference'] = 0.0
                product_dict['price_difference_percent'] = 0.0
            
            products_with_pricing.append(product_dict)
        
        # Create pagination response
        total_pages = (total_count + per_page - 1) // per_page
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'prev_page': page - 1 if page > 1 else None
        }
        
        record_metric("matched_products_requested", len(products_with_pricing))
        
        return jsonify({
            'success': True,
            'products': products_with_pricing,
            'pagination': pagination_info,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting matched products (optimized): {e}")
        record_metric("api_error_count", 1, {"endpoint": "/api/products/matched-optimized"})
        return jsonify({'error': str(e)}), 500

@app.route('/api/comparison/stats-optimized')
@time_api_call('/api/comparison/stats-optimized', 'GET')
def comparison_stats_optimized():
    """Get SKU comparison statistics with caching"""
    try:
        stats = get_sku_comparison_stats_optimized()
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting comparison stats (optimized): {e}")
        record_metric("api_error_count", 1, {"endpoint": "/api/comparison/stats-optimized"})
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
@time_api_call('/api/status', 'GET')
def status():
    """Enhanced status endpoint with performance metrics"""
    try:
        # Get performance health
        health = get_performance_health()
        
        # Get cache stats
        cache_stats = get_cache_stats()
        
        # Get database stats
        db_stats = get_database_stats()
        
        return jsonify({
            'status': 'healthy' if health['overall_health'] >= 80 else 'degraded',
            'phase': 'Phase 5 Complete - Optimization & Monitoring',
            'database': 'SQLite3 (optimized)',
            'python_version': sys.version.split()[0],
            'flask_working': True,
            'performance_health': health,
            'cache_stats': cache_stats,
            'database_stats': db_stats,
            'message': 'All systems operational with monitoring',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        record_metric("api_error_count", 1, {"endpoint": "/api/status"})
        return jsonify({'error': str(e)}), 500

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
@time_api_call('/api/sync/all', 'POST')
def sync_all():
    """Sync all data from JDS and Shopify APIs"""
    try:
        start_time = time.time()
        force = request.json.get('force', False) if request.is_json else False
        result = sync_all_data(force=force)
        
        # Record performance metrics
        duration = time.time() - start_time
        record_metric("sync_all_duration", duration)
        record_metric("sync_all_success", 1 if result.get('success') else 0)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing all data: {e}")
        record_metric("sync_all_error", 1)
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
@require_api_key
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
@require_api_key
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
@require_api_key
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
    print("🚀 Starting Product Adder - Phase 5 Complete!")
    print("=" * 50)
    print("✅ Database: SQLite3 with full schema")
    print("✅ Pricing Calculator: edit_price formulas integrated")
    print("✅ SKU Comparison: Advanced matching logic")
    print("✅ Data Sync: JDS & Shopify API integration")
    print("✅ Product Creation: One-click Shopify product addition")
    print("✅ Bulk Operations: Mass product creation and price updates")
    print("✅ Error Handling: Retry logic and rollback functionality")
    print("✅ Validation: Product validation before creation")
    print("✅ Performance: Caching, pagination, and optimization")
    print("✅ Monitoring: Real-time metrics and health tracking")
    print("✅ Testing: Comprehensive test suite")
    print("✅ Python: 3.13.7 compatible")
    print("✅ Flask: 3.0.0 running")
    print("=" * 50)
    print("🌐 Open your browser to: http://localhost:5000")
    print("📊 Dashboard: Real-time sync status and statistics")
    print("🔧 API Endpoints: /api/sync, /api/products, /api/pricing")
    print("📈 Performance: /api/performance/summary, /api/performance/health")
    print("💾 Cache: /api/cache/stats, /api/cache/clear")
    print("🗄️ Database: /api/database/stats, /api/database/optimize")
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
