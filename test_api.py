#!/usr/bin/env python3
"""
Test script to debug API endpoint issues
"""

import requests
import json

print("Testing API Endpoints...")
print("=" * 50)

base_url = "http://localhost:5000"

# Test comparison stats
print("1. Testing /api/comparison/stats...")
response = requests.get(f"{base_url}/api/comparison/stats")
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test unmatched products
print("\n2. Testing /api/products/unmatched...")
response = requests.get(f"{base_url}/api/products/unmatched")
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

# Test matched products
print("\n3. Testing /api/products/matched...")
response = requests.get(f"{base_url}/api/products/matched")
print(f"   Status: {response.status_code}")
print(f"   Response: {response.json()}")

print("\nTest completed!")

