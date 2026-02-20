"""
Real Satellite Data Integration - Multiple Sources

This module provides access to real satellite imagery from multiple sources:
1. Sentinel Hub (if available)
2. NOAA GOES satellites (always available, free)
3. NASA MODIS (always available, free)

No synthetic data - always using actual satellite imagery.
"""

import os
import logging
import requests
from typing import Optional, Tuple, Dict
from datetime import datetime
import numpy as np
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)


class NOAASatelliteData:
    """Access real NOAA satellite imagery (GOES-18, GOES-17)."""
    
    @staticmethod
    def get_goes_image(
        region: str = "CONUS",
        band: str = "13",
        latest: bool = True
    ) -> Optional[bytes]:
        """
        Download real NOAA GOES satellite image.
        
        Args:
            region: Geographic region (CONUS, Mesoscale, FullDisk, Puerto Rico, Hawaii)
            band: Band number (1-16, band 13 is clean IR)
            latest: Get latest image
        
        Returns:
            Image bytes or None if failed
        
        Free public data from NOAA:
        https://www.ncei.noaa.gov/products/satellite-imagery
        """
        try:
            # NOAA public GOES API endpoint
            base_url = "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/SECTOR"
            
            # Map region to NOAA path
            region_map = {
                "CONUS": "CONUS",
                "Mesoscale": "MESOSCALE",
                "Gulf": "MESOSCALE",
                "Atlantic": "CONUS"
            }
            noaa_region = region_map.get(region, "CONUS")
            
            # Construct URL for latest available image
            # NOAA updates every 15 minutes
            url = f"{base_url}/{noaa_region}/GEOCOLOR/latest.jpg"
            
            logger.info(f"Fetching NOAA GOES satellite image: {url}")
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info("✓ Successfully retrieved NOAA GOES satellite image")
                return response.content
            else:
                logger.warning(f"NOAA returned status {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Failed to fetch NOAA GOES data: {e}")
            return None
    
    @staticmethod
    def save_goes_image(region: str, output_path: str) -> Optional[str]:
        """Download and save NOAA GOES real satellite image."""
        image_bytes = NOAASatelliteData.get_goes_image(region)
        
        if not image_bytes:
            return None
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Convert JPG to TIF for consistency with other sources
            img = Image.open(BytesIO(image_bytes))
            img = img.convert('RGB')
            
            tif_path = output_path.replace('.jpg', '.tif')
            img.save(tif_path, 'TIFF')
            
            logger.info(f"✓ Saved NOAA GOES image to {tif_path}")
            return tif_path
        
        except Exception as e:
            logger.error(f"Failed to save NOAA image: {e}")
            return None


class NASAModisData:
    """Access real NASA MODIS satellite imagery."""
    
    @staticmethod
    def get_modis_image(
        latitude: float,
        longitude: float,
        days_back: int = 1,
        dim: int = 400
    ) -> Optional[bytes]:
        """
        Download real NASA MODIS satellite image for location.
        
        Args:
            latitude: Target latitude
            longitude: Target longitude
            days_back: How many days back to search
            dim: Dimension in km (default 400km)
        
        Returns:
            Image bytes or None if failed
        
        Free public data from NASA:
        https://worldview.earthdata.nasa.gov/
        """
        try:
            # NASA MODIS Web Service (no API key required)
            url = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
            
            # Get date (days back)
            from datetime import datetime, timedelta
            date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            params = {
                "REQUEST": "GetSnapshot",
                "LAYERS": "MODIS_Aqua_CorrectedReflectance_TrueColor",
                "CRS": "EPSG:4326",
                "BBOX": f"{longitude-1},{latitude-1},{longitude+1},{latitude+1}",
                "FORMAT": "image/jpeg",
                "WIDTH": 512,
                "HEIGHT": 512,
                "TIME": date
            }
            
            logger.info(f"Fetching NASA MODIS image for ({latitude}, {longitude})")
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                logger.info("✓ Successfully retrieved NASA MODIS satellite image")
                return response.content
            else:
                logger.warning(f"NASA MODIS returned status {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Failed to fetch NASA MODIS data: {e}")
            return None
    
    @staticmethod
    def save_modis_image(
        latitude: float,
        longitude: float,
        output_path: str,
        days_back: int = 1
    ) -> Optional[str]:
        """Download and save NASA MODIS real satellite image."""
        image_bytes = NASAModisData.get_modis_image(latitude, longitude, days_back)
        
        if not image_bytes:
            return None
        
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Convert JPG to TIF for consistency
            img = Image.open(BytesIO(image_bytes))
            img = img.convert('RGB')
            
            tif_path = output_path.replace('.jpg', '.tif')
            img.save(tif_path, 'TIFF')
            
            logger.info(f"✓ Saved NASA MODIS image to {tif_path}")
            return tif_path
        
        except Exception as e:
            logger.error(f"Failed to save MODIS image: {e}")
            return None


class RealSatelliteDataManager:
    """
    Unified interface for real satellite data from multiple sources.
    Automatically fallback through sources for reliability.
    """
    
    # Source priority (try in order)
    SOURCES = ['sentinel-hub', 'noaa-goes', 'nasa-modis']
    
    @staticmethod
    def download_for_region(
        region_name: str,
        bbox: Tuple[float, float, float, float],
        output_path: str,
        source: str = 'auto'
    ) -> Optional[str]:
        """
        Download real satellite image for region, trying multiple sources.
        
        Args:
            region_name: Name of region (Gulf of Mexico, Mediterranean, etc)
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
            output_path: Path to save image
            source: 'auto', 'sentinel-hub', 'noaa-goes', 'nasa-modis'
        
        Returns:
            Path to saved image or None if all sources failed
        """
        
        if source == 'auto':
            sources = RealSatelliteDataManager.SOURCES
        else:
            sources = [source]
        
        for source_name in sources:
            logger.info(f"\nAttempting {source_name}...")
            
            if source_name == 'sentinel-hub':
                result = RealSatelliteDataManager._download_sentinel(bbox, output_path)
                if result:
                    return result
            
            elif source_name == 'noaa-goes':
                result = RealSatelliteDataManager._download_noaa(region_name, output_path)
                if result:
                    return result
            
            elif source_name == 'nasa-modis':
                result = RealSatelliteDataManager._download_modis(bbox, output_path)
                if result:
                    return result
        
        logger.error("✗ All satellite data sources failed")
        return None
    
    @staticmethod
    def _download_sentinel(bbox: Tuple[float, float, float, float], output_path: str) -> Optional[str]:
        """Try to download from Sentinel Hub."""
        try:
            from detection.sentinelhub_integration import get_sentinel_client
            
            client = get_sentinel_client()
            if not client:
                logger.warning("Sentinel Hub not configured")
                return None
            
            from datetime import datetime, timedelta
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
            
            results = client.query_imagery(
                bbox=bbox,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                max_cloud_coverage=30
            )
            
            if not results:
                logger.warning("No Sentinel imagery available")
                return None
            
            best = min(results, key=lambda x: x['cloud_cover'])
            return client.download_imagery(
                bbox=bbox,
                start_date=best['acquired'][:10],
                end_date=best['acquired'][:10],
                output_path=output_path
            )
        
        except Exception as e:
            logger.warning(f"Sentinel Hub failed: {e}")
            return None
    
    @staticmethod
    def _download_noaa(region_name: str, output_path: str) -> Optional[str]:
        """Try to download from NOAA GOES."""
        try:
            region_map = {
                'Gulf of Mexico': 'Mesoscale',
                'Mediterranean': 'FullDisk',
                'Gulf': 'Mesoscale',
                'Atlantic': 'CONUS'
            }
            noaa_region = region_map.get(region_name, 'CONUS')
            
            return NOAASatelliteData.save_goes_image(noaa_region, output_path)
        
        except Exception as e:
            logger.warning(f"NOAA GOES failed: {e}")
            return None
    
    @staticmethod
    def _download_modis(bbox: Tuple[float, float, float, float], output_path: str) -> Optional[str]:
        """Try to download from NASA MODIS."""
        try:
            # Use center of bbox
            center_lon = (bbox[0] + bbox[2]) / 2
            center_lat = (bbox[1] + bbox[3]) / 2
            
            return NASAModisData.save_modis_image(center_lat, center_lon, output_path)
        
        except Exception as e:
            logger.warning(f"NASA MODIS failed: {e}")
            return None
    
    @staticmethod
    def get_source_info(source: str) -> Dict:
        """Get information about a data source."""
        info = {
            'sentinel-hub': {
                'name': 'Sentinel-2 (ESA)',
                'resolution': '10m',
                'latency': '5 days',
                'cost': 'Free',
                'requires_auth': True,
                'url': 'https://www.sentinel-hub.com/'
            },
            'noaa-goes': {
                'name': 'NOAA GOES-18 (NOAA)',
                'resolution': '500m-2km',
                'latency': '15 minutes',
                'cost': 'Free',
                'requires_auth': False,
                'url': 'https://www.ncei.noaa.gov/products/satellite-imagery'
            },
            'nasa-modis': {
                'name': 'NASA MODIS (NASA)',
                'resolution': '250m-1km',
                'latency': '1-2 days',
                'cost': 'Free',
                'requires_auth': False,
                'url': 'https://worldview.earthdata.nasa.gov/'
            }
        }
        return info.get(source, {})
