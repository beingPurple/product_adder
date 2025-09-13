#!/usr/bin/env python3
"""
Test script to debug JDS client issues
"""

import os
from dotenv import load_dotenv
from jds_client import JDSClient

# Load environment variables
load_dotenv()

print("Testing JDS Client...")
print("=" * 50)

# Create JDS client
jds_client = JDSClient()

print(f"API URL: {jds_client.api_url}")
print(f"API Token present: {bool(jds_client.api_token)}")
print(f"API Token (first 10 chars): {jds_client.api_token[:10] if jds_client.api_token else 'None'}...")

# Test connection
print("\nTesting connection...")
connected = jds_client.test_connection()
print(f"Connection test: {'PASSED' if connected else 'FAILED'}")

# Test fetch_all_skus
print("\nTesting fetch_all_skus...")
skus = jds_client.fetch_all_skus()
print(f"SKUs returned: {len(skus)}")
print(f"Sample SKUs: {skus[:5]}")

# Test sync with sample SKUs
print("\nTesting sync with sample SKUs...")
result = jds_client.sync_products(skus[:3])  # Test with first 3 SKUs
print(f"Sync result: {result}")

print("\nTest completed!")

