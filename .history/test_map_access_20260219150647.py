#!/usr/bin/env python
"""Test if the map interface loads correctly"""
import requests
import re

session = requests.Session()

# Get login page
print("[1/3] Getting login page...")
response = session.get('http://localhost:8000/accounts/login/', timeout=5)
print(f"  Status: {response.status_code}")

# Extract CSRF token
csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
if not csrf_match:
    print("  ERROR: Could not find CSRF token")
    exit(1)

csrf_token = csrf_match.group(1)
print(f"  ✓ CSRF token found")

# Login
print("[2/3] Logging in as testuser...")
login_data = {
    'username': 'testuser',
    'password': 'testpass123',
    'csrfmiddlewaretoken': csrf_token
}
response = session.post('http://localhost:8000/auth/login/', data=login_data, allow_redirects=True, timeout=5)
print(f"  Status: {response.status_code}")
print(f"  Cookies: {len(session.cookies)} set")

# Access map
print("[3/3] Accessing map page...")
map_response = session.get('http://localhost:8000/dashboard/map/', timeout=5)
print(f"  Status: {map_response.status_code}")

# Check for map elements
checks = {
    'map-container': 'map-container' in map_response.text,
    'leaflet': 'L.map' in map_response.text,
    'filters': 'severityFilter' in map_response.text,
    'markers': 'L.marker' in map_response.text,
}

print("\nPage elements:")
for element, found in checks.items():
    print(f"  {'✓' if found else '✗'} {element}")

if all(checks.values()):
    print("\n✓ Map interface IS LOADING CORRECTLY!")
else:
    print("\n✗ Map interface has issues")
    # Show first 1000 chars
    print("\nPage content preview:")
    print(map_response.text[:1000])
