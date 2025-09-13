#!/usr/bin/env python3
"""
Quick test to check if Shopify access token has read_products permission
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Testing Shopify Access Token Permissions...")
print("=" * 50)

store = os.getenv('SHOPIFY_STORE')
access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')

if not store or not access_token:
    print("❌ Missing Shopify credentials")
    exit(1)

# Test with REST API (simpler than GraphQL)
rest_url = f"https://{store}/admin/api/2023-10/products.json"
headers = {
    'X-Shopify-Access-Token': access_token,
    'Content-Type': 'application/json'
}

print(f"Testing: {rest_url}")
print(f"Token: {access_token[:10]}...")

try:
    response = requests.get(rest_url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        print(f"✅ SUCCESS! Found {len(products)} products")
        if products:
            print(f"Sample product: {products[0].get('title', 'No title')}")
            print("🎉 Your access token has the correct permissions!")
        else:
            print("⚠️  No products found, but permissions are correct")
    elif response.status_code == 403:
        print("❌ ACCESS DENIED - Token still missing read_products scope")
        print("Response:", response.text)
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print("\nTest completed!")

