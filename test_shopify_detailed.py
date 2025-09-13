#!/usr/bin/env python3
"""
Test Shopify API with detailed error reporting
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing Shopify API with Detailed Error Reporting...")
print("=" * 50)

store = os.getenv('SHOPIFY_STORE')
access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
api_version = '2023-10'

print(f"Store: {store}")
print(f"API Version: {api_version}")
print(f"Access Token: {access_token[:10]}...")

# Test different API versions and parameters
test_cases = [
    {
        'name': '2023-10 with limit only',
        'url': f"https://{store}/admin/api/2023-10/products.json",
        'params': {'limit': 10}
    },
    {
        'name': '2023-10 with no params',
        'url': f"https://{store}/admin/api/2023-10/products.json",
        'params': {}
    },
    {
        'name': '2023-07 with limit only',
        'url': f"https://{store}/admin/api/2023-07/products.json",
        'params': {'limit': 10}
    },
    {
        'name': '2023-04 with limit only',
        'url': f"https://{store}/admin/api/2023-04/products.json",
        'params': {'limit': 10}
    }
]

headers = {
    'X-Shopify-Access-Token': access_token,
    'Content-Type': 'application/json'
}

for test_case in test_cases:
    print(f"\n--- {test_case['name']} ---")
    try:
        response = requests.get(test_case['url'], params=test_case['params'], headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', [])
            print(f"✅ SUCCESS! Found {len(products)} products")
            if products:
                print(f"Sample: {products[0].get('title', 'No title')}")
            break  # Found working version
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

print("\nTest completed!")

