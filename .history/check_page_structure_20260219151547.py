#!/usr/bin/env python
"""Check the page structure"""
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
    
    print('=== Page Structure Check ===\n')
    
    # Check components
    checks = {
        'Has sidebar': 'sidebar' in map_response.text,
        'Has main-content': 'main-content' in map_response.text,
        'Has page-title': 'page-title' in map_response.text,
        'Has filter-card': 'filter-card' in map_response.text,
        'Has map-container': 'map-container' in map_response.text,
        'Has content wrapper': 'color: #1f2937' in map_response.text,
        'Has Leaflet': 'L.map' in map_response.text,
    }
    
    for check, result in checks.items():
        print(f"{'✓' if result else '✗'} {check}")
    
    # Check main-content div
    print('\n=== Main Content Check ===\n')
    if 'main-content' in map_response.text:
        # Extract main-content div
        match = re.search(r'<div class="main-content"[^>]*>(.*?)</div>\s*</body>', map_response.text, re.DOTALL)
        if match:
            content = match.group(1)
            print(f"Main content length: {len(content)} characters")
            print(f"First 200 chars: {content[:200]}...")
        else:
            print("Could not extract main-content")
    
    # Check for visibility issues
    print('\n=== CSS Visibility Check ===\n')
    
    issues = []
    if 'display: none' in map_response.text:
        issues.append('display: none found')
    if 'visibility: hidden' in map_response.text:
        issues.append('visibility: hidden found')
    if 'opacity: 0' in map_response.text:
        issues.append('opacity: 0 found')
    
    if issues:
        for issue in issues:
            print(f"⚠️ {issue}")
    else:
        print("No visibility issues detected")
    
    print(f"\nPage loads OK: {map_response.status_code == 200}")
    print(f"Page size: {len(map_response.text)} bytes")
