#!/usr/bin/env python
"""Create test oil spill detections for map testing"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from detection.models import OilSpillDetection, SatelliteImage
from django.utils import timezone

# Get a satellite image to associate with detections
sat_image = SatelliteImage.objects.first()

if not sat_image:
    print('No satellite images found in database')
    exit(1)

# Create test detections at different locations in Niger Delta
test_detections = [
    {
        'latitude': 4.8,
        'longitude': 5.2,
        'severity': 'HIGH',
        'confidence': 0.92,
        'area': 25.5,
        'verified': True,
        'name': 'Location 1'
    },
    {
        'latitude': 5.3,
        'longitude': 5.8,
        'severity': 'CRITICAL',
        'confidence': 0.87,
        'area': 42.3,
        'verified': False,
        'name': 'Location 2'
    },
    {
        'latitude': 5.1,
        'longitude': 5.0,
        'severity': 'MEDIUM',
        'confidence': 0.71,
        'area': 12.8,
        'verified': True,
        'name': 'Location 3'
    },
    {
        'latitude': 4.9,
        'longitude': 5.6,
        'severity': 'LOW',
        'confidence': 0.55,
        'area': 5.2,
        'verified': False,
        'name': 'Location 4'
    },
]

print("Creating test detections...\n")

created = 0
for detection_data in test_detections:
    detection = OilSpillDetection.objects.create(
        satellite_image=sat_image,
        location=Point(detection_data['longitude'], detection_data['latitude']),
        severity=detection_data['severity'],
        confidence_score=detection_data['confidence'],
        area_size=detection_data['area'],
        verified=detection_data['verified'],
        detection_date=timezone.now(),
    )
    created += 1
    status = '✓ Verified' if detection_data['verified'] else '○ Unverified'
    print(f"✓ Created {detection_data['severity']:8} detection at ({detection_data['latitude']}, {detection_data['longitude']}) - {status}")

print(f"\n{'='*60}")
print(f"✓ Total test detections created: {created}")
print(f"✓ Total detections in database: {OilSpillDetection.objects.count()}")
print(f"\nNow refresh your map at:")
print(f"  http://localhost:8000/dashboard/map/")
print(f"\nYou should see {created} colored markers on the map!")
