#!/usr/bin/env python3
"""
Debug script to check module imports
"""

import sys
import os

print("Python Path Debug...")
print("=" * 50)
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}...")

# Test imports
print("\nTesting imports...")
try:
    from database import get_unmatched_products, get_sku_comparison_stats
    print("✅ database imports successful")
except Exception as e:
    print(f"❌ database import failed: {e}")

try:
    from data_sync import get_unmatched_products_with_pricing
    print("✅ data_sync imports successful")
except Exception as e:
    print(f"❌ data_sync import failed: {e}")

# Test functions
print("\nTesting functions...")
try:
    stats = get_sku_comparison_stats()
    print(f"✅ get_sku_comparison_stats: {stats}")
except Exception as e:
    print(f"❌ get_sku_comparison_stats failed: {e}")

try:
    products = get_unmatched_products_with_pricing()
    print(f"✅ get_unmatched_products_with_pricing: {len(products)} products")
except Exception as e:
    print(f"❌ get_unmatched_products_with_pricing failed: {e}")

print("\nDebug completed!")

