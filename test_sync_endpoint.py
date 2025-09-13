#!/usr/bin/env python3
"""
Test the sync endpoint to make sure it's working
"""

import requests
import json

print("Testing Sync Endpoint...")
print("=" * 50)

base_url = "http://localhost:5000"

# Test the sync endpoint
print("Testing /api/sync/all...")
try:
    response = requests.post(
        f"{base_url}/api/sync/all",
        headers={'Content-Type': 'application/json'},
        json={'force': True},
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ SUCCESS!")
        print(f"Message: {data.get('message', 'No message')}")
        print(f"JDS Sync: {data.get('jds_sync', {}).get('success', False)}")
        print(f"Shopify Sync: {data.get('shopify_sync', {}).get('success', False)}")
        print(f"JDS Count: {data.get('jds_sync', {}).get('count', 0)}")
        print(f"Shopify Count: {data.get('shopify_sync', {}).get('count', 0)}")
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print("\nTest completed!")

