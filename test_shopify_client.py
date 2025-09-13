#!/usr/bin/env python3
"""
Test the updated Shopify client directly
"""

import os
from dotenv import load_dotenv
from shopify_client import ShopifyClient

# Load environment variables
load_dotenv()

print("Testing Updated Shopify Client...")
print("=" * 50)

# Create Shopify client
shopify_client = ShopifyClient()

print(f"Store: {shopify_client.store}")
print(f"API Version: {shopify_client.api_version}")
print(f"Access Token present: {bool(shopify_client.access_token)}")

# Test fetch all products
print("\nTesting fetch_all_products...")
try:
    products = shopify_client.fetch_all_products()
    print(f"Products returned: {len(products)}")
    if products:
        print(f"Sample product: {products[0]}")
    else:
        print("No products found")
except Exception as e:
    print(f"Error fetching products: {e}")
    import traceback
    traceback.print_exc()

# Test sync
print("\nTesting sync...")
try:
    result = shopify_client.sync_products()
    print(f"Sync result: {result}")
except Exception as e:
    print(f"Error syncing: {e}")
    import traceback
    traceback.print_exc()

print("\nTest completed!")

