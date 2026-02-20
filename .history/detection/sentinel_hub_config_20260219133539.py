"""
Sentinel Hub Configuration and Credential Management

Handles API credentials for Sentinel Hub and provides authentication.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class SentinelHubConfig:
    """Manage Sentinel Hub API credentials and configuration"""
    
    CONFIG_FILE = "sentinel_hub_credentials.json"
    ENV_PREFIX = "SENTINEL_HUB"
    
    def __init__(self):
        """Initialize credential manager"""
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.base_url = "https://sh.dataspace.copernicus.eu"
        self.auth_url = f"{self.base_url}/oauth"
        self._load_credentials()
    
    def _load_credentials(self) -> None:
        """Load credentials from multiple sources (priority order)"""
        
        # 1. Try environment variables
        self.client_id = os.environ.get(f"{self.ENV_PREFIX}_CLIENT_ID")
        self.client_secret = os.environ.get(f"{self.ENV_PREFIX}_CLIENT_SECRET")
        
        if self.client_id and self.client_secret:
            logger.info("✓ Credentials loaded from environment variables")
            return
        
        # 2. Try credentials file
        if Path(self.CONFIG_FILE).exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    creds = json.load(f)
                    self.client_id = creds.get("client_id")
                    self.client_secret = creds.get("client_secret")
                    logger.info(f"✓ Credentials loaded from {self.CONFIG_FILE}")
                    return
            except Exception as e:
                logger.warning(f"Failed to load credentials file: {e}")
        
        # 3. If nothing found, log warning
        logger.warning("⚠ No Sentinel Hub credentials found")
        logger.warning("  Set SENTINEL_HUB_CLIENT_ID and SENTINEL_HUB_CLIENT_SECRET environment variables")
        logger.warning("  OR create sentinel_hub_credentials.json with client_id and client_secret")
    
    def save_credentials(self, client_id: str, client_secret: str, filename: str = CONFIG_FILE) -> bool:
        """
        Save credentials to file (for setup/configuration).
        
        Args:
            client_id: Sentinel Hub Client ID
            client_secret: Sentinel Hub Client Secret
            filename: Where to save credentials
            
        Returns:
            True if successful
        """
        try:
            creds = {
                "client_id": client_id,
                "client_secret": client_secret,
                "saved_at": datetime.now().isoformat(),
                "api_endpoint": self.base_url
            }
            
            with open(filename, 'w') as f:
                json.dump(creds, f, indent=2)
            
            # Also update instance variables
            self.client_id = client_id
            self.client_secret = client_secret
            
            logger.info(f"✓ Credentials saved to {filename}")
            logger.warning("⚠ Keep sentinel_hub_credentials.json secure - add to .gitignore!")
            
            return True
        except Exception as e:
            logger.error(f"✗ Failed to save credentials: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if credentials are available"""
        return bool(self.client_id and self.client_secret)
    
    def validate_credentials(self) -> bool:
        """
        Validate credentials by attempting authentication.
        
        Returns:
            True if credentials are valid
        """
        if not self.is_configured():
            logger.error("Credentials not configured")
            return False
        
        try:
            import requests
            
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = requests.post(
                f"{self.auth_url}/token",
                data=auth_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✓ Sentinel Hub credentials validated successfully")
                return True
            else:
                logger.error(f"✗ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except ImportError:
            logger.error("requests library required for credential validation")
            return False
        except Exception as e:
            logger.error(f"✗ Validation error: {e}")
            return False
    
    def get_access_token(self) -> Optional[str]:
        """
        Get valid access token for API requests.
        
        Returns:
            Access token or None if authentication fails
        """
        if not self.is_configured():
            logger.error("Credentials not configured - cannot get access token")
            return None
        
        try:
            import requests
            
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = requests.post(
                f"{self.auth_url}/token",
                data=auth_data,
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token")
                logger.debug(f"✓ Access token obtained (expires in {token_data.get('expires_in')}s)")
                return access_token
            else:
                logger.error(f"Failed to get access token: {response.status_code}")
                return None
                
        except ImportError:
            logger.error("requests library required for authentication")
            return None
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return None
    
    def to_dict(self) -> Dict:
        """Get config as dictionary (credentials excluded)"""
        return {
            "configured": self.is_configured(),
            "base_url": self.base_url,
            "auth_url": self.auth_url,
            "client_id": f"{self.client_id[:10]}***" if self.client_id else None
        }


def setup_sentinel_hub_interactive() -> bool:
    """
    Interactive setup for Sentinel Hub credentials.
    
    Returns:
        True if setup successful
    """
    print("\n" + "="*60)
    print("SENTINEL HUB CREDENTIAL SETUP")
    print("="*60)
    
    print("""
To get credentials:
1. Go to https://www.sentinel-hub.com/
2. Sign up or log in
3. Go to Dashboard → Settings → API Credentials
4. Create OAuth Client (for Authentication)
5. Copy CLIENT_ID and CLIENT_SECRET
""")
    
    client_id = input("Enter SENTINEL_HUB_CLIENT_ID: ").strip()
    client_secret = input("Enter SENTINEL_HUB_CLIENT_SECRET: ").strip()
    
    if not client_id or not client_secret:
        print("✗ Both client ID and secret are required")
        return False
    
    config = SentinelHubConfig()
    
    # Save to file or environment
    save_method = input("Save to file (f) or environment variable (e)? [f/e]: ").strip().lower()
    
    if save_method == 'e':
        print("\nAdd these to your environment:")
        print(f"  export SENTINEL_HUB_CLIENT_ID='{client_id}'")
        print(f"  export SENTINEL_HUB_CLIENT_SECRET='{client_secret}'")
        print("\nOr in Windows PowerShell:")
        print(f"  $env:SENTINEL_HUB_CLIENT_ID='{client_id}'")
        print(f"  $env:SENTINEL_HUB_CLIENT_SECRET='{client_secret}'")
        return True
    else:
        success = config.save_credentials(client_id, client_secret)
        if success:
            print("\n✓ Credentials saved to sentinel_hub_credentials.json")
            print("⚠ Add sentinel_hub_credentials.json to .gitignore!")
            print("\nVerifying credentials...")
            
            if config.validate_credentials():
                print("✓ Credentials validated successfully!")
                return True
            else:
                print("✗ Credentials validation failed - check your credentials")
                return False
        return False


# Export convenience function
def get_sentinel_hub_config() -> SentinelHubConfig:
    """Get or create Sentinel Hub configuration"""
    return SentinelHubConfig()
