"""
Spatial Post-Processing Module

Merges neighboring oil spill detections and removes isolated false positives.

Implements Step 11 of the oil spill detection pipeline.
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional
from scipy.spatial.distance import cdist
from scipy.cluster.hierarchy import fclusterdata

logger = logging.getLogger(__name__)


class SpatialPostprocessor:
    """Post-process detected oil spills in geographic space"""
    
    @staticmethod
    def cluster_nearby_detections(
        detections: List,
        distance_threshold_km: float = 5.0
    ) -> List[List]:
        """
        Cluster nearby detections using hierarchical clustering.
        
        Oil spills often appear as clusters of detected patches.
        Merge nearby detections for better representation.
        
        Args:
            detections: List of DetectionGeometry objects
            distance_threshold_km: Merge detections within this distance
        
        Returns:
            List of clusters, where each cluster is a list of detections
        """
        if len(detections) <= 1:
            return [[det] for det in detections]
        
        # Extract coordinates
        coords = np.array([
            [det.center_lat, det.center_lon] for det in detections
        ])
        
        # Convert km to degrees (approximate at equator)
        distance_threshold_deg = distance_threshold_km / 111.0
        
        # Compute distance matrix (using lat/lon as approximation)
        distances = cdist(coords, coords, metric='euclidean')
        
        # Hierarchical clustering
        try:
            cluster_labels = fclusterdata(
                coords,
                t=distance_threshold_deg,
                criterion='distance',
                method='complete'
            )
        except Exception as e:
            logger.warning(f"Clustering failed: {e}, returning individual detections")
            return [[det] for det in detections]
        
        # Group detections by cluster
        clusters = {}
        for detection, label in zip(detections, cluster_labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(detection)
        
        logger.info(f"✓ Clustered {len(detections)} detections into {len(clusters)} clusters")
        
        return list(clusters.values())
    
    @staticmethod
    def merge_detection_cluster(
        cluster: List,
        method: str = "weighted_centroid"
    ):
        """
        Merge detections in a cluster into single detection.
        
        Args:
            cluster: List of DetectionGeometry objects
            method: "centroid", "weighted_centroid", or "maximum_confidence"
        
        Returns:
            Single merged detection
        """
        from detection.coordinate_conversion import DetectionGeometry
        
        if not cluster:
            raise ValueError("Empty cluster")
        
        if len(cluster) == 1:
            return cluster[0]
        
        if method == "centroid":
            # Simple centroid
            lons = [det.center_lon for det in cluster]
            lats = [det.center_lat for det in cluster]
            
            merged_lon = np.mean(lons)
            merged_lat = np.mean(lats)
            merged_conf = np.mean([det.confidence for det in cluster])
        
        elif method == "weighted_centroid":
            # Confidence-weighted centroid
            lons = [det.center_lon for det in cluster]
            lats = [det.center_lat for det in cluster]
            confs = [det.confidence for det in cluster]
            
            total_conf = sum(confs)
            merged_lon = sum(l * c for l, c in zip(lons, confs)) / total_conf
            merged_lat = sum(l * c for l, c in zip(lats, confs)) / total_conf
            merged_conf = total_conf / len(cluster)
        
        elif method == "maximum_confidence":
            # Use detection with maximum confidence
            max_det = max(cluster, key=lambda d: d.confidence)
            merged_lon = max_det.center_lon
            merged_lat = max_det.center_lat
            merged_conf = max_det.confidence
        
        else:
            raise ValueError(f"Unknown merge method: {method}")
        
        # Create merged detection
        merged = DetectionGeometry(
            detection_id=f"merged_cluster_{cluster[0].detection_id}",
            center_lon=merged_lon,
            center_lat=merged_lat,
            confidence=merged_conf
        )
        
        return merged
    
    @staticmethod
    def remove_isolated_detections(
        detections: List,
        min_nearby_count: int = 2,
        search_radius_km: float = 2.0
    ) -> List:
        """
        Remove isolated detections (likely noise).
        
        A detection is considered valid if it has at least min_nearby_count
        detections within search_radius_km.
        
        Args:
            detections: List of DetectionGeometry objects
            min_nearby_count: Minimum neighbors to keep detection
            search_radius_km: Search radius for neighbors
        
        Returns:
            Filtered list of detections
        """
        if len(detections) <= min_nearby_count:
            return detections
        
        # Extract coordinates
        coords = np.array([
            [det.center_lat, det.center_lon] for det in detections
        ])
        
        # Convert km to degrees
        search_radius_deg = search_radius_km / 111.0
        
        # Compute distance matrix
        distances = cdist(coords, coords, metric='euclidean')
        
        # Count neighbors for each detection
        kept_detections = []
        
        for i, detection in enumerate(detections):
            num_neighbors = np.sum(distances[i] < search_radius_deg)
            
            if num_neighbors >= min_nearby_count:
                kept_detections.append(detection)
                logger.debug(
                    f"✓ Kept detection {detection.detection_id} "
                    f"({num_neighbors} neighbors)"
                )
            else:
                logger.debug(
                    f"✗ Removed isolated detection {detection.detection_id} "
                    f"({num_neighbors} neighbors)"
                )
        
        logger.info(
            f"✓ Removed {len(detections) - len(kept_detections)} isolated detections"
        )
        
        return kept_detections
    
    @staticmethod
    def filter_by_confidence(
        detections: List,
        min_confidence: float = 0.6,
        max_confidence: float = 1.0
    ) -> List:
        """
        Filter detections by confidence threshold.
        
        Args:
            detections: List of DetectionGeometry objects
            min_confidence: Minimum confidence to keep
            max_confidence: Maximum confidence to keep
        
        Returns:
            Filtered detections
        """
        filtered = [
            det for det in detections
            if min_confidence <= det.confidence <= max_confidence
        ]
        
        removed = len(detections) - len(filtered)
        
        if removed > 0:
            logger.info(
                f"✓ Filtered out {removed} detections "
                f"(confidence < {min_confidence} or > {max_confidence})"
            )
        
        return filtered


class PostProcessingPipeline:
    """Complete post-processing pipeline"""
    
    def __init__(
        self,
        cluster_distance_km: float = 5.0,
        min_confidence: float = 0.6,
        remove_isolated: bool = True,
        min_nearby: int = 2,
        search_radius_km: float = 2.0
    ):
        """
        Initialize post-processing pipeline.
        
        Args:
            cluster_distance_km: Distance threshold for clustering
            min_confidence: Minimum confidence threshold
            remove_isolated: Whether to remove isolated detections
            min_nearby: Minimum neighbors to keep detection
            search_radius_km: Radius for neighbor search
        """
        self.cluster_distance_km = cluster_distance_km
        self.min_confidence = min_confidence
        self.remove_isolated = remove_isolated
        self.min_nearby = min_nearby
        self.search_radius_km = search_radius_km
        
        self.postprocessor = SpatialPostprocessor()
    
    def run(self, detections: List) -> List:
        """
        Run complete post-processing pipeline.
        
        Implements Step 11 of the oil spill detection pipeline.
        
        Args:
            detections: List of DetectionGeometry objects
        
        Returns:
            Post-processed detections
        """
        logger.info("="*60)
        logger.info("SPATIAL POST-PROCESSING")
        logger.info("="*60)
        
        if not detections:
            logger.info("No detections to process")
            return []
        
        original_count = len(detections)
        
        # Step 1: Filter by confidence
        detections = self.postprocessor.filter_by_confidence(
            detections,
            min_confidence=self.min_confidence
        )
        
        # Step 2: Remove isolated (noise)
        if self.remove_isolated:
            detections = self.postprocessor.remove_isolated_detections(
                detections,
                min_nearby_count=self.min_nearby,
                search_radius_km=self.search_radius_km
            )
        
        # Step 3: Cluster nearby detections
        clusters = self.postprocessor.cluster_nearby_detections(
            detections,
            distance_threshold_km=self.cluster_distance_km
        )
        
        # Step 4: Merge clusters
        final_detections = []
        for cluster in clusters:
            merged = self.postprocessor.merge_detection_cluster(
                cluster,
                method="weighted_centroid"
            )
            final_detections.append(merged)
        
        logger.info(f"✓ Post-processing complete")
        logger.info(f"  Input detections: {original_count}")
        logger.info(f"  Output detections: {len(final_detections)}")
        
        return final_detections


def create_postprocessing_pipeline(
    level: str = "standard"
) -> PostProcessingPipeline:
    """
    Factory function to create post-processing pipeline.
    
    Args:
        level: "minimal", "standard", or "aggressive"
    
    Returns:
        Configured PostProcessingPipeline
    """
    if level == "minimal":
        return PostProcessingPipeline(
            cluster_distance_km=10.0,
            min_confidence=0.5,
            remove_isolated=False
        )
    
    elif level == "standard":
        return PostProcessingPipeline(
            cluster_distance_km=5.0,
            min_confidence=0.6,
            remove_isolated=True,
            min_nearby=2,
            search_radius_km=2.0
        )
    
    elif level == "aggressive":
        return PostProcessingPipeline(
            cluster_distance_km=3.0,
            min_confidence=0.7,
            remove_isolated=True,
            min_nearby=3,
            search_radius_km=1.0
        )
    
    else:
        logger.warning(f"Unknown post-processing level: {level}, using standard")
        return PostProcessingPipeline()
