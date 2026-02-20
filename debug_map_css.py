#!/usr/bin/env python
"""Debug map CSS and visibility issues"""
import requests
import re

session = requests.Session()
response = session.get('http://localhost:8000/accounts/login/', timeout=5)
csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)

if csrf_match:
    csrf_token = csrf_match.group(1)
    login_data = {
        'username': 'testuser',
        'password': 'testpass123',
        'csrfmiddlewaretoken': csrf_token
    }
    session.post('http://localhost:8000/accounts/login/', data=login_data, allow_redirects=True, timeout=5)
    map_response = session.get('http://localhost:8000/dashboard/map/', timeout=5)
    
    # Extract map div
    map_div_match = re.search(r'<div[^>]*id="map"[^>]*>', map_response.text)
    if map_div_match:
        print("Map container HTML:")
        print(f"  {map_div_match.group(0)}")
    
    # Check for display:none
    print("\nVisibility check:")
    if 'display: none' in map_response.text:
        print("  ✗ display:none found!")
        lines = map_response.text.split('\n')
        for i, line in enumerate(lines):
            if 'display: none' in line:
                print(f"    Line {i}: {line.strip()[:100]}")
    else:
        print("  ✓ No display:none found")
    
    # Check for map styles
    print("\nMap styling check:")
    if 'map-container' in map_response.text:
        print("  ✓ .map-container class found")
    
    # Extract style block for map
    style_match = re.search(r'<style>(.*?)</style>', map_response.text, re.DOTALL)
    if style_match:
        styles = style_match.group(1)
        if '.map-container' in styles:
            map_style = re.search(r'\.map-container\s*\{([^}]+)\}', styles, re.DOTALL)
            if map_style:
                print("  .map-container styles:")
                for line in map_style.group(1).split(';'):
                    line = line.strip()
                    if line:
                        print(f"    {line}")
        
        if '#map' in styles:
            print("  ✓ #map styles found")
        else:
            print("  ⚠️ #map styles NOT found (might be okay if using .map-container)")
    
    # Check if Leaflet loads correctly
    print("\nLeaflet library check:")
    if 'L.map(' in map_response.text:
        print("  ✓ L.map() call found in page")
        # Find the exact initialization
        init_match = re.search(r'const map = L\.map\([^)]+\)', map_response.text)
        if init_match:
            print(f"  Initialization: {init_match.group(0)}")
