"""
Oil Spill Detection Pipeline - Complete Usage Guide

This module demonstrates how to use the complete 12-step pipeline
for continuous oil spill detection from Sentinel-1 SAR imagery.

Usage Examples for All 12 Steps
"""

from pathlib import Path
from detection.aoi_config import AreaOfInterest, BoundingBox
from detection.pipeline_orchestrator import OilSpillDetectionPipeline, create_pipeline
from detection.pipeline_scheduler import (
    start_pipeline_loop,
    IntervalScheduler,
    FaultTolerantRunner,
    PipelineLoop
)


# ============================================================================
# EXAMPLE 1: Simple Single Run
# ============================================================================
def example_single_run():
    """
    Run the pipeline once on a predefined AOI.
    
    This demonstrates all 12 steps in a single execution.
    """
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 1: SINGLE PIPELINE RUN")
    logger.info("="*70)
    
    # Step 1: Define Area of Interest (Niger Delta example)
    aoi = AreaOfInterest.from_bbox(
        name="Niger Delta",
        min_lon=5.0,
        min_lat=4.0,
        max_lon=7.0,
        max_lat=6.0,
        description="Oil-rich region in Nigeria"
    )
    
    logger.info(f"✓ AOI defined: {aoi.name}")
    logger.info(f"  Bounds: {aoi.get_bounding_box().as_tuple}")
    logger.info(f"  Area: {aoi.get_bounding_box().area_km2:.0f} km²")
    
    # Create pipeline
    pipeline = OilSpillDetectionPipeline(
        aoi=aoi,
        model_path="ml_models/saved_models/oil_spill_detector.joblib",
        download_dir="data/downloads",
        results_dir="data/results",
        metadata_dir="data/metadata"
    )
    
    # Run Steps 2-11 automatically
    results = pipeline.run()
    
    logger.info(f"\n✓ Pipeline completed")
    logger.info(f"  Status: {results.get('status')}")
    logger.info(f"  Tiles processed: {len(results.get('tile_results', []))}")
    
    return results


# ============================================================================
# EXAMPLE 2: Continuous Monitoring Loop
# ============================================================================
def example_continuous_monitoring():
    """
    Run pipeline continuously at regular intervals.
    
    Implements Step 12 (Repeat) with fault tolerance.
    """
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 2: CONTINUOUS MONITORING LOOP")
    logger.info("="*70)
    
    # Create pipeline for Niger Delta
    pipeline = create_pipeline(
        aoi_name="Niger Delta",
        bbox=(5.0, 4.0, 7.0, 6.0),
        model_path="ml_models/saved_models/oil_spill_detector.joblib"
    )
    
    # Start continuous loop (runs every 24 hours)
    # This will run indefinitely until interrupted (Ctrl+C)
    logger.info(
        "Starting continuous monitoring loop...\n"
        "Control+C to stop\n"
    )
    
    start_pipeline_loop(
        pipeline=pipeline,
        interval_hours=24.0,    # Run every 24 hours
        max_retries=3,          # Retry 3 times on failure
        poll_interval=60.0,     # Check scheduler every 60 seconds
        max_runs=None,          # Run indefinitely
        state_file="pipeline_state.json"
    )


# ============================================================================
# EXAMPLE 3: Multiple AOI Monitoring
# ============================================================================
def example_multiple_aois():
    """
    Monitor multiple Areas of Interest simultaneously.
    
    Runs separate pipeline instances for different regions.
    """
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 3: MULTIPLE AOI MONITORING")
    logger.info("="*70)
    
    # Define multiple regions
    aois = [
        ("Niger Delta", (5.0, 4.0, 7.0, 6.0)),
        ("Gulf of Mexico", (-90.0, 25.0, -85.0, 30.0)),
        ("North Sea", (-2.0, 55.0, 6.0, 60.0))
    ]
    
    results = {}
    
    for aoi_name, bbox in aois:
        logger.info(f"\nProcessing {aoi_name}...")
        
        pipeline = create_pipeline(
            aoi_name=aoi_name,
            bbox=bbox,
            model_path="ml_models/saved_models/oil_spill_detector.joblib",
            base_dir=f"data/{aoi_name.replace(' ', '_').lower()}"
        )
        
        # Run once
        result = pipeline.run()
        results[aoi_name] = result
        
        logger.info(f"  Status: {result.get('status')}")
    
    return results


# ============================================================================
# EXAMPLE 4: Custom Configuration
# ============================================================================
def example_custom_configuration():
    """
    Use custom configuration for pipeline parameters.
    """
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 4: CUSTOM CONFIGURATION")
    logger.info("="*70)
    
    # Create AOI from GeoJSON
    aoi = AreaOfInterest.from_geojson(
        name="Custom Region",
        geojson_dict={
            "type": "Polygon",
            "coordinates": [[
                [5.0, 4.0],
                [7.0, 4.0],
                [7.0, 6.0],
                [5.0, 6.0],
                [5.0, 4.0]
            ]]
        }
    )
    
    # Custom configuration
    custom_config = {
        "sentinel1": {
            "days_back": 14,          # Search last 14 days
            "pass_direction": "ASCENDING",
            "polarization": "VV"
        },
        "preprocessing": {
            "apply_db_conversion": True,
            "speckle_filter": "bilateral",  # Bilateral filter instead of median
            "normalization": "minmax",
            "mask_water": True
        },
        "patches": {
            "patch_size": 256,        # Larger patches
            "stride": 128
        },
        "features": {
            "level": "comprehensive"  # All available features
        },
        "inference": {
            "confidence_threshold": 0.7
        },
        "postprocessing": {
            "level": "aggressive"     # Remove more false positives
        }
    }
    
    pipeline = OilSpillDetectionPipeline(
        aoi=aoi,
        model_path="ml_models/saved_models/oil_spill_detector.joblib",
        download_dir="data/downloads",
        results_dir="data/results",
        metadata_dir="data/metadata",
        config=custom_config
    )
    
    logger.info("✓ Pipeline created with custom configuration")
    logger.info(f"  Feature level: {custom_config['features']['level']}")
    logger.info(f"  Patch size: {custom_config['patches']['patch_size']}")
    logger.info(f"  Post-processing: {custom_config['postprocessing']['level']}")
    
    return pipeline


# ============================================================================
# EXAMPLE 5: Manual Step-by-Step Control
# ============================================================================
def example_manual_steps():
    """
    Demonstrate manual control of individual pipeline steps.
    
    Useful for debugging or custom workflows.
    """
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 5: MANUAL STEP-BY-STEP CONTROL")
    logger.info("="*70)
    
    import numpy as np
    from detection.sar_preprocessing import SARPreprocessor
    from detection.patch_extraction import PatchExtractor
    from detection.feature_extraction import create_feature_extractor
    from detection.model_inference import SklearnModelInference
    from detection.coordinate_conversion import (
        CoordinateConverter, PatchCoordinateMapper
    )
    
    # Step 4: Manual preprocessing
    logger.info("\nStep 4: Manual SAR Preprocessing")
    preprocessor = SARPreprocessor()
    sar_image, metadata = preprocessor.preprocess_sar_image(
        "data/sample_sentinel1.tif",
        apply_db_conversion=True,
        speckle_filter="median"
    )
    
    # Step 5: Manual patch extraction
    logger.info("Step 5: Manual Patch Extraction")
    extractor = PatchExtractor(patch_size=128, stride=64)
    patches, patch_metadata, pipeline_meta = extractor.extract_patches(sar_image, metadata)
    logger.info(f"  Extracted {len(patches)} patches")
    
    # Step 6: Manual feature extraction
    logger.info("Step 6: Manual Feature Extraction")
    feature_extractor = create_feature_extractor("standard")
    feature_matrix, patch_features = feature_extractor.extract_batch_features(
        patches,
        [m.patch_id for m in patch_metadata]
    )
    logger.info(f"  Created {feature_matrix.shape[0]}x{feature_matrix.shape[1]} feature matrix")
    
    # Step 7-8: Manual inference
    logger.info("Step 7-8: Manual Model Inference")
    inference_engine = SklearnModelInference(
        "ml_models/saved_models/oil_spill_detector.joblib"
    )
    predictions, inference_time = inference_engine.predict_batch(
        feature_matrix,
        [m.patch_id for m in patch_metadata]
    )
    logger.info(f"  {sum(1 for p in predictions if p.is_oil_spill())} oil spills detected")
    
    logger.info("✓ Manual pipeline execution complete")


# ============================================================================
# EXAMPLE 6: Integration with Django
# ============================================================================
def example_django_integration():
    """
    Save results directly to Django database.
    """
    logger.info("\n" + "="*70)
    logger.info("EXAMPLE 6: DJANGO DATABASE INTEGRATION")
    logger.info("="*70)
    
    # Example of saving to Django ORM
    # Warning: Only works inside Django environment
    
    logger.info("""
    To integrate with Django:
    
    1. Run in Django shell:
       python manage.py shell
    
    2. Import and execute:
       from detection.pipeline_orchestrator import create_pipeline
       from detection.results_storage import DatabaseResultsStorage
       from detection.models import SatelliteImage, OilSpillDetection
       
       # Create and run pipeline
       pipeline = create_pipeline(
           aoi_name="Niger Delta",
           bbox=(5.0, 4.0, 7.0, 6.0),
           model_path="ml_models/saved_models/oil_spill_detector.joblib"
       )
       results = pipeline.run()
       
       # Map results to Django models
       # Create SatelliteImage and OilSpillDetection records
       for tile_result in results['tile_results']:
           sat_image = SatelliteImage.objects.create(
               image_id=tile_result['tile_id'],
               source='SENTINEL',
               ...
           )
           
           # Save detections
           DatabaseResultsStorage.save_to_database(
               detections,
               satellite_image=sat_image
           )
    """)


# ============================================================================
# Configuration Reference
# ============================================================================
def print_configuration_reference():
    """Print all available configuration options"""
    
    reference = """
    PIPELINE CONFIGURATION REFERENCE
    
    config = {
        # Sentinel-1 Data Querying (Steps 2-3)
        "sentinel1": {
            "days_back": 7,              # Search last N days
            "pass_direction": None,      # ASCENDING/DESCENDING/None
            "polarization": "VV"         # VV, VH, or both
        },
        
        # SAR Preprocessing (Step 4)
        "preprocessing": {
            "apply_db_conversion": True,              # Convert to dB scale
            "speckle_filter": "median",               # median/bilateral/morphological
            "normalization": "minmax",                # minmax/zscore
            "mask_water": False                       # Apply water-only mask
        },
        
        # Patch Extraction (Step 5)
        "patches": {
            "patch_size": 128,           # Patch size in pixels
            "stride": 64                 # Stride (64=50% overlap)
        },
        
        # Feature Extraction (Step 6)
        "features": {
            "level": "standard"          # minimal/standard/comprehensive
        },
        
        # Model Inference (Steps 7-8)
        "inference": {
            "confidence_threshold": 0.6
        },
        
        # Spatial Post-Processing (Step 11)
        "postprocessing": {
            "level": "standard"          # minimal/standard/aggressive
        }
    }
    """
    
    print(reference)


# ============================================================================
# Main execution
# ============================================================================
if __name__ == "__main__":
    logger.info("OIL SPILL DETECTION PIPELINE - USAGE EXAMPLES")
    
    # Uncomment to run examples:
    
    # Run single execution
    # example_single_run()
    
    # Run continuous monitoring
    # example_continuous_monitoring()
    
    # Monitor multiple AOIs
    # example_multiple_aois()
    
    # Custom configuration
    # pipeline = example_custom_configuration()
    
    # Manual step control
    # example_manual_steps()
    
    # Show configuration options
    print_configuration_reference()
    
    logger.info("\n✓ Refer to the examples above for different use cases")
