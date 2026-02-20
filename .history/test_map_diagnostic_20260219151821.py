#!/usr/bin/env python
"""Comprehensive diagnostic test for the map"""
import requests
import re
from urllib.parse import urlparse

session = requests.Session()

# Authenticate
print("[1] Authenticating...")
response = session.get('http://localhost:8000/accounts/login/', timeout=5)
csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)

if not csrf_match:
    print("✗ Could not authenticate")
    exit(1)

csrf_token = csrf_match.group(1)
login_data = {
    'username': 'testuser',
    'password': 'testpass123',
    'csrfmiddlewaretoken': csrf_token
}
session.post('http://localhost:8000/accounts/login/', data=login_data, allow_redirects=True, timeout=5)
print("✓ Authenticated")

# Get map page
print("\n[2] Loading map page...")
map_response = session.get('http://localhost:8000/dashboard/map/', timeout=5)
print(f"✓ Map page status: {map_response.status_code}")

# Check for required components
print("\n[3] Checking page components...")

checks = {
    'Page header': 'page-header' in map_response.text,
    'Map controls': 'map-controls' in map_response.text,
    'Map container (#map)': 'id="map"' in map_response.text,
    'Leaflet library loaded': 'leaflet' in map_response.text.lower(),
    'Map initialization code': 'L.map(' in map_response.text,
    'OSM tile layer': 'openstreetmap.org' in map_response.text,
    'Severity colors': 'severityColors' in map_response.text,
    'Filter controls': 'id="severityFilter"' in map_response.text,
}

for component, present in checks.items():
    print(f"  {'✓' if present else '✗'} {component}")

# Check CSS dimensions
print("\n[4] Checking CSS dimensions...")

# Look for #map height
height_match = re.search(r'#map\s*\{[^}]*height:\s*(\d+)px', map_response.text)
width_match = re.search(r'#map\s*\{[^}]*width:\s*(\d+|100%)', map_response.text)

if height_match:
    print(f"  ✓ Map height: {height_match.group(1)}px")
else:
    print("  ⚠️ Map height not explicitly set")

if width_match:
    print(f"  ✓ Map width: {width_match.group(1)}")
else:
    print("  ⚠️ Map width not explicitly set")

# Check for DOM ready handler
print("\n[5] Checking initialization handlers...")

init_checks = {
    'DOMContentLoaded handler': 'DOMContentLoaded' in map_response.text,
    'document.readyState check': 'document.readyState' in map_response.text or 'initializeMap()' in map_response.text,
    'applyFilters function': 'window.applyFilters' in map_response.text,
    'loadDetections function': 'async function loadDetections' in map_response.text,
}

for check, present in init_checks.items():
    print(f"  {'✓' if present else '✗'} {check}")

# Summary
print("\n" + "="*50)
if all(checks.values()) and all(init_checks.values()):
    print("✓ MAP FULLY CONFIGURED")
    print("\nThe issue is likely:")
    print("  1. Browser not loading the page (clear cache)")
    print("  2. JavaScript not executing (check browser console F12)")
    print("  3. Network blocked for OSM tiles (firewall/proxy issue)")
    print("  4. Local Leaflet/CSS not loading from CDN")
    print("\nTroubleshooting steps:")
    print("  1. Open browser DevTools (F12 or Ctrl+Shift+I)")
    print("  2. Go to Console tab")
    print("  3. Check for red error messages")
    print("  4. Go to Network tab")
    print("  5. Look for failed requests (red X)")
    print("  6. Try accessing: http://localhost:8000/dashboard/map/")
else:
    print("✗ MAP CONFIGURATION INCOMPLETE")
    missing = [k for k, v in {**checks, **init_checks}.items() if not v]
    print(f"\nMissing components:")
    for item in missing:
        print(f"  - {item}")
