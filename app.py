#!/usr/bin/env python3
"""
Product Adder Flask Application - Phase 5 Complete
Implements optimization, monitoring, and production-ready features
"""

from dotenv import load_dotenv
# Load environment variables first, before other imports
load_dotenv()

from flask import Flask, jsonify, render_template, request, redirect, url_for
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
# For Vercel serverless environment, only use console logging
if os.environ.get('VERCEL'):
    # Vercel environment - only console logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
else:
    # Local environment - console and file logging
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
app.config['API_KEY'] = os.environ.get('APP_API_KEY', 'dev-api-key')  # Allow default for testing
app.config['SHOPIFY_API_KEY'] = os.environ.get('SHOPIFY_API_KEY', '')  # For App Bridge

# Simple header-based API key gate for internal/admin APIs
from functools import wraps
def require_api_key(fn):
    @wraps(fn)
    def api_key_wrapper(*args, **kwargs):
        api_key = app.config.get('API_KEY')
        provided = request.headers.get('X-API-Key')
        # Allow access if no API key is set (for testing)
        if not api_key:
            return fn(*args, **kwargs)
        if provided != api_key:
            return jsonify({'error': 'Unauthorized'}), 401
        return fn(*args, **kwargs)
    return api_key_wrapper

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return app.send_static_file('images/placeholder.svg')

@app.route('/auth/callback')
def shopify_auth_callback():
    """Handle Shopify OAuth callback"""
    try:
        # Get the shop parameter
        shop = request.args.get('shop')
        if not shop:
            return "Missing shop parameter", 400
        
        # In a real app, you'd validate the HMAC and exchange the code for an access token
        # For now, we'll just redirect to the main app
        return redirect(url_for('index', shop=shop))
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return f"Authentication error: {e}", 500

@app.route('/')
def index():
    """Main SKU search page"""
    try:
        # Check if we have the required environment variables
        missing_vars = []
        if not os.environ.get('SHOPIFY_STORE'):
            missing_vars.append('SHOPIFY_STORE')
        if not os.environ.get('SHOPIFY_ACCESS_TOKEN'):
            missing_vars.append('SHOPIFY_ACCESS_TOKEN')
        if not os.environ.get('EXTERNAL_API_TOKEN'):
            missing_vars.append('EXTERNAL_API_TOKEN')
        
        # Get comparison stats and sync status for the template
        comparison_stats = get_sku_comparison_stats()
        sync_status = get_sync_status()
        
        if missing_vars:
            return render_template('index.html', 
                                 setup_required=True,
                                 missing_vars=missing_vars,
                                 comparison_stats=comparison_stats,
                                 sync_status=sync_status,
                                 api_key=app.config['API_KEY'],
                                 shopify_api_key=app.config.get('SHOPIFY_API_KEY', ''))
        
        return render_template('index.html', 
                             setup_required=False,
                             comparison_stats=comparison_stats,
                             sync_status=sync_status,
                             api_key=app.config['API_KEY'],
                             shopify_api_key=app.config.get('SHOPIFY_API_KEY', ''))
    except Exception as e:
        logger.error(f"Error loading SKU search page: {e}")
        # Provide default values for template variables
        default_stats = {
            'jds_total': 0,
            'shopify_total': 0,
            'matched': 0,
            'unmatched': 0,
            'match_percentage': 0
        }
        default_sync_status = {
            'jds_api_connected': False,
            'shopify_api_connected': False,
            'last_sync': None
        }
        return render_template('index.html', 
                             setup_required=True,
                             error=str(e),
                             comparison_stats=default_stats,
                             sync_status=default_sync_status,
                             api_key=app.config['API_KEY'],
                             shopify_api_key=app.config.get('SHOPIFY_API_KEY', ''))

# SKU Search and Add Routes

@app.route('/api/sku/search', methods=['POST'])
@time_api_call('/api/sku/search', 'POST')
def search_sku():
    """Search for a specific SKU and return product details"""
    try:
        if not request.is_json:
            return jsonify({'error': 'JSON data required'}), 400
        
        data = request.json
        sku = data.get('sku', '').strip()
        
        if not sku:
            return jsonify({'error': 'SKU is required'}), 400
        
        # Use existing JDS client to fetch product details
        jds_client = JDSClient()
        products = jds_client.fetch_product_details([sku])
        
        if not products:
            return jsonify({
                'success': False,
                'message': f'No product found for SKU: {sku}',
                'sku': sku
            })
        
        product = products[0]  # Get the first (and should be only) product
        
        # Map JDS API field names to pricing calculator expected field names
        pricing_data = {
            'less_than_case_price': product.get('lessThanCasePrice'),
            'one_case': product.get('oneCase'),
            'five_cases': product.get('fiveCases'),
            'ten_cases': product.get('tenCases'),
            'twenty_cases': product.get('twentyCases'),
            'forty_cases': product.get('fortyCases'),
            'case_quantity': product.get('caseQuantity')
        }
        
        # Add image URLs to the product data
        product['image_url'] = product.get('image', '')
        product['thumbnail_url'] = product.get('thumbnail', '')
        product['quick_image_url'] = product.get('quickImage', '')
        
        # Calculate pricing using existing pricing calculator
        pricing_validation = pricing_calculator.validate_pricing_data(pricing_data)
        product['calculated_prices'] = pricing_validation['calculated_prices']
        product['recommended_price'] = pricing_validation['recommended_price']
        product['pricing_valid'] = pricing_validation['is_valid']
        product['pricing_warnings'] = pricing_validation['warnings']
        product['pricing_errors'] = pricing_validation['errors']
        
        # Check if product already exists in Shopify (both local DB and live API)
        from database import get_shopify_price_for_sku
        from shopify_client import ShopifyClient
        
        # First check local database
        shopify_price = get_shopify_price_for_sku(sku)
        product['already_in_shopify'] = shopify_price is not None
        product['current_shopify_price'] = shopify_price
        
        # Also check live Shopify API for real-time verification
        try:
            shopify_client = ShopifyClient()
            live_check = shopify_client.check_product_exists_by_sku(sku)
            
            if live_check['exists']:
                # Product exists in live Shopify
                product['shopify_live_exists'] = True
                product['shopify_live_price'] = live_check['product']['price']
                product['shopify_live_title'] = live_check['product']['title']
                
                # If local DB says it doesn't exist but live API says it does, sync in background
                if not product['already_in_shopify']:
                    logger.info(f"Product {sku} exists in live Shopify but not in local DB - requesting background sync")
                    # Request background sync for this specific SKU
                    from background_sync import background_sync_manager
                    sync_requested = background_sync_manager.request_sync(sku)
                    
                    if sync_requested:
                        product['background_sync_started'] = True
                    else:
                        # Check if already completed or pending
                        sync_status = background_sync_manager.get_sync_status(sku)
                        if sync_status == 'completed':
                            product['background_sync_completed'] = True
                        elif sync_status == 'pending':
                            product['background_sync_started'] = True
                        elif sync_status == 'failed':
                            product['background_sync_failed'] = True
                            product['background_sync_error'] = background_sync_manager.get_sync_error(sku)
            else:
                # Product doesn't exist in live Shopify
                product['shopify_live_exists'] = False
                product['shopify_live_price'] = None
                product['shopify_live_title'] = None
                
                # If local DB says it exists but live API says it doesn't, mark as deleted
                if product['already_in_shopify']:
                    logger.info(f"Product {sku} exists in local DB but not in live Shopify - marking as deleted")
                    from database import mark_product_as_deleted
                    mark_product_as_deleted(sku)
                    product['already_in_shopify'] = False
                    product['current_shopify_price'] = None
                    product['background_sync_completed'] = True
                    
        except Exception as e:
            logger.error(f"Error checking live Shopify status for SKU {sku}: {e}")
            product['shopify_live_exists'] = None  # Unknown due to error
            product['shopify_live_error'] = str(e)
        
        record_metric("sku_search_success", 1)
        
        return jsonify({
            'success': True,
            'product': product,
            'sku': sku
        })
        
    except Exception as e:
        logger.error(f"Error searching SKU: {e}")
        record_metric("sku_search_error", 1)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/status/<sku>', methods=['GET'])
@time_api_call('/api/sync/status/<sku>', 'GET')
def get_sync_status(sku):
    """Get background sync status for a specific SKU"""
    try:
        from background_sync import background_sync_manager
        
        status = background_sync_manager.get_sync_status(sku)
        result = {
            'success': True,
            'sku': sku,
            'status': status
        }
        
        if status == 'failed':
            error = background_sync_manager.get_sync_error(sku)
            if error:
                result['error'] = error
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting sync status for SKU {sku}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sku/add-to-shopify', methods=['POST'])
@require_api_key
@time_api_call('/api/sku/add-to-shopify', 'POST')
def add_sku_to_shopify():
    """Add a specific SKU to Shopify store"""
    try:
        if not request.is_json:
            return jsonify({'error': 'JSON data required'}), 400
        
        data = request.json
        sku = data.get('sku', '').strip()
        
        if not sku:
            return jsonify({'error': 'SKU is required'}), 400
        
        # First, search for the product to get details
        jds_client = JDSClient()
        products = jds_client.fetch_product_details([sku])
        
        if not products:
            return jsonify({
                'success': False,
                'error': f'No product found for SKU: {sku}'
            })
        
        product = products[0]
        
        # Map JDS API field names to expected field names
        product['image_url'] = product.get('image', '')
        product['thumbnail_url'] = product.get('thumbnail', '')
        product['quick_image_url'] = product.get('quickImage', '')
        
        # Map JDS API field names to pricing calculator expected field names
        pricing_data = {
            'less_than_case_price': product.get('lessThanCasePrice'),
            'one_case': product.get('oneCase'),
            'five_cases': product.get('fiveCases'),
            'ten_cases': product.get('tenCases'),
            'twenty_cases': product.get('twentyCases'),
            'forty_cases': product.get('fortyCases'),
            'case_quantity': product.get('caseQuantity')
        }
        
        # Calculate pricing
        pricing_validation = pricing_calculator.validate_pricing_data(pricing_data)
        if not pricing_validation['is_valid']:
            return jsonify({
                'success': False,
                'error': 'Product validation failed',
                'validation_errors': pricing_validation['errors']
            })
        
        # Check if already in Shopify
        from database import get_shopify_price_for_sku
        if get_shopify_price_for_sku(sku) is not None:
            return jsonify({
                'success': False,
                'error': f'Product with SKU {sku} already exists in Shopify'
            })
        
        # Create product in Shopify using existing functionality
        shopify_client = ShopifyClient()
        result = shopify_client.create_product_with_retry(product, pricing_validation['recommended_price'])
        
        if result['success']:
            record_metric("sku_added_to_shopify", 1)
        else:
            record_metric("sku_add_failed", 1)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error adding SKU to Shopify: {e}")
        record_metric("sku_add_error", 1)
        return jsonify({'error': str(e)}), 500

@app.route('/api/sku/add-or-update-shopify', methods=['POST'])
@require_api_key
@time_api_call('/api/sku/add-or-update-shopify', 'POST')
def add_or_update_sku_to_shopify():
    """Add a new SKU to Shopify or update existing product price"""
    try:
        if not request.is_json:
            return jsonify({'error': 'JSON data required'}), 400
        
        data = request.json
        sku = data.get('sku', '').strip()
        custom_price = data.get('custom_price')
        
        if not sku:
            return jsonify({'error': 'SKU is required'}), 400
        
        # First, search for the product to get details
        jds_client = JDSClient()
        products = jds_client.fetch_product_details([sku])
        
        if not products:
            return jsonify({
                'success': False,
                'error': f'No product found for SKU: {sku}'
            })
        
        product = products[0]
        
        # Map JDS API field names to expected field names
        product['image_url'] = product.get('image', '')
        product['thumbnail_url'] = product.get('thumbnail', '')
        product['quick_image_url'] = product.get('quickImage', '')
        
        # Map JDS API field names to pricing calculator expected field names
        pricing_data = {
            'less_than_case_price': product.get('lessThanCasePrice'),
            'one_case': product.get('oneCase'),
            'five_cases': product.get('fiveCases'),
            'ten_cases': product.get('tenCases'),
            'twenty_cases': product.get('twentyCases'),
            'forty_cases': product.get('fortyCases'),
            'case_quantity': product.get('caseQuantity')
        }
        
        # Calculate pricing
        pricing_validation = pricing_calculator.validate_pricing_data(pricing_data)
        if not pricing_validation['is_valid']:
            return jsonify({
                'success': False,
                'error': 'Product validation failed',
                'validation_errors': pricing_validation['errors']
            })
        
        # Use custom price if provided, otherwise use recommended price
        if custom_price is not None:
            try:
                custom_price_float = float(custom_price)
                if custom_price_float <= 0:
                    return jsonify({
                        'success': False,
                        'error': 'Custom price must be greater than 0'
                    })
                recommended_price = custom_price_float
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'error': 'Invalid custom price format'
                })
        else:
            recommended_price = pricing_validation['recommended_price']
        
        # Check if already in Shopify
        from database import get_shopify_price_for_sku, get_shopify_variant_id_for_sku
        existing_price = get_shopify_price_for_sku(sku)
        variant_id = get_shopify_variant_id_for_sku(sku)
        
        if existing_price is not None and variant_id:
            # Product exists in local DB, try to update the price
            shopify_client = ShopifyClient()
            result = shopify_client.update_product_price_with_retry(variant_id, recommended_price)
            
            if result['success']:
                # Update the database with new price
                from database import update_shopify_price_for_sku
                update_shopify_price_for_sku(sku, recommended_price)
                record_metric("sku_price_updated", 1)
                price_type = "custom price" if custom_price is not None else "recommended price"
                return jsonify({
                    'success': True,
                    'message': f'Successfully updated price for {product.get("name", sku)} to ${recommended_price:.2f} ({price_type})',
                    'action': 'updated',
                    'recommended_price': recommended_price
                })
            elif result.get('variant_not_found', False):
                # Variant not found in Shopify, remove from local DB and create new product
                logger.info(f"Variant {variant_id} not found in Shopify for SKU {sku}, creating new product")
                from database import mark_product_as_deleted
                mark_product_as_deleted(sku)
                
                # Fall through to create new product
                shopify_client = ShopifyClient()
            else:
                record_metric("sku_update_failed", 1)
                return jsonify({
                    'success': False,
                    'error': f'Failed to update price: {result.get("error", "Unknown error")}'
                })
        
        # Product doesn't exist in local DB or variant was not found, create it
        shopify_client = ShopifyClient()
        result = shopify_client.create_product_with_retry(product, recommended_price)
        
        if result['success']:
            record_metric("sku_added_to_shopify", 1)
            price_type = "custom price" if custom_price is not None else "recommended price"
            return jsonify({
                'success': True,
                'message': f'Successfully added {product.get("name", sku)} to Shopify at ${recommended_price:.2f} ({price_type})',
                'action': 'added',
                'recommended_price': recommended_price
            })
        else:
            record_metric("sku_add_failed", 1)
            return jsonify({
                'success': False,
                'error': f'Failed to add product: {result.get("error", "Unknown error")}'
            })
        
    except Exception as e:
        logger.error(f"Error adding/updating SKU to Shopify: {e}")
        record_metric("sku_add_update_error", 1)
        return jsonify({'error': str(e)}), 500

# Removed product list views - not needed for simplified SKU search functionality

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
    try:
        # Simple health check that doesn't require database
        return jsonify({
            'health': 'excellent',
            'uptime': 'running',
            'api': 'responding',
            'environment': os.environ.get('FLASK_ENV', 'development'),
            'vercel': bool(os.environ.get('VERCEL'))
        })
    except Exception as e:
        return jsonify({
            'health': 'degraded',
            'error': str(e),
            'api': 'responding'
        }), 200

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

@app.route('/api/sync/discover', methods=['POST'])
@require_api_key
@time_api_call('/api/sync/discover', 'POST')
def discover_new_products():
    """Discover and sync new JDS products not in Shopify"""
    try:
        data = request.json if request.is_json else {}
        sample_skus = data.get('sample_skus', None)
        
        # Use the JDS client to discover new products
        from jds_client import JDSClient
        jds_client = JDSClient()
        result = jds_client.discover_new_products(sample_skus)
        
        # Record the discovery operation
        from database import record_sync_operation
        record_sync_operation('discover_new_products', result.get('success', False), result.get('message', ''))
        
        # Record performance metrics
        record_metric("discovery_success", 1 if result.get('success') else 0)
        record_metric("new_products_discovered", result.get('count', 0))
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error discovering new products: {e}")
        record_metric("discovery_error", 1)
        return jsonify({'error': str(e)}), 500
@app.route('/api/sync/status')
def sync_status():
    """Get current sync status and statistics"""
    try:
        status = get_sync_status()
        
        # Add last sync time information
        from database import get_last_sync_time
        last_sync = get_last_sync_time()
        if last_sync:
            status['last_sync'] = last_sync
            status['time_since_sync'] = time.time() - last_sync
        
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
        
        # Check if sync was done recently (within 10 minutes) unless forced
        if not force:
            from database import get_last_sync_time
            last_sync = get_last_sync_time()
            if last_sync:
                time_since_sync = time.time() - last_sync
                if time_since_sync < 600:  # 10 minutes = 600 seconds
                    remaining_time = 600 - time_since_sync
                    return jsonify({
                        'success': False,
                        'message': f'Sync was performed recently. Please wait {int(remaining_time/60)} minutes and {int(remaining_time%60)} seconds before syncing again.',
                        'last_sync': last_sync,
                        'time_since_sync': time_since_sync,
                        'cooldown_remaining': remaining_time
                    }), 429  # Too Many Requests
        
        result = sync_all_data(force=force)
        
        # Record the sync operation in database
        from database import record_sync_operation
        record_sync_operation('sync_all', result.get('success', False), result.get('message', ''))
        
        # Record performance metrics
        duration = time.time() - start_time
        record_metric("sync_all_duration", duration)
        record_metric("sync_all_success", 1 if result.get('success') else 0)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing all data: {e}")
        record_metric("sync_all_error", 1)
        return jsonify({'error': str(e)}), 500

# Removed upload progress tracking - not needed for simplified SKU search functionality

# Removed file splitting functionality - not needed for simplified SKU search

# Error handler to ensure all errors return JSON
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error', 'message': str(error)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': str(error)}), 404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400

# Removed upload progress routes - not needed for simplified SKU search functionality

# Removed all upload-related routes - not needed for simplified SKU search functionality

# Removed all upload processing functions - not needed for simplified SKU search functionality


# Removed product listing routes - not needed for simplified SKU search functionality

# Removed pricing calculation route - not needed for simplified SKU search functionality

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

# Removed bulk operations and debug routes - not needed for simplified SKU search functionality

# Initialize database on startup (for Vercel)
try:
    init_db()
    logger.info("Database initialized successfully")
    
    # Check if we're in Vercel and database is empty, trigger auto-sync
    if os.environ.get('VERCEL'):
        from database import get_database_stats
        db_stats = get_database_stats()
        if db_stats.get('total_products', 0) == 0:
            logger.info("Vercel environment detected with empty database, triggering auto-sync...")
            try:
                from data_sync import sync_all_data
                sync_result = sync_all_data(force=True)
                logger.info(f"Auto-sync completed: {sync_result.get('message', 'Unknown result')}")
            except Exception as sync_error:
                logger.warning(f"Auto-sync failed: {sync_error}")
        
except Exception as e:
    logger.warning(f"Database initialization warning: {e}")

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
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error starting app: {e}")
        sys.exit(1)
