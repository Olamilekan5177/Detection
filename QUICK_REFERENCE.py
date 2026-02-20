"""
QUICK REFERENCE GUIDE - Oil Spill Detection Pipeline

Complete reference for all modules and their usage.
"""

# ============================================================================
# STEP 1: AOI CONFIGURATION
# ============================================================================
from detection.aoi_config import (
    AreaOfInterest,
    BoundingBox,
    AOIManager
)

# Create AOI from bounding box
aoi = AreaOfInterest.from_bbox(
    name="Niger Delta",
    min_lon=5.0, min_lat=4.0,
    max_lon=7.0, max_lat=6.0
)

# Create AOI from GeoJSON
aoi = AreaOfInterest.from_geojson(name="Region", geojson_dict={...})

# Create AOI from GeoJSON file
aoi = AreaOfInterest.from_geojson_file(name="Region", file_path="aoi.geojson")

# Manage multiple AOIs
manager = AOIManager()
manager.add_aoi(aoi)
manager.save_all("aois/")
manager.load_all("aois/")


# ============================================================================
# STEPS 2-3: SENTINEL-1 QUERY AND DOWNLOAD
# ============================================================================
from detection.sentinel1_pipeline import (
    Sentinel1QueryEngine,
    Sentinel1Downloader,
    Sentinel1Pipeline,
    Sentinel1TileMetadata
)

# Query Sentinel-1 data
query_engine = Sentinel1QueryEngine(api_key="your_api_key")
tiles = query_engine.search_tiles(
    bbox=(5.0, 4.0, 7.0, 6.0),
    start_date=datetime(2026, 2, 1),
    end_date=datetime(2026, 2, 19),
    pass_direction="ASCENDING"
)

# Filter to only new tiles
new_tiles = query_engine.filter_new_tiles(
    tiles,
    metadata_dir="data/metadata",
    last_processed_date=None
)

# Download tiles
downloader = Sentinel1Downloader(download_dir="data/downloads")
for tile in new_tiles:
    zip_path = downloader.download_tile(tile["id"], tile["download_url"])
    extract_dir = downloader.extract_tile(zip_path)

# Or use complete pipeline
s1_pipeline = Sentinel1Pipeline(
    download_dir="data/downloads",
    metadata_dir="data/metadata"
)
downloaded_tiles = s1_pipeline.run(
    bbox=(5.0, 4.0, 7.0, 6.0),
    days_back=7
)


# ============================================================================
# STEP 4: SAR PREPROCESSING
# ============================================================================
from detection.sar_preprocessing import (
    SARPreprocessor,
    MultiPolarizationProcessor
)

# Preprocess SAR image
preprocessor = SARPreprocessor()
sar_image, metadata = preprocessor.preprocess_sar_image(
    geotiff_path="path/to/sentinel1_vv.tif",
    apply_db_conversion=True,
    speckle_filter="median",
    normalization="minmax",
    output_path="output.tif"
)

# Multi-polarization processing (VV and VH)
multi_poly = MultiPolarizationProcessor()
vv, vh, metadata = multi_poly.read_dual_pol("vv.tif", "vh.tif")
ratio = multi_poly.compute_vh_vv_ratio(vv, vh)


# ============================================================================
# STEP 5: PATCH EXTRACTION
# ============================================================================
from detection.patch_extraction import (
    PatchExtractor,
    AdaptivePatchExtractor,
    PatchMetadata,
    visualize_patches
)

# Extract fixed-size patches
extractor = PatchExtractor(patch_size=128, stride=64)
patches, patch_metadata, pipeline_meta = extractor.extract_patches(
    raster=sar_image,
    metadata=metadata
)

# Extract patches from region of interest
roi_patches, roi_meta, _ = extractor.extract_roi(
    raster=sar_image,
    bbox=(100, 100, 200, 200)
)

# Adaptive patch extraction
adaptive = AdaptivePatchExtractor(base_patch_size=128)
patches, meta, _ = adaptive.extract_adaptive_patches(
    raster=sar_image,
    interest_map=None
)

# Visualize patches
visualize_patches(patches, patch_metadata, num_display=9, save_path="patches.png")


# ============================================================================
# STEP 6: FEATURE EXTRACTION
# ============================================================================
from detection.feature_extraction import (
    PatchFeatureExtractor,
    StatisticalFeatureExtractor,
    TextureFeatureExtractor,
    create_feature_extractor
)

# Create feature extractor (factory function)
feature_extractor = create_feature_extractor("standard")  # minimal/standard/comprehensive

# Extract batch features
feature_matrix, patch_features = feature_extractor.extract_batch_features(
    patches=patches,
    patch_ids=[m.patch_id for m in patch_metadata]
)

# Manual feature extraction
stat_extractor = StatisticalFeatureExtractor()
basic_stats = stat_extractor.extract_basic_statistics(patch)
range_features = stat_extractor.extract_range_features(patch)
hist_features = stat_extractor.extract_histogram_features(patch)

texture_extractor = TextureFeatureExtractor()
glcm_features = texture_extractor.extract_glcm_features(patch)
lbp_features = texture_extractor.extract_lbp_features(patch)


# ============================================================================
# STEPS 7-8: MODEL INFERENCE
# ============================================================================
from detection.model_inference import (
    SklearnModelInference,
    EnsembleModelInference,
    create_inference_engine
)

# Single model inference
inference_engine = SklearnModelInference("ml_models/saved_models/oil_spill_detector.joblib")

# Single patch prediction
result = inference_engine.predict_single(feature_vector)
print(f"Oil spill: {result.is_oil_spill()}, Confidence: {result.confidence}")

# Batch predictions
predictions, total_time = inference_engine.predict_batch(
    feature_matrix=feature_matrix,
    patch_ids=[m.patch_id for m in patch_metadata]
)

# Ensemble of multiple models
ensemble = EnsembleModelInference([
    "model1.joblib",
    "model2.joblib",
    "model3.joblib"
])
ensemble_predictions = ensemble.predict_ensemble(
    feature_matrix,
    method="voting"  # voting or averaging
)


# ============================================================================
# STEP 9: COORDINATE CONVERSION
# ============================================================================
from detection.coordinate_conversion import (
    CoordinateConverter,
    PatchCoordinateMapper,
    DetectionGeometry,
    convert_detections_to_geographic
)

# Initialize converter
converter = CoordinateConverter(
    transform=metadata["transform"],
    crs=metadata["crs"]
)

# Convert single pixel to geographic
lon, lat = converter.pixel_to_geographic(row=100, col=200)

# Convert geographic to pixel
row, col = converter.geographic_to_pixel(lon=5.234, lat=4.567)

# Convert patch bounds
bounds = converter.pixel_bbox_to_geographic(
    row_start=100, col_start=100,
    row_end=228, col_end=228
)

# Map patches to coordinates
mapper = PatchCoordinateMapper(converter, patch_metadata)
lon, lat = mapper.get_patch_center_coordinates(patch_id=0)
patch_bounds = mapper.get_patch_bounds(patch_id=0)

# Convert detections to geographic
geographic_detections = convert_detections_to_geographic(
    detections=predictions,
    mapper=mapper
)

# Create detection geometry
det = DetectionGeometry(
    detection_id="det_001",
    center_lon=5.234,
    center_lat=4.567,
    confidence=0.89
)
geojson_point = det.to_geojson_point()
geojson_polygon = det.to_geojson_polygon()


# ============================================================================
# STEP 10: RESULTS STORAGE
# ============================================================================
from detection.results_storage import (
    DetectionResultsStorage,
    DatabaseResultsStorage,
    ResultsAggregator
)

# File-based storage
storage = DetectionResultsStorage(storage_dir="results/")
files = storage.save_detection_results(
    detections=geographic_detections,
    tile_id="S1A_IW_GRDH_..."
)
print(f"JSON: {files['json']}")
print(f"GeoJSON: {files['geojson']}")

# Save batch results
batch_results = {
    "tile_1": detections_1,
    "tile_2": detections_2
}
batch_file = storage.save_batch_results(batch_results, batch_name="daily_run")

# Database storage (Django)
from detection.models import SatelliteImage
sat_image = SatelliteImage.objects.create(image_id="...", source="SENTINEL")
DatabaseResultsStorage.save_to_database(
    detections=geographic_detections,
    satellite_image=sat_image
)

# Generate summary
summary = ResultsAggregator.generate_summary(
    detections=geographic_detections,
    tile_id="S1A_IW_GRDH_...",
    processing_time=25.5
)

# Generate report
report_path = ResultsAggregator.generate_report(
    summaries=[summary],
    output_path="report.json"
)


# ============================================================================
# STEP 11: SPATIAL POST-PROCESSING
# ============================================================================
from detection.spatial_postprocessing import (
    SpatialPostprocessor,
    PostProcessingPipeline,
    create_postprocessing_pipeline
)

# Use complete post-processing pipeline
postprocessor = create_postprocessing_pipeline("standard")  # minimal/standard/aggressive
final_detections = postprocessor.run(geographic_detections)

# Manual post-processing
processor = SpatialPostprocessor()

# Cluster nearby detections
clusters = processor.cluster_nearby_detections(
    detections=geographic_detections,
    distance_threshold_km=5.0
)

# Merge cluster
merged = processor.merge_detection_cluster(
    cluster=clusters[0],
    method="weighted_centroid"
)

# Remove isolated detections
filtered = processor.remove_isolated_detections(
    detections=geographic_detections,
    min_nearby_count=2,
    search_radius_km=2.0
)

# Filter by confidence
confidence_filtered = processor.filter_by_confidence(
    detections=geographic_detections,
    min_confidence=0.6
)


# ============================================================================
# STEPS 1-11: MAIN ORCHESTRATOR
# ============================================================================
from detection.pipeline_orchestrator import (
    OilSpillDetectionPipeline,
    create_pipeline
)

# Quick creation with factory function
pipeline = create_pipeline(
    aoi_name="Niger Delta",
    bbox=(5.0, 4.0, 7.0, 6.0),
    model_path="ml_models/saved_models/oil_spill_detector.joblib"
)

# Full initialization with custom config
custom_config = {
    "sentinel1": {"days_back": 14},
    "preprocessing": {"speckle_filter": "bilateral"},
    "patches": {"patch_size": 256, "stride": 128},
    "features": {"level": "comprehensive"},
    "postprocessing": {"level": "aggressive"}
}

pipeline = OilSpillDetectionPipeline(
    aoi=aoi,
    model_path="ml_models/saved_models/oil_spill_detector.joblib",
    download_dir="downloads/",
    results_dir="results/",
    metadata_dir="metadata/",
    config=custom_config
)

# Run single execution
results = pipeline.run()


# ============================================================================
# STEP 12: SCHEDULER AND CONTINUOUS EXECUTION
# ============================================================================
from detection.pipeline_scheduler import (
    IntervalScheduler,
    TimeWindowScheduler,
    FaultTolerantRunner,
    PipelineLoop,
    start_pipeline_loop,
    create_scheduler
)

# Simple interval scheduler
scheduler = IntervalScheduler(interval_hours=24.0)

# Time window scheduler (run during specific hours)
scheduler = TimeWindowScheduler(
    interval_hours=24.0,
    start_hour=0,
    end_hour=6
)

# Fault-tolerant execution
runner = FaultTolerantRunner(
    pipeline=pipeline,
    scheduler=scheduler,
    max_retries=3,
    state_file="pipeline_state.json"
)
results = runner.run_with_retry()

# Pipeline loop (continuous execution)
loop = PipelineLoop(runner, poll_interval_seconds=60.0)
loop.start(max_runs=None)  # Run indefinitely

# Or use convenience function
start_pipeline_loop(
    pipeline=pipeline,
    interval_hours=24.0,
    max_retries=3,
    poll_interval=60.0,
    max_runs=None
)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# Get default configuration
default_config = pipeline._get_default_config()

# Load AOI from different formats
aoi_bbox = AreaOfInterest.from_bbox("Region", 5.0, 4.0, 7.0, 6.0)
aoi_geojson = AreaOfInterest.from_geojson_file("Region", "boundary.geojson")

# Query results
from detection.models import OilSpillDetection
detections = OilSpillDetection.objects.filter(
    confidence_score__gte=0.7,
    verified=False
)


# ============================================================================
# DATA TYPES AND MODELS
# ============================================================================

from detection.patch_extraction import PatchMetadata
from detection.feature_extraction import PatchFeatures
from detection.model_inference import PredictionResult
from detection.coordinate_conversion import DetectionGeometry
from detection.sentinel1_pipeline import Sentinel1TileMetadata

# PatchMetadata attributes
patch_meta: PatchMetadata
print(patch_meta.patch_id)
print(patch_meta.center_pixel)
print(patch_meta.size)
print(patch_meta.to_dict())

# PatchFeatures attributes
features: PatchFeatures
print(features.patch_id)
print(features.features)  # numpy array
print(features.feature_names)  # list of strings
print(features.to_list())

# PredictionResult attributes
prediction: PredictionResult
print(prediction.patch_id)
print(prediction.predicted_class)  # 0 or 1
print(prediction.confidence)  # 0.0-1.0
print(prediction.is_oil_spill())  # boolean
print(prediction.to_dict())

# DetectionGeometry attributes
detection: DetectionGeometry
print(detection.detection_id)
print(detection.center_lon)
print(detection.center_lat)
print(detection.confidence)
print(detection.to_geojson_point())
print(detection.to_geojson_polygon())
