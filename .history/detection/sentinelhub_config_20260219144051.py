"""
Sentinel Hub Configuration Helper

Loads Sentinel Hub credentials from environment variables and provides
a configuration object for easy initialization.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SentinelHubConfig:
    """Configuration for Sentinel Hub client."""
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize Sentinel Hub configuration.
        
        Args:
            client_id: Sentinel Hub OAuth2 client ID (defaults to env var)
            client_secret: Sentinel Hub OAuth2 client secret (defaults to env var)
        """
        self.client_id = client_id or os.getenv('SENTINEL_HUB_CLIENT_ID', '')
        self.client_secret = client_secret or os.getenv('SENTINEL_HUB_CLIENT_SECRET', '')
    
    def is_configured(self) -> bool:
        """Check if Sentinel Hub credentials are configured."""
        return bool(self.client_id and self.client_secret)
    
    def get_client_id(self) -> str:
        """Get client ID."""
        return self.client_id
    
    def get_client_secret(self) -> str:
        """Get client secret."""
        return self.client_secret


def get_sentinel_hub_config() -> SentinelHubConfig:
    """
    Get Sentinel Hub configuration from environment variables.
    
    Returns:
        SentinelHubConfig instance
    """
    return SentinelHubConfig()


def check_sentinelhub_credentials() -> bool:
    """
    Check if Sentinel Hub credentials are properly configured.
    
    Returns:
        True if configured, False otherwise
    """
    config = get_sentinel_hub_config()
    
    if not config.is_configured():
        logger.error("Sentinel Hub credentials not configured!")
        logger.error("Please set the following environment variables:")
        logger.error("  - SENTINEL_HUB_CLIENT_ID")
        logger.error("  - SENTINEL_HUB_CLIENT_SECRET")
        logger.error("Get these from: https://apps.sentinel-hub.com/dashboard/")
        return False
    
    logger.info("✓ Sentinel Hub credentials configured")
    return True
