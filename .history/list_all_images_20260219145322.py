#!/usr/bin/env python
"""Check all satellite images in database"""
import os
import sys
import django
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(str(PROJECT_ROOT))
django.setup()

from detection.models import SatelliteImage

imgs = SatelliteImage.objects.all().order_by('-id')
print(f'Total Satellite Images: {imgs.count()}\n')
print('Latest Images:')
print('='*85)
for i, img in enumerate(imgs[:15], 1):
    print(f'{i:2}. {img.image_id:40} {img.source:15} {img.acquisition_date.strftime("%m-%d %H:%M")}')
print('='*85)
