"""
Coordinate Conversion Utilities

Converts patch pixel coordinates to geographic (lat/lon) coordinates.
Uses raster geotransform from rasterio.

Implements Step 9 of the oil spill detection pipeline.
"""

import logging
import numpy as np
from typing import Tuple, Dict, Optional
from rasterio.transform import Affine
from rasterio.crs import CRS
import pyproj

logger = logging.getLogger(__name__)


class CoordinateConverter:
    """Convert between pixel and geographic coordinates"""
    
    def __init__(self, transform: Affine, crs: CRS):
        """
        Initialize converter.
        
        Args:
            transform: Rasterio Affine transform
            crs: Coordinate Reference System (from rasterio)
        """
        self.transform = transform
        self.crs = crs
        
        # Create pyproj transformer to WGS84 (EPSG:4326)
        self.to_wgs84 = pyproj.Transformer.from_crs(
            crs,
            "EPSG:4326",
            always_xy=True
        )
        
        logger.info(f"Coordinate converter initialized")
        logger.info(f"  Source CRS: {crs}")
        logger.info(f"  Transform: {transform}")
    
    def pixel_to_geographic(self, row: int, col: int) -> Tuple[float, float]:
        """
        Convert pixel coordinates to geographic (lon, lat).
        
        Args:
            row: Row index in raster (y coordinate)
            col: Column index in raster (x coordinate)
        
        Returns:
            Tuple of (longitude, latitude) in WGS84
        """
        # Apply rasterio transform: pixel to CRS coordinates
        x, y = self.transform * (col, row)
        
        # Transform to WGS84
        lon, lat = self.to_wgs84.transform(x, y)
        
        return (float(lon), float(lat))
    
    def geographic_to_pixel(self, lon: float, lat: float) -> Tuple[int, int]:
        """
        Convert geographic (lon, lat) to pixel coordinates.
        
        Args:
            lon: Longitude in WGS84
            lat: Latitude in WGS84
        
        Returns:
            Tuple of (row, col) in pixel coordinates
        """
        # Transform from WGS84 to source CRS
        from_wgs84 = self.to_wgs84.transform
        x, y = from_wgs84(lon, lat)
        
        # Apply inverse transform
        col = int((x - self.transform.c) / self.transform.a)
        row = int((y - self.transform.f) / self.transform.e)
        
        return (row, col)
    
    def pixel_bbox_to_geographic(
        self,
        row_start: int,
        col_start: int,
        row_end: int,
        col_end: int
    ) -> Dict[str, Tuple[float, float]]:
        """
        Convert pixel bounding box to geographic bounds.
        
        Args:
            row_start, col_start: Top-left corner in pixels
            row_end, col_end: Bottom-right corner in pixels
        
        Returns:
            Dictionary with corner coordinates
        """
        corners = {
            "top_left": self.pixel_to_geographic(row_start, col_start),
            "top_right": self.pixel_to_geographic(row_start, col_end),
            "bottom_left": self.pixel_to_geographic(row_end, col_start),
            "bottom_right": self.pixel_to_geographic(row_end, col_end)
        }
        
        lons = [c[0] for c in corners.values()]
        lats = [c[1] for c in corners.values()]
        
        return {
            **corners,
            "center": (
                np.mean(lons),
                np.mean(lats)
            ),
            "bounds": {
                "min_lon": min(lons),
                "max_lon": max(lons),
                "min_lat": min(lats),
                "max_lat": max(lats)
            }
        }


class PatchCoordinateMapper:
    """Map patch locations to geographic coordinates"""
    
    def __init__(self, converter: CoordinateConverter, patch_metadata_list: list):
        """
        Initialize mapper.
        
        Args:
            converter: CoordinateConverter instance
            patch_metadata_list: List of PatchMetadata objects
        """
        self.converter = converter
        self.patch_metadata_list = patch_metadata_list
    
    def get_patch_center_coordinates(self, patch_id: int) -> Tuple[float, float]:
        """
        Get geographic coordinates of patch center.
        
        Args:
            patch_id: ID of patch
        
        Returns:
            Tuple of (longitude, latitude)
        """
        # Find patch metadata
        patch_meta = None
        for meta in self.patch_metadata_list:
            if meta.patch_id == patch_id:
                patch_meta = meta
                break
        
        if patch_meta is None:
            raise ValueError(f"Patch {patch_id} not found")
        
        # Get center pixel
        row_center, col_center = patch_meta.center_pixel
        
        # Convert to geographic
        return self.converter.pixel_to_geographic(row_center, col_center)
    
    def get_patch_bounds(self, patch_id: int) -> Dict:
        """
        Get geographic bounds of patch.
        
        Args:
            patch_id: ID of patch
        
        Returns:
            Dictionary with bounds information
        """
        # Find patch metadata
        patch_meta = None
        for meta in self.patch_metadata_list:
            if meta.patch_id == patch_id:
                patch_meta = meta
                break
        
        if patch_meta is None:
            raise ValueError(f"Patch {patch_id} not found")
        
        # Convert patch bounds to geographic
        return self.converter.pixel_bbox_to_geographic(
            patch_meta.row_start,
            patch_meta.col_start,
            patch_meta.row_end,
            patch_meta.col_end
        )
    
    def get_all_patch_centers(self) -> Dict[int, Tuple[float, float]]:
        """
        Get geographic center coordinates for all patches.
        
        Returns:
            Dictionary mapping patch_id to (lon, lat)
        """
        centers = {}
        for patch_meta in self.patch_metadata_list:
            try:
                lon, lat = self.get_patch_center_coordinates(patch_meta.patch_id)
                centers[patch_meta.patch_id] = (lon, lat)
            except Exception as e:
                logger.warning(f"Failed to get coordinates for patch {patch_meta.patch_id}: {e}")
        
        return centers


class DetectionGeometry:
    """Geographic representation of a detection"""
    
    def __init__(
        self,
        detection_id: str,
        center_lon: float,
        center_lat: float,
        bounds: Optional[Dict] = None,
        confidence: float = 0.0
    ):
        """
        Initialize detection geometry.
        
        Args:
            detection_id: Detection identifier
            center_lon: Center longitude
            center_lat: Center latitude
            bounds: Optional bounds dictionary
            confidence: Confidence score
        """
        self.detection_id = detection_id
        self.center_lon = center_lon
        self.center_lat = center_lat
        self.bounds = bounds or {}
        self.confidence = confidence
    
    def to_geojson_point(self) -> Dict:
        """Export as GeoJSON Point"""
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.center_lon, self.center_lat]
            },
            "properties": {
                "detection_id": self.detection_id,
                "confidence": self.confidence
            }
        }
    
    def to_geojson_polygon(self) -> Optional[Dict]:
        """Export as GeoJSON Polygon using bounds"""
        if not self.bounds or "bounds" not in self.bounds:
            return None
        
        bounds = self.bounds["bounds"]
        coords = [
            [bounds["min_lon"], bounds["min_lat"]],
            [bounds["max_lon"], bounds["min_lat"]],
            [bounds["max_lon"], bounds["max_lat"]],
            [bounds["min_lon"], bounds["max_lat"]],
            [bounds["min_lon"], bounds["min_lat"]]
        ]
        
        return {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            },
            "properties": {
                "detection_id": self.detection_id,
                "confidence": self.confidence
            }
        }


def convert_detections_to_geographic(
    detections: list,
    mapper: PatchCoordinateMapper
) -> list:
    """
    Convert detection results to geographic coordinates.
    
    Implements Step 9 of the pipeline.
    
    Args:
        detections: List of PredictionResult objects
        mapper: PatchCoordinateMapper instance
    
    Returns:
        List of DetectionGeometry objects
    """
    logger.info("="*60)
    logger.info("COORDINATE CONVERSION")
    logger.info("="*60)
    
    geographic_detections = []
    
    for detection in detections:
        if not detection.is_oil_spill():
            continue  # Only convert oil spill detections
        
        try:
            # Get center coordinates
            lon, lat = mapper.get_patch_center_coordinates(detection.patch_id)
            
            # Get bounds
            bounds = mapper.get_patch_bounds(detection.patch_id)
            
            # Create geometry object
            geo_detection = DetectionGeometry(
                detection_id=f"detection_{detection.patch_id}",
                center_lon=lon,
                center_lat=lat,
                bounds=bounds,
                confidence=detection.confidence
            )
            
            geographic_detections.append(geo_detection)
            
            logger.debug(
                f"Converted patch {detection.patch_id} to "
                f"({lat:.4f}, {lon:.4f}) with confidence {detection.confidence:.2f}"
            )
        
        except Exception as e:
            logger.error(f"Failed to convert patch {detection.patch_id}: {e}")
    
    logger.info(f"✓ Converted {len(geographic_detections)} detections to geographic coordinates")
    
    return geographic_detections
