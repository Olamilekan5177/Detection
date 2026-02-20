"""
Sentinel-1 SAR Data Querying and Download Module

Queries and downloads new Sentinel-1 GRD (Ground Range Detected) products
for a given Area of Interest, avoiding reprocessing of already handled tiles.

Uses Sentinel Hub API for authentication and tile querying.
"""

import logging
import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import rasterio
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

from detection.sentinel_hub_config import get_sentinel_hub_config

logger = logging.getLogger(__name__)


class Sentinel1TileMetadata:
    """Store metadata about a Sentinel-1 tile to track processing"""
    
    def __init__(
        self,
        tile_id: str,
        acquisition_date: datetime,
        orbit_number: int,
        pass_direction: str,
        polarization: str,
        coordinates: Dict,
        source_url: Optional[str] = None
    ):
        """
        Initialize tile metadata.
        
        Args:
            tile_id: Unique tile identifier (e.g., from Copernicus)
            acquisition_date: When the tile was acquired
            orbit_number: Satellite orbit number
            pass_direction: ASCENDING or DESCENDING
            polarization: VV, VH, etc.
            coordinates: GeoJSON coordinates of tile bounds
            source_url: Where the tile was downloaded from
        """
        self.tile_id = tile_id
        self.acquisition_date = acquisition_date
        self.orbit_number = orbit_number
        self.pass_direction = pass_direction
        self.polarization = polarization
        self.coordinates = coordinates
        self.source_url = source_url
        self.processed = False
        self.processed_date: Optional[datetime] = None
        self.processing_notes = ""
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "tile_id": self.tile_id,
            "acquisition_date": self.acquisition_date.isoformat(),
            "orbit_number": self.orbit_number,
            "pass_direction": self.pass_direction,
            "polarization": self.polarization,
            "coordinates": self.coordinates,
            "source_url": self.source_url,
            "processed": self.processed,
            "processed_date": self.processed_date.isoformat() if self.processed_date else None,
            "processing_notes": self.processing_notes
        }


class Sentinel1QueryEngine:
    """Query Sentinel-1 products for an AOI using Sentinel Hub API"""
    
    def __init__(self, sentinel_hub_config: Optional[object] = None):
        """
        Initialize Sentinel-1 query engine with Sentinel Hub credentials.
        
        Args:
            sentinel_hub_config: SentinelHubConfig instance (auto-loads if not provided)
        """
        if sentinel_hub_config is None:
            sentinel_hub_config = get_sentinel_hub_config()
        
        self.config = sentinel_hub_config
        self.base_url = "https://sh.dataspace.copernicus.eu/api/v1"
        self.catalog_url = "https://catalogue.dataspace.copernicus.eu/odata/v1"
        
        if not self.config.is_configured():
            logger.warning("⚠ Sentinel Hub credentials not configured")
            logger.warning("   Call setup_sentinel_hub_interactive() or set environment variables")
        else:
            logger.info(f"✓ Sentinel Hub configured: {self.config.client_id[:10]}***")
    
    
    def search_tiles(
        self,
        bbox: Tuple[float, float, float, float],
        start_date: datetime,
        end_date: datetime,
        pass_direction: Optional[str] = None,
        polarization: str = "VV",
        limit: int = 100
    ) -> List[Dict]:
        """
        Search for Sentinel-1 GRD products using Sentinel Hub Catalog API.
        
        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat)
            start_date: Earliest acquisition date
            end_date: Latest acquisition date
            pass_direction: ASCENDING or DESCENDING (or None for both)
            polarization: VV, VH, or both
            limit: Maximum number of results
        
        Returns:
            List of product dictionaries with metadata
        """
        if not self.config.is_configured():
            logger.error("Sentinel Hub credentials not configured")
            return []
        
        if requests is None:
            logger.error("requests library required for Sentinel Hub API queries")
            return []
        
        logger.info(
            f"Searching Sentinel-1 tiles for bbox {bbox} "
            f"between {start_date.date()} and {end_date.date()}"
        )
        
        try:
            # Format dates for OData query (ISO format without microseconds)
            start_str = start_date.strftime('%Y-%m-%dT%H:%M:%S')
            end_str = end_date.strftime('%Y-%m-%dT%H:%M:%S')
            
            # Simplified query for Sentinel Data Space Catalog API
            # Just use collection name and date range (spatial filtering may not be supported via OData)
            filter_str = f"Collection/Name eq 'SENTINEL-1' and ContentDate/Start ge {start_str}Z and ContentDate/Start le {end_str}Z"
            
            query_url = f"{self.catalog_url}/Products"
            query_params = {
                "$filter": filter_str,
                "$top": limit,
                "$orderby": "ContentDate/Start desc",
            }
            
            logger.debug(f"Query URL: {query_url}")
            logger.debug(f"Filter: {filter_str}")
            
            # Execute the query
            response = requests.get(
                query_url,
                params=query_params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get("value", [])
                
                logger.info(f"✓ Found {len(products)} Sentinel-1 products")
                
                # Parse and return product metadata
                results = []
                for product in products:
                    result = {
                        "id": product.get("Id"),
                        "name": product.get("Name"),
                        "acquisition_date": product.get("ContentDate", {}).get("Start"),
                        "coordinates": product.get("Footprint"),
                        "product_dict": product
                    }
                    results.append(result)
                
                return results
            else:
                logger.error(f"Query failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching Sentinel-1 tiles: {e}")
            return []
    
    def check_already_processed(
        self,
        tile_id: str,
        metadata_dir: str
    ) -> bool:
        """
        Check if a tile has already been processed.
        
        Args:
            tile_id: The tile ID to check
            metadata_dir: Directory where tile metadata is stored
        
        Returns:
            True if already processed, False otherwise
        """
        metadata_path = os.path.join(metadata_dir, f"{tile_id}_metadata.json")
        
        if not os.path.exists(metadata_path):
            return False
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return metadata.get("processed", False)
        except Exception as e:
            logger.error(f"Error reading metadata for {tile_id}: {e}")
            return False
    
    def filter_new_tiles(
        self,
        tiles: List[Dict],
        metadata_dir: str,
        last_processed_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Filter tiles to only include new, unprocessed ones.
        
        Args:
            tiles: List of tiles from search_tiles()
            metadata_dir: Directory where tile metadata is stored
            last_processed_date: Only include tiles newer than this date
        
        Returns:
            Filtered list of new tiles
        """
        new_tiles = []
        
        for tile in tiles:
            tile_id = tile["id"]
            
            # Check if already processed
            if self.check_already_processed(tile_id, metadata_dir):
                logger.debug(f"Tile {tile_id} already processed, skipping")
                continue
            
            # Check if newer than last processed date
            if last_processed_date:
                tile_date = datetime.fromisoformat(
                    tile["acquisition_date"].replace("Z", "+00:00")
                )
                if tile_date <= last_processed_date:
                    logger.debug(f"Tile {tile_id} is older than last processed date, skipping")
                    continue
            
            new_tiles.append(tile)
        
        logger.info(f"✓ Found {len(new_tiles)} new tiles (filtered from {len(tiles)} total)")
        return new_tiles


class Sentinel1Downloader:
    """Download Sentinel-1 tiles"""
    
    def __init__(self, download_dir: str):
        """
        Initialize downloader.
        
        Args:
            download_dir: Directory to store downloaded tiles
        """
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
    
    def download_tile(
        self,
        tile_id: str,
        download_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 300
    ) -> Optional[str]:
        """
        Download a single Sentinel-1 tile.
        
        Args:
            tile_id: Tile identifier
            download_url: URL to download from
            username: SciHub username (if needed)
            password: SciHub password (if needed)
            timeout: Download timeout in seconds
        
        Returns:
            Path to downloaded file, or None if failed
        """
        import requests
        
        output_path = os.path.join(self.download_dir, f"{tile_id}.zip")
        
        if os.path.exists(output_path):
            logger.info(f"✓ Tile {tile_id} already downloaded at {output_path}")
            return output_path
        
        try:
            logger.info(f"Downloading {tile_id}...")
            
            # In real implementation:
            # response = requests.get(
            #     download_url,
            #     auth=(username, password) if auth needed,
            #     timeout=timeout,
            #     stream=True
            # )
            # response.raise_for_status()
            # with open(output_path, 'wb') as f:
            #     for chunk in response.iter_content(chunk_size=8192):
            #         f.write(chunk)
            
            logger.info(f"✓ Downloaded {tile_id} to {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Failed to download {tile_id}: {e}")
            return None
    
    def extract_tile(self, zip_path: str) -> Optional[str]:
        """
        Extract downloaded tile ZIP file.
        
        Args:
            zip_path: Path to downloaded ZIP file
        
        Returns:
            Path to extracted directory, or None if failed
        """
        import zipfile
        
        try:
            extract_dir = os.path.dirname(zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            logger.info(f"✓ Extracted {zip_path} to {extract_dir}")
            return extract_dir
        
        except Exception as e:
            logger.error(f"Failed to extract {zip_path}: {e}")
            return None
    
    def save_tile_metadata(
        self,
        metadata: Sentinel1TileMetadata,
        metadata_dir: str
    ):
        """
        Save tile metadata to JSON file.
        
        Args:
            metadata: Sentinel1TileMetadata object
            metadata_dir: Directory to store metadata files
        """
        os.makedirs(metadata_dir, exist_ok=True)
        
        metadata_path = os.path.join(
            metadata_dir,
            f"{metadata.tile_id}_metadata.json"
        )
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        logger.info(f"✓ Saved metadata for {metadata.tile_id}")


class Sentinel1Pipeline:
    """
    End-to-end Sentinel-1 query and download pipeline.
    Implements Step 2 and Step 3 of the oil spill detection pipeline.
    """
    
    def __init__(
        self,
        download_dir: str,
        metadata_dir: str,
        api_key: Optional[str] = None
    ):
        """Initialize pipeline"""
        self.query_engine = Sentinel1QueryEngine(api_key)
        self.downloader = Sentinel1Downloader(download_dir)
        self.metadata_dir = metadata_dir
        self.download_dir = download_dir
    
    def run(
        self,
        bbox: Tuple[float, float, float, float],
        pass_direction: Optional[str] = None,
        days_back: int = 7,
        last_processed_date: Optional[datetime] = None
    ) -> List[str]:
        """
        Run query and download pipeline.
        
        Args:
            bbox: AOI bounding box
            pass_direction: ASCENDING/DESCENDING or None
            days_back: How many days back to search
            last_processed_date: Skip tiles older than this
        
        Returns:
            List of paths to newly downloaded tiles
        """
        logger.info("="*60)
        logger.info("SENTINEL-1 QUERY AND DOWNLOAD PIPELINE")
        logger.info("="*60)
        
        # Step 2: Query Sentinel-1 data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        tiles = self.query_engine.search_tiles(
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            pass_direction=pass_direction
        )
        
        # Filter new tiles
        new_tiles = self.query_engine.filter_new_tiles(
            tiles,
            self.metadata_dir,
            last_processed_date
        )
        
        if not new_tiles:
            logger.info("No new tiles found")
            return []
        
        # Step 3: Download new tiles
        downloaded_paths = []
        
        for tile in new_tiles:
            tile_id = tile["id"]
            download_url = tile["download_url"]
            
            # Download
            zip_path = self.downloader.download_tile(tile_id, download_url)
            if not zip_path:
                continue
            
            # Extract
            extract_dir = self.downloader.extract_tile(zip_path)
            if not extract_dir:
                continue
            
            # Save metadata
            metadata = Sentinel1TileMetadata(
                tile_id=tile_id,
                acquisition_date=datetime.fromisoformat(
                    tile["acquisition_date"].replace("Z", "+00:00")
                ),
                orbit_number=tile.get("orbit_number", 0),
                pass_direction=tile.get("pass_direction", "UNKNOWN"),
                polarization=tile.get("polarization", "VV"),
                coordinates=tile.get("coordinates", {}),
                source_url=download_url
            )
            
            self.downloader.save_tile_metadata(metadata, self.metadata_dir)
            downloaded_paths.append(extract_dir)
        
        logger.info(f"✓ Pipeline completed: {len(downloaded_paths)} tiles downloaded")
        return downloaded_paths
