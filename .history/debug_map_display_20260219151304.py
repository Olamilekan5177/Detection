#!/usr/bin/env python
"""Test if the map page loads with Leaflet and check for errors"""
import requests
import re
import json

session = requests.Session()

# Get login page
print("[1/3] Logging in...")
response = session.get('http://localhost:8000/accounts/login/', timeout=5)
csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)

if csrf_match:
    csrf_token = csrf_match.group(1)
    
    # Login
    login_data = {
        'username': 'testuser',
        'password': 'testpass123',
        'csrfmiddlewaretoken': csrf_token
    }
    session.post('http://localhost:8000/accounts/login/', data=login_data, allow_redirects=True, timeout=5)

# Access map
print("[2/3] Accessing map page...")
map_response = session.get('http://localhost:8000/dashboard/map/', timeout=5)
print(f"  Status: {map_response.status_code}")

# Check for Leaflet library
print("\n[3/3] Checking for required libraries and code...")

checks = {
    'Leaflet CSS': 'leaflet.css' in map_response.text,
    'Leaflet JS': 'leaflet.js' in map_response.text,
    'L.map initialization': 'L.map("map"' in map_response.text,
    'initializeMap function': 'function initializeMap' in map_response.text,
    'DOMContentLoaded handler': 'DOMContentLoaded' in map_response.text,
    'OpenStreetMap tile layer': 'tile.openstreetmap.org' in map_response.text,
    'Map container HTML': 'id="map"' in map_response.text,
    'Map container styling': 'map-container' in map_response.text,
}

print("\nLibrary and Code Checks:")
for check, found in checks.items():
    print(f"  {'✓' if found else '✗'} {check}")

# Check for console errors in the code
print("\nChecking for potential issues...")

issues = []

# Check if map container has proper height
if 'height: 700px' not in map_response.text and 'height:700px' not in map_response.text:
    issues.append("⚠️ Map container might not have proper height set")

# Check for defer or async attributes that might delay initialization
if 'defer' in map_response.text or 'async' in map_response.text:
    issues.append("⚠️ Scripts might be deferred/async")

if not issues:
    print("  No obvious issues found")
else:
    for issue in issues:
        print(f"  {issue}")

if all(checks.values()):
    print("\n✓ All required libraries and code present!")
    print("\nTroubleshooting steps:")
    print("1. Open browser console (F12 or Ctrl+Shift+I)")
    print("2. Go to http://localhost:8000/accounts/login/")
    print("3. Log in with: testuser / testpass123")
    print("4. Go to http://localhost:8000/dashboard/map/")
    print("5. Check the 'Console' tab for JavaScript errors")
    print("6. Check the 'Network' tab to see if tile layer is loading")
else:
    print("\n✗ Missing required libraries!")
