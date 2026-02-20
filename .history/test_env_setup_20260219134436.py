#!/usr/bin/env python
"""Test .env file loading"""

import os
from pathlib import Path

print("Testing .env file setup...\n")

# Check if .env exists
if Path(".env").exists():
    print("✓ .env file found")
else:
    print("✗ .env file not found")
    exit(1)

# Try to load with python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ python-dotenv loaded .env file")
except ImportError:
    print("⚠ python-dotenv not installed")
    print("  Install with: pip install python-dotenv")
    exit(1)

# Check for credentials
client_id = os.getenv("SENTINEL_HUB_CLIENT_ID")
client_secret = os.getenv("SENTINEL_HUB_CLIENT_SECRET")

print("\nCredentials Status:")
if client_id:
    print(f"✓ SENTINEL_HUB_CLIENT_ID: {client_id[:10]}***")
else:
    print("✗ SENTINEL_HUB_CLIENT_ID: NOT SET")

if client_secret:
    print(f"✓ SENTINEL_HUB_CLIENT_SECRET: {client_secret[:10]}***")
else:
    print("✗ SENTINEL_HUB_CLIENT_SECRET: NOT SET")

# Test with Sentinel Hub config
print("\nTesting Sentinel Hub Config:")
from detection.sentinel_hub_config import get_sentinel_hub_config

config = get_sentinel_hub_config()

if config.is_configured():
    print("✓ Config loaded from .env")
    print(f"  Client ID: {config.client_id[:10]}***")
    print(f"  Base URL: {config.base_url}")
    
    # Try validation
    print("\nValidating credentials...")
    if config.validate_credentials():
        print("✓ Credentials validated successfully!")
        print("\n🎉 ALL SYSTEMS READY!")
    else:
        print("✗ Credential validation failed")
        print("  Check that credentials are correct")
else:
    print("✗ No credentials loaded")
    print("  Check .env file has SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET")
