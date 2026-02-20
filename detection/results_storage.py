"""
Results Storage Module

Stores detection results in database and JSON formats.

Implements Step 10 of the oil spill detection pipeline.
"""

import logging
import json
import os
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class DetectionResultsStorage:
    """Store detection results to multiple formats"""
    
    def __init__(self, storage_dir: str):
        """
        Initialize storage.
        
        Args:
            storage_dir: Directory to store results
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.json_dir = self.storage_dir / "json"
        self.geojson_dir = self.storage_dir / "geojson"
        
        self.json_dir.mkdir(exist_ok=True)
        self.geojson_dir.mkdir(exist_ok=True)
        
        logger.info(f"Results storage initialized at {storage_dir}")
    
    def save_detection_results(
        self,
        detections: List,
        tile_id: str,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, str]:
        """
        Save detection results to JSON and GeoJSON files.
        
        Args:
            detections: List of DetectionGeometry objects
            tile_id: Source tile ID
            timestamp: Acquisition timestamp
        
        Returns:
            Dictionary with file paths
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        base_filename = f"{tile_id}_{timestamp_str}"
        
        # Prepare results dictionary
        results_dict = {
            "tile_id": tile_id,
            "acquisition_date": timestamp.isoformat(),
            "processing_date": datetime.now().isoformat(),
            "num_detections": len(detections),
            "detections": [
                {
                    "detection_id": det.detection_id,
                    "center_lon": det.center_lon,
                    "center_lat": det.center_lat,
                    "confidence": det.confidence,
                    "bounds": det.bounds
                }
                for det in detections
            ]
        }
        
        # Save JSON
        json_path = self.json_dir / f"{base_filename}.json"
        with open(json_path, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        logger.info(f"✓ Saved detection results to {json_path}")
        
        # Save GeoJSON
        geojson_features = []
        for det in detections:
            # Save as point
            geojson_features.append(det.to_geojson_point())
            
            # Also save as polygon if bounds available
            if det.bounds:
                poly = det.to_geojson_polygon()
                if poly:
                    geojson_features.append(poly)
        
        geojson_dict = {
            "type": "FeatureCollection",
            "properties": {
                "tile_id": tile_id,
                "acquisition_date": timestamp.isoformat(),
                "num_detections": len(detections)
            },
            "features": geojson_features
        }
        
        geojson_path = self.geojson_dir / f"{base_filename}.geojson"
        with open(geojson_path, 'w') as f:
            json.dump(geojson_dict, f, indent=2)
        
        logger.info(f"✓ Saved GeoJSON to {geojson_path}")
        
        return {
            "json": str(json_path),
            "geojson": str(geojson_path)
        }
    
    def save_batch_results(
        self,
        all_results: Dict[str, List],
        batch_name: str = "batch"
    ) -> str:
        """
        Save results from multiple tiles.
        
        Args:
            all_results: Dictionary mapping tile_id to detection lists
            batch_name: Name for this batch
        
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        batch_results = {
            "batch_name": batch_name,
            "processing_date": datetime.now().isoformat(),
            "num_tiles": len(all_results),
            "tiles": []
        }
        
        total_detections = 0
        
        for tile_id, detections in all_results.items():
            tile_result = {
                "tile_id": tile_id,
                "num_detections": len(detections),
                "detections": [
                    {
                        "detection_id": det.detection_id,
                        "center_lon": det.center_lon,
                        "center_lat": det.center_lat,
                        "confidence": det.confidence
                    }
                    for det in detections
                ]
            }
            batch_results["tiles"].append(tile_result)
            total_detections += len(detections)
        
        batch_results["total_detections"] = total_detections
        
        # Save batch file
        batch_path = self.storage_dir / f"{batch_name}_{timestamp}.json"
        with open(batch_path, 'w') as f:
            json.dump(batch_results, f, indent=2)
        
        logger.info(
            f"✓ Saved batch results: {total_detections} detections in "
            f"{len(all_results)} tiles to {batch_path}"
        )
        
        return str(batch_path)


class DatabaseResultsStorage:
    """
    Store detection results to Django database.
    
    Uses the OilSpillDetection model defined in detection/models.py
    """
    
    @staticmethod
    def save_to_database(
        detections: List,
        satellite_image,
        verification_status: bool = False
    ) -> List:
        """
        Save detections to Django ORM database.
        
        Args:
            detections: List of DetectionGeometry objects
            satellite_image: SatelliteImage model instance
            verification_status: Whether results have been verified
        
        Returns:
            List of created OilSpillDetection model instances
        """
        from django.utils import timezone
        from detection.models import OilSpillDetection
        
        created_detections = []
        
        for det in detections:
            detection_obj = OilSpillDetection(
                satellite_image=satellite_image,
                confidence_score=det.confidence,
                location={
                    "type": "Point",
                    "coordinates": [det.center_lon, det.center_lat]
                },
                area_size=0.0,  # Will be calculated separately if needed
                verified=verification_status,
                geojson_data=det.to_geojson_point()
            )
            
            detection_obj.save()
            created_detections.append(detection_obj)
            
            logger.info(
                f"✓ Saved detection to database: "
                f"({det.center_lat:.4f}, {det.center_lon:.4f})"
            )
        
        logger.info(f"✓ Saved {len(created_detections)} detections to database")
        
        return created_detections


class ResultsAggregator:
    """Aggregate and summarize results"""
    
    @staticmethod
    def generate_summary(
        detections: List,
        tile_id: str,
        processing_time: float
    ) -> Dict:
        """
        Generate summary statistics for detection results.
        
        Args:
            detections: List of DetectionGeometry objects
            tile_id: Source tile ID
            processing_time: Total processing time in seconds
        
        Returns:
            Summary dictionary
        """
        if not detections:
            return {
                "tile_id": tile_id,
                "detection_count": 0,
                "processing_time_seconds": processing_time,
                "average_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0
            }
        
        confidences = [det.confidence for det in detections]
        
        return {
            "tile_id": tile_id,
            "detection_count": len(detections),
            "processing_time_seconds": processing_time,
            "average_confidence": float(np.mean(confidences)),
            "min_confidence": float(np.min(confidences)),
            "max_confidence": float(np.max(confidences)),
            "high_confidence_count": sum(1 for c in confidences if c > 0.8),
            "medium_confidence_count": sum(1 for c in confidences if 0.6 <= c <= 0.8)
        }
    
    @staticmethod
    def generate_report(
        summaries: List[Dict],
        output_path: str
    ) -> str:
        """
        Generate comprehensive report.
        
        Args:
            summaries: List of summary dictionaries
            output_path: Path to save report
        
        Returns:
            Path to saved report
        """
        import numpy as np
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Aggregate statistics
        total_detections = sum(s.get("detection_count", 0) for s in summaries)
        total_time = sum(s.get("processing_time_seconds", 0) for s in summaries)
        
        confidences = []
        for s in summaries:
            # Reconstruct confidences from summary (simplified)
            confidences.append(s.get("average_confidence", 0.0))
        
        report = {
            "report_date": datetime.now().isoformat(),
            "summary": {
                "num_tiles_processed": len(summaries),
                "total_detections": total_detections,
                "total_processing_time_seconds": total_time,
                "average_time_per_tile": total_time / len(summaries) if summaries else 0
            },
            "per_tile_results": summaries
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"✓ Generated report: {output_path}")
        
        return str(output_path)


import numpy as np  # Import here for use in generate_report
