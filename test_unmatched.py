#!/usr/bin/env python3
"""
Test script to debug unmatched products issue
"""

from database import get_unmatched_products, get_sku_comparison_stats
from data_sync import get_unmatched_products_with_pricing

print("Testing Unmatched Products...")
print("=" * 50)

# Test database function directly
print("1. Testing get_unmatched_products() from database...")
unmatched = get_unmatched_products()
print(f"   Found {len(unmatched)} unmatched products")
for product in unmatched:
    print(f"   - {product.sku}: {product.name}")

print("\n2. Testing get_sku_comparison_stats()...")
stats = get_sku_comparison_stats()
print(f"   JDS Total: {stats['jds_total']}")
print(f"   Shopify Total: {stats['shopify_total']}")
print(f"   Unmatched: {stats['unmatched']}")

print("\n3. Testing get_unmatched_products_with_pricing()...")
unmatched_with_pricing = get_unmatched_products_with_pricing()
print(f"   Found {len(unmatched_with_pricing)} products with pricing")
for product in unmatched_with_pricing:
    print(f"   - {product['sku']}: {product['name']} (Price: ${product.get('recommended_price', 'N/A')})")

print("\nTest completed!")

