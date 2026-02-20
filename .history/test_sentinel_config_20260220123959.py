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
    logger.info("Testing Sentinel Hub configuration...")
    
    # Test 1: Check environment variables
    logger.info("\n[1] Checking environment variables...")
    client_id = os.getenv('SENTINEL_HUB_CLIENT_ID', '')
    client_secret = os.getenv('SENTINEL_HUB_CLIENT_SECRET', '')
    
    if client_id and client_secret:
        logger.info(f"✓ SENTINEL_HUB_CLIENT_ID: {client_id[:20]}...")
        logger.info(f"✓ SENTINEL_HUB_CLIENT_SECRET: set")
    else:
        logger.error("✗ Sentinel Hub credentials not found in environment")
        return False
    
    # Test 2: Check config module
    logger.info("\n[2] Testing SentinelHubConfig...")
    try:
        from detection.sentinel_hub_config import get_sentinel_hub_config
        config = get_sentinel_hub_config()
        
        if config.is_configured():
            logger.info("✓ Sentinel Hub config loaded successfully")
        else:
            logger.error("✗ Config not properly configured")
            return False
    except Exception as e:
        logger.error(f"✗ Failed to load config: {e}")
        return False
    
    # Test 3: Check Sentinel1QueryEngine import
    logger.info("\n[3] Testing Sentinel1QueryEngine import...")
    try:
        from detection.sentinel1_pipeline import Sentinel1QueryEngine
        logger.info("✓ Sentinel1QueryEngine imported successfully")
    except Exception as e:
        logger.warning(f"⚠ Sentinel1QueryEngine import failed: {e}")
        logger.warning("  This is OK - system will fall back to SentinelHubClient")
    
    # Test 4: Check SentinelHubClient import
    logger.info("\n[4] Testing SentinelHubClient import...")
    try:
        from detection.sentinelhub_integration import SentinelHubClient
        logger.info("✓ SentinelHubClient imported successfully")
    except Exception as e:
        logger.warning(f"⚠ SentinelHubClient import failed: {e}")
        return False
    
    # Test 5: Check process_real_satellite_data.py
    logger.info("\n[5] Testing process_real_satellite_data.py imports...")
    try:
        from scripts.process_real_satellite_data import RealSatelliteDataProcessor
        logger.info("✓ RealSatelliteDataProcessor imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import processor: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    logger.info("\n" + "="*70)
    logger.info("✓ All configuration tests passed!")
    logger.info("System is ready to download Sentinel-1 data!")
    logger.info("="*70)
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
