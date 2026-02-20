"""
Sentinel Hub Integration Module

Provides live access to Sentinel satellite imagery for oil spill detection.
Uses Sentinel Hub Data Space (new Copernicus) API.
Get free account at: https://www.sentinel-hub.com/ or https://dataspace.copernicus.eu/
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np
from PIL import Image
import requests

logger = logging.getLogger(__name__)


class SentinelHubClient:
    """Client for Sentinel Hub Data Space API interactions."""
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize Sentinel Hub client.
        
        Args:
            client_id: Sentinel Hub OAuth2 client ID
            client_secret: Sentinel Hub OAuth2 client secret
        
        Get these from: https://apps.sentinel-hub.com/dashboard/ or
                       https://dataspace.copernicus.eu/
        """
        self.client_id = client_id
        self.client_secret = client_secret
        # Use new Sentinel Data Space (Copernicus)
        self.base_url = "https://sh.dataspace.copernicus.eu"
        self.token = None
        self.token_expires = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Sentinel Hub Data Space and get OAuth2 token."""
        auth_url = f"{self.base_url}/oauth/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(auth_url, data=auth_data, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self.token_expires = datetime.now() + timedelta(seconds=expires_in)
            logger.info("✓ Authenticated with Sentinel Hub Data Space")
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to authenticate with Sentinel Hub Data Space: {e}")
            raise
    
    def _check_token(self):
        """Check and refresh token if needed."""
        if not self.token or datetime.now() >= self.token_expires:
            self._authenticate()
    
    def _get_headers(self) -> Dict:
        """Get authorization headers."""
        self._check_token()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def query_imagery(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        max_cloud_coverage: float = 20,
        resolution: int = 10
    ) -> List[Dict]:
        """
        Query Sentinel-2 imagery for a bounding box and date range.
        
        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat) bounding box
            start_date: Start date in format YYYY-MM-DD
            end_date: End date in format YYYY-MM-DD
            max_cloud_coverage: Maximum cloud coverage percentage (0-100)
            resolution: Output resolution in meters (10, 20, 60)
        
        Returns:
            List of available imagery records with download URLs
        """
        catalog_url = f"{self.base_url}/api/v1/catalog/search/json"
        
        # Build search query
        query = {
            "bbox": [bbox[0], bbox[1], bbox[2], bbox[3]],
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "collections": ["sentinel-2-l2a"],
            "filter": {
                "op": "and",
                "args": [
                    {
                        "op": "lte",
                        "args": [{"property": "eo:cloud_cover"}, max_cloud_coverage]
                    }
                ]
            },
            "limit": 50,
            "next": 0
        }
        
        try:
            headers = self._get_headers()
            response = requests.post(catalog_url, json=query, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            features = data.get("features", [])
            logger.info(f"✓ Found {len(features)} Sentinel-2 images")
            
            return [
                {
                    "id": feature["id"],
                    "acquired": feature["properties"].get("datetime", ""),
                    "cloud_cover": feature["properties"].get("eo:cloud_cover", 100),
                    "bbox": bbox,
                    "geometry": feature.get("geometry", {})
                }
                for feature in features
            ]
        
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to query imagery: {e}")
            return []
    
    def download_imagery(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        output_path: str,
        max_cloud_coverage: float = 20
    ) -> Optional[str]:
        """
        Download the best available Sentinel-2 image for a region and date range.
        
        Args:
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            output_path: Path to save the image
            max_cloud_coverage: Maximum acceptable cloud cover
        
        Returns:
            Path to downloaded image or None if failed
        """
        # Query for available imagery
        results = self.query_imagery(bbox, start_date, end_date, max_cloud_coverage)
        
        if not results:
            logger.warning("No suitable imagery available for download")
            return None
        
        # Use the image with lowest cloud coverage
        best_image = min(results, key=lambda x: x["cloud_cover"])
        
        # Build request for actual image data
        wcs_url = f"{self.base_url}/wcs"
        
        wcs_params = {
            "service": "WCS",
            "version": "1.1.1",
            "request": "GetCoverage",
            "coverageId": f"SENTINEL2_L2A:{best_image['id']}",
            "format": "image/tiff",
            "bbox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "crs": "http://www.opengis.net/gml/srs/epsg.xml#4326",
            "width": "512",
            "height": "512"
        }
        
        try:
            headers = self._get_headers()
            response = requests.get(wcs_url, params=wcs_params, headers=headers, stream=True)
            response.raise_for_status()
            
            # Save image
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"✓ Downloaded image to {output_path}")
            logger.info(f"  Date: {best_image['acquired']}")
            logger.info(f"  Cloud coverage: {best_image['cloud_cover']}%")
            
            return output_path
        
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Failed to download imagery: {e}")
            return None


def get_sentinel_client() -> Optional[SentinelHubClient]:
    """
    Get Sentinel Hub client from environment variables.
    
    Set these environment variables:
    - SENTINEL_CLIENT_ID: Your Sentinel Hub OAuth2 client ID
    - SENTINEL_CLIENT_SECRET: Your Sentinel Hub OAuth2 client secret
    
    Free account at: https://www.sentinel-hub.com/
    """
    client_id = os.getenv("SENTINEL_CLIENT_ID")
    client_secret = os.getenv("SENTINEL_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logger.warning(
            "⚠ Sentinel Hub credentials not configured.\n"
            "Set environment variables:\n"
            "  SENTINEL_CLIENT_ID=<your-id>\n"
            "  SENTINEL_CLIENT_SECRET=<your-secret>\n"
            "Get free account at: https://www.sentinel-hub.com/"
        )
        return None
    
    return SentinelHubClient(client_id, client_secret)


def process_sentinel_image(image_path: str) -> Optional[np.ndarray]:
    """
    Process Sentinel-2 image for oil spill detection.
    
    Converts multi-band to RGB/normalized for ML model input.
    
    Args:
        image_path: Path to Sentinel-2 GeoTIFF image
    
    Returns:
        Processed image array or None if failed
    """
    try:
        img = Image.open(image_path)
        
        # Convert to numpy array and normalize
        img_array = np.array(img, dtype=np.float32)
        
        if len(img_array.shape) == 3:
            # Multi-band: select RGB channels (typical: B4=3, B3=2, B2=1 in TIFF)
            if img_array.shape[2] >= 3:
                # Use first 3 channels as RGB
                img_rgb = img_array[:, :, :3]
            else:
                # Grayscale, replicate across channels
                img_rgb = np.stack([img_array[:, :, 0]] * 3, axis=2)
        else:
            # Single band grayscale
            img_rgb = np.stack([img_array] * 3, axis=2)
        
        # Normalize to [0, 1]
        max_val = np.max(img_rgb)
        if max_val > 0:
            img_rgb = img_rgb / max_val
        
        return img_rgb
    
    except Exception as e:
        logger.error(f"✗ Failed to process image: {e}")
        return None
