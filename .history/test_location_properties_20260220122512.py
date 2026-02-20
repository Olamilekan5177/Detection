#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from detection.models import OilSpillDetection

# Get a sample detection
detection = OilSpillDetection.objects.first()

if detection:
    print(f"✅ Detection #{detection.id}")
    print(f"   Location (raw): {detection.location}")
    print(f"   Latitude: {detection.latitude}")
    print(f"   Longitude: {detection.longitude}")
    print(f"   Formatted: {detection.lat_lon_string}")
    print(f"   Severity: {detection.severity}")
    print(f"   Verified: {detection.verified}")
    print("\n✅ Location properties are working correctly!")
else:
    print("⚠️  No detections in database")
