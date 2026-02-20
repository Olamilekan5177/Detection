#!/usr/bin/env python
"""
Quick test to verify Sentinel Hub configuration is working
"""

import os
import sys
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Django setup
PROJECT_ROOT = Path(__file__).parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.append(str(PROJECT_ROOT))

import django
django.setup()

# Test imports
def main():
    # Test 1: Check environment variables
    client_id = os.getenv('SENTINEL_HUB_CLIENT_ID', '')
    client_secret = os.getenv('SENTINEL_HUB_CLIENT_SECRET', '')
    
    if not (client_id and client_secret):
        return False
    
    # Test 2: Check config module
    try:
        from detection.sentinel_hub_config import get_sentinel_hub_config
        config = get_sentinel_hub_config()
        
        if not config.is_configured():
            return False
    except Exception as e:
        return False
    
    # Test 3: Check Sentinel1QueryEngine import
    try:
        from detection.sentinel1_pipeline import Sentinel1QueryEngine
    except Exception as e:
        pass
    
    # Test 4: Check SentinelHubClient import
    try:
        from detection.sentinelhub_integration import SentinelHubClient
    except Exception as e:
        return False
    
    # Test 5: Check process_real_satellite_data.py
    try:
        from scripts.process_real_satellite_data import RealSatelliteDataProcessor
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
