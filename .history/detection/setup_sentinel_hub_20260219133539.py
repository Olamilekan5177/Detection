"""
Sentinel Hub Setup Guide and Credential Configuration

This script helps you set up Sentinel Hub API credentials for the pipeline.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from detection.sentinel_hub_config import setup_sentinel_hub_interactive, get_sentinel_hub_config


def print_banner(title: str):
    """Print formatted banner"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_section(title: str):
    """Print section header"""
    print(f"\n{'─'*70}")
    print(f"  {title}")
    print(f"{'─'*70}")


def setup_guide():
    """Interactive Sentinel Hub setup guide"""
    
    print_banner("SENTINEL HUB SETUP GUIDE")
    
    print("""
This guide will help you:
1. Get Sentinel Hub API credentials
2. Configure them for the oil spill detection pipeline
3. Verify the connection works

WHAT YOU NEED:
- A web browser
- ~5 minutes
- Your Sentinel Hub account (free tier available)
""")
    
    choice = input("\nStart setup? (y/n): ").strip().lower()
    if choice != 'y':
        print("Setup cancelled.")
        return False
    
    # STEP 1: Get credentials
    print_section("STEP 1: Get API Credentials from Sentinel Hub")
    
    print("""
1. Open: https://www.sentinel-hub.com/
2. Click "Sign in" or "Register"
3. Create free account if needed
4. Go to: Dashboard → Settings → Credentials
5. Click "Create OAuth Client"
6. Give it a name like "oil-spill-detection"
7. Copy the CLIENT_ID and CLIENT_SECRET
8. Keep these safe!

Then copy-paste them here...
""")
    
    input("\nPress Enter when you have your credentials ready...")
    
    # STEP 2: Enter and save credentials
    print_section("STEP 2: Enter and Save Credentials")
    
    client_id = input("\n📋 SENTINEL_HUB_CLIENT_ID: ").strip()
    client_secret = input("🔐 SENTINEL_HUB_CLIENT_SECRET: ").strip()
    
    if not client_id or not client_secret:
        print("\n✗ Error: Both CLIENT_ID and CLIENT_SECRET are required")
        return False
    
    # STEP 3: Choose storage method
    print_section("STEP 3: Choose How to Store Credentials")
    
    print("""
You can store credentials in 2 ways:

Option 1: SECURE FILE (Recommended if .gitignore is set up)
- Saves to: sentinel_hub_credentials.json
- File is local, not tracked by git
- More convenient for development
- ⚠️ IMPORTANT: Add to .gitignore!

Option 2: ENVIRONMENT VARIABLES (Most Secure for Production)
- Set in your system or terminal
- Never stored in files
- Better for production/CI-CD
- Requires setting up environment

Which method? (1=File, 2=Environment): """)
    
    method = input().strip()
    
    config = get_sentinel_hub_config()
    
    if method == "1":
        print("\n📝 Saving credentials to file...")
        success = config.save_credentials(client_id, client_secret)
        if not success:
            print("✗ Failed to save credentials")
            return False
        
        print("\n⚠️ IMPORTANT SECURITY STEPS:")
        print("1. Add sentinel_hub_credentials.json to .gitignore")
        print("2. NEVER commit this file to version control")
        print("3. Keep this file secure on your system")
        
    else:  # method == "2"
        print("\n📝 Setting environment variables...")
        print("\n🔧 Windows PowerShell:")
        print(f"  $env:SENTINEL_HUB_CLIENT_ID = '{client_id}'")
        print(f"  $env:SENTINEL_HUB_CLIENT_SECRET = '{client_secret}'")
        print("\n🔧 Linux/Mac Bash:")
        print(f"  export SENTINEL_HUB_CLIENT_ID='{client_id}'")
        print(f"  export SENTINEL_HUB_CLIENT_SECRET='{client_secret}'")
        print("\nOr add to ~/.bashrc or ~/.zshrc for permanent setup")
        
        config.client_id = client_id
        config.client_secret = client_secret
    
    # STEP 4: Validate credentials
    print_section("STEP 4: Validate Credentials")
    
    print("\n🔍 Testing credentials...")
    
    if config.validate_credentials():
        print("✓ SUCCESS! Credentials are valid and working")
        return True
    else:
        print("✗ FAILED: Credentials validation failed")
        print("\nTroubleshooting:")
        print("- Check that you copied CLIENT_ID and SECRET correctly")
        print("- Make sure your account is active at https://www.sentinel-hub.com")
        print("- Try creating a new OAuth Client")
        return False


def quick_test():
    """Test current Sentinel Hub configuration"""
    
    print_banner("SENTINEL HUB CONNECTION TEST")
    
    config = get_sentinel_hub_config()
    
    print("\n📊 Configuration Status:")
    print(f"  Client ID: {'✓ Configured' if config.client_id else '✗ Not configured'}")
    print(f"  Client Secret: {'✓ Configured' if config.client_secret else '✗ Not configured'}")
    print(f"  API Endpoint: {config.base_url}")
    
    if not config.is_configured():
        print("\n✗ Credentials not configured")
        print("   Run: python detect/setup_sentinel_hub.py --setup")
        return False
    
    print("\n🔍 Testing API connection...")
    
    if config.validate_credentials():
        print("✓ SUCCESS! All systems working")
        
        # Try to get an access token
        token = config.get_access_token()
        if token:
            print(f"✓ Access token obtained: {token[:20]}...")
            return True
    else:
        print("✗ FAILED: Could not authenticate with Sentinel Hub")
        print("   Check your credentials")
        return False


def query_example():
    """Show example of querying Sentinel-1 data"""
    
    print_banner("EXAMPLE: QUERY SENTINEL-1 DATA")
    
    config = get_sentinel_hub_config()
    
    if not config.is_configured():
        print("✗ Sentinel Hub not configured")
        return
    
    from detection.sentinel1_pipeline import Sentinel1QueryEngine
    
    print("""
Example: Query Sentinel-1 data for Niger Delta region
Date range: Last 30 days
Pass direction: ASCENDING
""")
    
    from datetime import datetime, timedelta
    
    # Niger Delta coordinates
    bbox = (5.0, 4.0, 7.0, 6.0)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"\n📍 Query Parameters:")
    print(f"  Region: Niger Delta (bbox: {bbox})")
    print(f"  Date Range: {start_date.date()} to {end_date.date()}")
    print(f"  Pass Direction: ASCENDING")
    
    print(f"\n🔍 Executing query...")
    
    query_engine = Sentinel1QueryEngine(config)
    tiles = query_engine.search_tiles(
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        pass_direction="ASCENDING",
        limit=10
    )
    
    if tiles:
        print(f"\n✓ Found {len(tiles)} Sentinel-1 products:")
        for i, tile in enumerate(tiles[:5], 1):
            print(f"\n  {i}. {tile.get('name', 'Unknown')}")
            print(f"     ID: {tile.get('id', 'N/A')}")
            print(f"     Date: {tile.get('acquisition_date', 'N/A')}")
    else:
        print("\n⚠️  No products found (this is OK - queue may be too recent)")


def main():
    """Main entry point"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "--setup":
            success = setup_guide()
            sys.exit(0 if success else 1)
        
        elif command == "--test":
            success = quick_test()
            sys.exit(0 if success else 1)
        
        elif command == "--query":
            query_example()
            sys.exit(0)
        
        elif command == "--help":
            print("""
Sentinel Hub Setup Tool

Usage: python setup_sentinel_hub.py [COMMAND]

Commands:
  --setup    Interactive credential setup
  --test     Test current configuration
  --query    Try example Sentinel-1 query
  --help     Show this help message

Examples:
  python detection/setup_sentinel_hub.py --setup
  python detection/setup_sentinel_hub.py --test
  python detection/setup_sentinel_hub.py --query
""")
            sys.exit(0)
        
        else:
            print(f"Unknown command: {command}")
            print("Use --help for usage information")
            sys.exit(1)
    
    # Default: interactive menu
    print_banner("SENTINEL HUB CONFIGURATION TOOL")
    
    print("""
Choose what to do:
1. Setup credentials
2. Test connection
3. Try example query
0. Exit
""")
    
    choice = input("Select (0-3): ").strip()
    
    if choice == "1":
        setup_guide()
    elif choice == "2":
        quick_test()
    elif choice == "3":
        query_example()
    elif choice != "0":
        print("Invalid selection")


if __name__ == "__main__":
    main()
