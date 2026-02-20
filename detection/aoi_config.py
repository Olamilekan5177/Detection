"""
Area of Interest (AOI) Configuration Module

Manages geographic boundaries for oil spill detection monitoring.
Supports both bounding boxes and GeoJSON polygon boundaries.
"""

import json
import logging
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """Bounding box definition (min_lon, min_lat, max_lon, max_lat)"""
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    
    @property
    def as_tuple(self) -> Tuple[float, float, float, float]:
        """Return as tuple for API calls"""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of bounding box"""
        lon = (self.min_lon + self.max_lon) / 2.0
        lat = (self.min_lat + self.max_lat) / 2.0
        return (lon, lat)
    
    @property
    def area_km2(self) -> float:
        """Approximate area in km² (at equator)"""
        lon_km = abs(self.max_lon - self.min_lon) * 111.32
        lat_km = abs(self.max_lat - self.min_lat) * 110.57
        return lon_km * lat_km
    
    def to_geojson(self) -> Dict:
        """Convert to GeoJSON Polygon"""
        coords = [
            [self.min_lon, self.min_lat],
            [self.max_lon, self.min_lat],
            [self.max_lon, self.max_lat],
            [self.min_lon, self.max_lat],
            [self.min_lon, self.min_lat]
        ]
        return {
            "type": "Polygon",
            "coordinates": [coords]
        }


class AreaOfInterest:
    """
    Manage an Area of Interest for oil spill detection.
    
    Supports:
    - Bounding boxes (simple rectangles)
    - GeoJSON polygons (complex shapes)
    """
    
    def __init__(
        self,
        name: str,
        bbox: Optional[BoundingBox] = None,
        geojson: Optional[Dict] = None,
        description: str = "",
        metadata: Optional[Dict] = None
    ):
        """
        Initialize AOI.
        
        Args:
            name: AOI name (e.g., "Niger Delta")
            bbox: BoundingBox object, or None if using GeoJSON
            geojson: GeoJSON polygon dict, or None if using bbox
            description: Human-readable description
            metadata: Custom metadata dict
        """
        self.name = name
        self.description = description
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        
        if bbox and geojson:
            raise ValueError("Provide either bbox OR geojson, not both")
        
        if not bbox and not geojson:
            raise ValueError("Provide either bbox OR geojson")
        
        self.bbox: Optional[BoundingBox] = bbox
        self.geojson: Optional[Dict] = geojson
        
        logger.info(f"✓ AOI initialized: {name}")
    
    @classmethod
    def from_bbox(
        cls,
        name: str,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        description: str = ""
    ) -> "AreaOfInterest":
        """Create AOI from bounding box coordinates"""
        bbox = BoundingBox(min_lon, min_lat, max_lon, max_lat)
        return cls(name=name, bbox=bbox, description=description)
    
    @classmethod
    def from_geojson(
        cls,
        name: str,
        geojson_dict: Dict,
        description: str = ""
    ) -> "AreaOfInterest":
        """Create AOI from GeoJSON polygon"""
        return cls(name=name, geojson=geojson_dict, description=description)
    
    @classmethod
    def from_geojson_file(
        cls,
        name: str,
        file_path: str,
        description: str = ""
    ) -> "AreaOfInterest":
        """Load AOI from GeoJSON file"""
        with open(file_path, 'r') as f:
            geojson_dict = json.load(f)
        return cls.from_geojson(name, geojson_dict, description)
    
    def get_bounding_box(self) -> BoundingBox:
        """
        Get bounding box.
        
        If AOI is defined by bbox, return directly.
        If AOI is defined by GeoJSON, calculate bbox from coordinates.
        """
        if self.bbox:
            return self.bbox
        
        # Extract coordinates from GeoJSON polygon
        coordinates = self.geojson["coordinates"][0]
        lons = [c[0] for c in coordinates]
        lats = [c[1] for c in coordinates]
        
        return BoundingBox(
            min_lon=min(lons),
            min_lat=min(lats),
            max_lon=max(lons),
            max_lat=max(lats)
        )
    
    def contains_point(self, lon: float, lat: float) -> bool:
        """Check if a point is within the AOI"""
        bbox = self.get_bounding_box()
        return (bbox.min_lon <= lon <= bbox.max_lon and
                bbox.min_lat <= lat <= bbox.max_lat)
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "bbox": asdict(self.bbox) if self.bbox else None,
            "geojson": self.geojson,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    def to_json_file(self, file_path: str):
        """Save AOI definition to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"✓ AOI saved to {file_path}")


class AOIManager:
    """Manage multiple Areas of Interest"""
    
    def __init__(self):
        """Initialize AOI manager"""
        self.aois: Dict[str, AreaOfInterest] = {}
    
    def add_aoi(self, aoi: AreaOfInterest):
        """Add an AOI to the manager"""
        if aoi.name in self.aois:
            logger.warning(f"AOI '{aoi.name}' already exists, overwriting")
        self.aois[aoi.name] = aoi
        logger.info(f"✓ AOI '{aoi.name}' added to manager")
    
    def get_aoi(self, name: str) -> Optional[AreaOfInterest]:
        """Get AOI by name"""
        return self.aois.get(name)
    
    def list_aois(self) -> List[str]:
        """List all AOI names"""
        return list(self.aois.keys())
    
    def remove_aoi(self, name: str) -> bool:
        """Remove an AOI"""
        if name in self.aois:
            del self.aois[name]
            logger.info(f"✓ AOI '{name}' removed")
            return True
        return False
    
    def save_all(self, directory: str):
        """Save all AOIs to directory as JSON files"""
        import os
        os.makedirs(directory, exist_ok=True)
        
        for name, aoi in self.aois.items():
            file_path = os.path.join(directory, f"{name}.json")
            aoi.to_json_file(file_path)
        
        logger.info(f"✓ Saved {len(self.aois)} AOIs to {directory}")
    
    def load_all(self, directory: str):
        """Load all AOIs from directory"""
        import os
        import glob
        
        json_files = glob.glob(os.path.join(directory, "*.json"))
        
        for json_file in json_files:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            if data["bbox"]:
                bbox = BoundingBox(**data["bbox"])
                aoi = AreaOfInterest(
                    name=data["name"],
                    bbox=bbox,
                    description=data.get("description", ""),
                    metadata=data.get("metadata", {})
                )
            else:
                aoi = AreaOfInterest(
                    name=data["name"],
                    geojson=data["geojson"],
                    description=data.get("description", ""),
                    metadata=data.get("metadata", {})
                )
            
            self.add_aoi(aoi)
        
        logger.info(f"✓ Loaded {len(json_files)} AOIs from {directory}")
