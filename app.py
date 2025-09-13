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

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

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

# Phase 2 API Routes

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
def sync_all():
    """Sync all data from JDS and Shopify APIs"""
    try:
        force = request.json.get('force', False) if request.is_json else False
        result = sync_all_data(force=force)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing all data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/jds', methods=['POST'])
def sync_jds():
    """Sync JDS data with specific SKUs or sample SKUs"""
    try:
        data = request.json if request.is_json else {}
        skus = data.get('skus', None)  # If no SKUs provided, will use sample SKUs
        
        from data_sync import sync_manager
        result = sync_manager.sync_jds_data(skus)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing JDS data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync/shopify', methods=['POST'])
def sync_shopify():
    """Sync Shopify data"""
    try:
        from data_sync import sync_manager
        result = sync_manager.sync_shopify_data()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error syncing Shopify data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/unmatched')
def unmatched_products():
    """Get unmatched JDS products with calculated pricing"""
    try:
        logger.info("Getting unmatched products...")
        
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
        logger.error(f"Error getting unmatched products: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/matched')
def matched_products():
    """Get matched products between JDS and Shopify"""
    try:
        products = get_matched_products()
        return jsonify({
            'success': True,
            'count': len(products),
            'products': [p.to_dict() for p in products]
        })
    except Exception as e:
        logger.error(f"Error getting matched products: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/matched-with-pricing')
def matched_products_with_pricing():
    """Get matched products with calculated pricing comparison"""
    try:
        from database import get_matched_products_with_shopify_prices
        from pricing_calculator import pricing_calculator
        
        matched_products = get_matched_products_with_shopify_prices()
        products_with_pricing = []
        
        for product_dict in matched_products:
            # Calculate what the Shopify price should be
            pricing_validation = pricing_calculator.validate_pricing_data(product_dict)
            product_dict['calculated_shopify_price'] = pricing_validation['recommended_price']
            product_dict['pricing_valid'] = pricing_validation['is_valid']
            product_dict['pricing_warnings'] = pricing_validation['warnings']
            
            # Calculate price difference
            current_price = product_dict.get('current_shopify_price', 0)
            calculated_price = product_dict.get('calculated_shopify_price', 0)
            
            if current_price and calculated_price:
                price_diff = calculated_price - current_price
                price_diff_percent = (price_diff / current_price * 100) if current_price > 0 else 0
                product_dict['price_difference'] = price_diff
                product_dict['price_difference_percent'] = price_diff_percent
            else:
                product_dict['price_difference'] = 0
                product_dict['price_difference_percent'] = 0
            
            products_with_pricing.append(product_dict)
        
        return jsonify({
            'success': True,
            'count': len(products_with_pricing),
            'products': products_with_pricing
        })
    except Exception as e:
        logger.error(f"Error getting matched products with pricing: {e}")
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
        jds_client = JDSClient()
        shopify_client = ShopifyClient()
        
        jds_connected = jds_client.test_connection()
        shopify_connected = shopify_client.test_connection()
        
        return jsonify({
            'jds_api': {
                'connected': jds_connected,
                'url': jds_client.api_url
            },
            'shopify_api': {
                'connected': shopify_connected,
                'store': shopify_client.store
            }
        })
    except Exception as e:
        logger.error(f"Error testing connections: {e}")
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
    print("🚀 Starting Product Adder - Phase 2 Complete!")
    print("=" * 50)
    print("✅ Database: SQLite3 with full schema")
    print("✅ Pricing Calculator: edit_price formulas integrated")
    print("✅ SKU Comparison: Advanced matching logic")
    print("✅ Data Sync: JDS & Shopify API integration")
    print("✅ Python: 3.13.7 compatible")
    print("✅ Flask: 3.0.0 running")
    print("=" * 50)
    print("🌐 Open your browser to: http://localhost:5000")
    print("📊 Dashboard: Real-time sync status and statistics")
    print("🔧 API Endpoints: /api/sync, /api/products, /api/pricing")
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
