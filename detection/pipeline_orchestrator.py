"""
Main Oil Spill Detection Pipeline Orchestrator

Coordinates all pipeline components (Steps 1-11) and implements
the complete end-to-end workflow.

Implements all 12 steps of the oil spill detection pipeline.
"""

import logging
import os
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class OilSpillDetectionPipeline:
    """
    Complete end-to-end oil spill detection pipeline.
    
    Orchestrates all 12 steps:
    1. Define AOI
    2. Query Sentinel-1
    3. Download tiles
    4. Preprocess SAR
    5. Extract patches
    6. Extract features
    7. Load model
    8. Predict
    9. Convert coordinates
    10. Store results
    11. Post-process
    12. Repeat/schedule
    """
    
    def __init__(
        self,
        aoi,
        model_path: str,
        download_dir: str,
        results_dir: str,
        metadata_dir: str,
        config: Optional[Dict] = None
    ):
        """
        Initialize pipeline.
        
        Args:
            aoi: AreaOfInterest object
            model_path: Path to trained sklearn model
            download_dir: Directory for downloaded tiles
            results_dir: Directory for results
            metadata_dir: Directory for metadata
            config: Optional configuration dictionary
        """
        self.aoi = aoi
        self.model_path = model_path
        self.download_dir = Path(download_dir)
        self.results_dir = Path(results_dir)
        self.metadata_dir = Path(metadata_dir)
        
        # Create directories
        for d in [self.download_dir, self.results_dir, self.metadata_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.config = config or self._get_default_config()
        
        # Pipeline state
        self.last_run_time = None
        self.last_processed_date = None
        self.run_count = 0
        
        logger.info("="*60)
        logger.info("OIL SPILL DETECTION PIPELINE INITIALIZED")
        logger.info("="*60)
        logger.info(f"AOI: {aoi.name}")
        logger.info(f"Model: {model_path}")
    
    def _get_default_config(self) -> Dict:
        """Get default pipeline configuration"""
        return {
            # Sentinel-1 querying
            "sentinel1": {
                "days_back": 7,
                "pass_direction": None,  # Both ascending and descending
                "polarization": "VV"
            },
            # SAR preprocessing
            "preprocessing": {
                "apply_db_conversion": True,
                "speckle_filter": "median",
                "normalization": "minmax",
                "mask_water": False
            },
            # Patch extraction
            "patches": {
                "patch_size": 128,
                "stride": 64
            },
            # Feature extraction
            "features": {
                "level": "standard"  # minimal, standard, comprehensive
            },
            # Model inference
            "inference": {
                "confidence_threshold": 0.6
            },
            # Post-processing
            "postprocessing": {
                "level": "standard"  # minimal, standard, aggressive
            },
            # Results storage
            "storage": {
                "save_json": True,
                "save_geojson": True,
                "save_database": True
            }
        }
    
    def run_single_tile(self, tile_path: str, tile_id: str) -> Dict:
        """
        Run pipeline on a single tile.
        
        Args:
            tile_path: Path to downloaded Sentinel-1 tile
            tile_id: Tile identifier
        
        Returns:
            Dictionary with pipeline results
        """
        import time
        from detection.sar_preprocessing import SARPreprocessor
        from detection.patch_extraction import PatchExtractor
        from detection.feature_extraction import create_feature_extractor
        from detection.model_inference import SklearnModelInference
        from detection.coordinate_conversion import (
            CoordinateConverter, PatchCoordinateMapper,
            convert_detections_to_geographic
        )
        from detection.spatial_postprocessing import create_postprocessing_pipeline
        from detection.results_storage import DetectionResultsStorage, ResultsAggregator
        
        logger.info("="*60)
        logger.info(f"PROCESSING TILE: {tile_id}")
        logger.info("="*60)
        
        start_time = time.time()
        results = {
            "tile_id": tile_id,
            "status": "processing",
            "components": {}
        }
        
        try:
            # Step 4: Preprocess SAR image
            logger.info(f"\n[Step 4] PREPROCESSING")
            preprocessor = SARPreprocessor()
            sar_image, metadata = preprocessor.preprocess_sar_image(
                tile_path,
                **self.config["preprocessing"]
            )
            results["components"]["preprocessing"] = {
                "status": "success",
                "shape": sar_image.shape
            }
            
            # Step 5: Extract patches
            logger.info(f"\n[Step 5] PATCH EXTRACTION")
            extractor = PatchExtractor(**self.config["patches"])
            patches, patch_metadata, pipeline_meta = extractor.extract_patches(sar_image, metadata)
            results["components"]["patch_extraction"] = {
                "status": "success",
                "num_patches": len(patches)
            }
            
            # Step 6: Extract features
            logger.info(f"\n[Step 6] FEATURE EXTRACTION")
            feature_extractor = create_feature_extractor(
                self.config["features"]["level"]
            )
            feature_matrix, patch_features = feature_extractor.extract_batch_features(
                patches,
                [m.patch_id for m in patch_metadata]
            )
            results["components"]["feature_extraction"] = {
                "status": "success",
                "num_features": feature_matrix.shape[1]
            }
            
            # Step 7-8: Load model and predict
            logger.info(f"\n[Step 7-8] MODEL INFERENCE")
            inference_engine = SklearnModelInference(self.model_path)
            predictions, inference_time = inference_engine.predict_batch(
                feature_matrix,
                [m.patch_id for m in patch_metadata]
            )
            results["components"]["inference"] = {
                "status": "success",
                "inference_time_ms": inference_time
            }
            
            # Step 9: Convert to geographic coordinates
            logger.info(f"\n[Step 9] COORDINATE CONVERSION")
            converter = CoordinateConverter(metadata["transform"], metadata["crs"])
            mapper = PatchCoordinateMapper(converter, patch_metadata)
            
            detections = convert_detections_to_geographic(predictions, mapper)
            results["components"]["coordinate_conversion"] = {
                "status": "success",
                "num_detections": len(detections)
            }
            
            # Step 11: Post-processing
            logger.info(f"\n[Step 11] SPATIAL POST-PROCESSING")
            postprocessor = create_postprocessing_pipeline(
                self.config["postprocessing"]["level"]
            )
            final_detections = postprocessor.run(detections)
            results["components"]["postprocessing"] = {
                "status": "success",
                "final_detection_count": len(final_detections)
            }
            
            # Step 10: Store results
            logger.info(f"\n[Step 10] RESULTS STORAGE")
            storage = DetectionResultsStorage(str(self.results_dir))
            file_paths = storage.save_detection_results(
                final_detections,
                tile_id,
                datetime.now()
            )
            results["components"]["results_storage"] = {
                "status": "success",
                "files": file_paths
            }
            
            # Generate summary
            elapsed = time.time() - start_time
            summary = ResultsAggregator.generate_summary(
                final_detections,
                tile_id,
                elapsed
            )
            
            results["status"] = "success"
            results["summary"] = summary
            results["processing_time_seconds"] = elapsed
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
        
        return results
    
    def run(self) -> Dict:
        """
        Run complete pipeline once.
        
        Steps 1-3: Query and download
        Steps 4-11: Process with run_single_tile
        Step 12: Repeat is handled by scheduler
        
        Returns:
            Dictionary with overall results
        """
        from detection.sentinel1_pipeline import Sentinel1Pipeline
        
        logger.info("\n" + "="*60)
        logger.info("STARTING OIL SPILL DETECTION PIPELINE RUN")
        logger.info("="*60)
        logger.info(f"Timestamp: {datetime.now()}")
        logger.info(f"Run #: {self.run_count + 1}")
        
        import time
        run_start = time.time()
        
        overall_results = {
            "timestamp": datetime.now().isoformat(),
            "aoi": self.aoi.name,
            "status": "processing",
            "tile_results": []
        }
        
        try:
            # Steps 2-3: Query and download Sentinel-1 data
            logger.info(f"\n[Steps 2-3] SENTINEL-1 QUERY AND DOWNLOAD")
            s1_pipeline = Sentinel1Pipeline(
                download_dir=str(self.download_dir),
                metadata_dir=str(self.metadata_dir)
            )
            
            bbox = self.aoi.get_bounding_box()
            downloaded_tiles = s1_pipeline.run(
                bbox=bbox.as_tuple,
                days_back=self.config["sentinel1"]["days_back"],
                last_processed_date=self.last_processed_date
            )
            
            if not downloaded_tiles:
                logger.info("No new tiles found")
                overall_results["status"] = "no_new_data"
                overall_results["processing_time_seconds"] = time.time() - run_start
                return overall_results
            
            # Process each tile
            for tile_path in downloaded_tiles:
                # Extract tile ID from path
                tile_id = Path(tile_path).name
                
                tile_result = self.run_single_tile(tile_path, tile_id)
                overall_results["tile_results"].append(tile_result)
            
            overall_results["status"] = "success"
            elapsed = time.time() - run_start
            overall_results["processing_time_seconds"] = elapsed
            
            # Update pipeline state
            self.last_run_time = datetime.now()
            self.last_processed_date = datetime.now()
            self.run_count += 1
            
            logger.info(f"\n✓ PIPELINE RUN COMPLETE")
            logger.info(f"  Total tiles processed: {len(downloaded_tiles)}")
            logger.info(f"  Total detections: {sum(len(r.get('summary', {}).get('detections', [])) for r in overall_results['tile_results'])}")
            logger.info(f"  Total time: {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            overall_results["status"] = "failed"
            overall_results["error"] = str(e)
        
        return overall_results


def create_pipeline(
    aoi_name: str,
    bbox: tuple,
    model_path: str,
    base_dir: str = "./spill_detection"
) -> OilSpillDetectionPipeline:
    """
    Factory function to create and initialize pipeline.
    
    Args:
        aoi_name: Name for AOI
        bbox: (min_lon, min_lat, max_lon, max_lat) bounding box
        model_path: Path to trained model
        base_dir: Base directory for downloads/results
    
    Returns:
        Initialized OilSpillDetectionPipeline
    """
    from detection.aoi_config import AreaOfInterest, BoundingBox
    
    # Create AOI
    bbox_obj = BoundingBox(*bbox)
    aoi = AreaOfInterest(
        name=aoi_name,
        bbox=bbox_obj,
        description=f"Oil spill monitoring region for {aoi_name}"
    )
    
    # Create pipeline
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)
    
    pipeline = OilSpillDetectionPipeline(
        aoi=aoi,
        model_path=model_path,
        download_dir=str(base_path / "downloads"),
        results_dir=str(base_path / "results"),
        metadata_dir=str(base_path / "metadata")
    )
    
    return pipeline
