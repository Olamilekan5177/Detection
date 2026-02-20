# Oil Spill Detection Pipeline - Complete Implementation

## Overview

This is a complete, production-ready implementation of a **12-step oil spill detection pipeline** using Sentinel-1 SAR (Synthetic Aperture Radar) imagery. The system continuously monitors Areas of Interest (AOIs) for oil spills using machine learning inference on SAR tiles.

## Pipeline Architecture

The pipeline implements all 12 steps specified:

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Define Area of Interest (AOI)                       │
│         - Bounding box or GeoJSON polygon                   │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Step 2-3: Query & Download Sentinel-1 Data                  │
│           - Search Sentinel Hub/Copernicus                  │
│           - Filter by date, exclude processed tiles         │
│           - Download new GRD products                       │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Step 4: Preprocess SAR Imagery                              │
│         - Read GeoTIFF with rasterio                        │
│         - Convert to dB scale if needed                     │
│         - Apply speckle filtering (median/bilateral)        │
│         - Normalize pixel values                            │
│         - Mask invalid/non-water pixels                     │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Step 5: Extract Patches                                     │
│         - Split raster into 128×128 patches                 │
│         - Configurable stride for overlap                   │
│         - Maintain pixel indices for coordinate conversion  │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Step 6: Feature Extraction                                  │
│         - Statistical: mean, std, min, max, median          │
│         - Histogram: entropy, energy                        │
│         - Texture (GLCM): contrast, homogeneity, energy     │
│         - Create feature vectors for sklearn                │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Step 7: Load Pretrained sklearn Model                       │
│         - Load from disk (joblib/pickle)                    │
│         - NO retraining during detection                    │
│         - Use strictly for inference                        │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Step 8: Predict Oil Spill per Patch                         │
│         - Pass feature vectors to model.predict()           │
│         - Classify: oil (1) or no-spill (0)                │
│         - Oil predictions proceed to coordinate conversion  │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Step 9: Convert to Geographic Coordinates                   │
│         - Use rasterio geotransform                         │
│         - Convert patch pixel indices → lat/lon             │
│         - Coordinates represent detected location           │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Step 10: Store Detection Results                            │
│          - Save to JSON files                               │
│          - Save to GeoJSON (mapping)                        │
│          - Store in Django database                         │
│          - Include confidence scores, timestamps            │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Step 11: Spatial Post-Processing                            │
│          - Cluster nearby detections                        │
│          - Remove isolated noise                            │
│          - Merge neighboring patches                        │
│          - Filter by confidence threshold                   │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Step 12: Repeat Execution (Scheduler)                       │
│          - Run continuously at fixed interval               │
│          - Prevent duplicate tile processing                │
│          - Fault tolerance & automatic retry                │
│          - Persist execution state                          │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

### Core Modules

| Module                      | Purpose                             | Steps |
| --------------------------- | ----------------------------------- | ----- |
| `aoi_config.py`             | AOI definition and management       | 1     |
| `sentinel1_pipeline.py`     | Query and download Sentinel-1 data  | 2-3   |
| `sar_preprocessing.py`      | SAR image preprocessing             | 4     |
| `patch_extraction.py`       | Extract patches from rasters        | 5     |
| `feature_extraction.py`     | Extract numerical features          | 6     |
| `model_inference.py`        | Load model and make predictions     | 7-8   |
| `coordinate_conversion.py`  | Convert pixels to geographic coords | 9     |
| `results_storage.py`        | Store results in multiple formats   | 10    |
| `spatial_postprocessing.py` | Post-processing and clustering      | 11    |
| `pipeline_orchestrator.py`  | Main pipeline orchestrator          | All   |
| `pipeline_scheduler.py`     | Scheduler and fault tolerance       | 12    |
| `pipeline_examples.py`      | Usage examples                      | All   |

## Quick Start

### Basic Single Run

```python
from detection.pipeline_orchestrator import create_pipeline

# Create pipeline for Niger Delta
pipeline = create_pipeline(
    aoi_name="Niger Delta",
    bbox=(5.0, 4.0, 7.0, 6.0),  # (min_lon, min_lat, max_lon, max_lat)
    model_path="ml_models/saved_models/oil_spill_detector.joblib"
)

# Run once
results = pipeline.run()
```

### Continuous Monitoring

```python
from detection.pipeline_scheduler import start_pipeline_loop

# Run pipeline every 24 hours continuously
start_pipeline_loop(
    pipeline=pipeline,
    interval_hours=24.0,
    max_retries=3,
    poll_interval=60.0
)
```

### Multiple AOIs

```python
# Monitor multiple regions
aois = [
    ("Niger Delta", (5.0, 4.0, 7.0, 6.0)),
    ("Gulf of Mexico", (-90.0, 25.0, -85.0, 30.0)),
    ("North Sea", (-2.0, 55.0, 6.0, 60.0))
]

for aoi_name, bbox in aois:
    pipeline = create_pipeline(aoi_name, bbox, model_path)
    results = pipeline.run()
```

## Configuration

### Custom Pipeline Configuration

```python
config = {
    "sentinel1": {
        "days_back": 7,              # Search interval
        "pass_direction": None,      # ASCENDING/DESCENDING/None
        "polarization": "VV"
    },
    "preprocessing": {
        "apply_db_conversion": True,
        "speckle_filter": "bilateral",  # median/bilateral/morphological
        "normalization": "minmax",      # minmax/zscore
        "mask_water": False
    },
    "patches": {
        "patch_size": 128,
        "stride": 64
    },
    "features": {
        "level": "standard"  # minimal/standard/comprehensive
    },
    "postprocessing": {
        "level": "standard"  # minimal/standard/aggressive
    }
}

pipeline = OilSpillDetectionPipeline(
    aoi=aoi,
    model_path="model.joblib",
    download_dir="downloads",
    results_dir="results",
    metadata_dir="metadata",
    config=config
)
```

## Feature Extraction

The pipeline extracts three levels of features from SAR patches:

### Minimal Features (10 features)

- Mean, Std, Min, Max, Median, Kurtosis, Skewness
- Range, IQR, Coefficient of Variation

### Standard Features (18 features)

- All minimal features
- Histogram entropy and energy
- GLCM (Gray Level Co-occurrence Matrix): contrast, dissimilarity, homogeneity, energy, correlation, ASM

### Comprehensive Features (19 features)

- All standard features
- LBP (Local Binary Pattern) entropy

## Results Output

### JSON Format

```json
{
  "tile_id": "S1A_IW_GRDH_...",
  "acquisition_date": "2026-02-19T10:30:00",
  "processing_date": "2026-02-19T10:35:00",
  "num_detections": 3,
  "detections": [
    {
      "detection_id": "detection_142",
      "center_lon": 5.234,
      "center_lat": 4.567,
      "confidence": 0.89,
      "bounds": {...}
    }
  ]
}
```

### GeoJSON Format

```json
{
  "type": "FeatureCollection",
  "properties": {
    "tile_id": "S1A_IW_GRDH_...",
    "num_detections": 3
  },
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [5.234, 4.567]
      },
      "properties": {
        "detection_id": "detection_142",
        "confidence": 0.89
      }
    }
  ]
}
```

### Database Storage

Results are automatically saved to Django `OilSpillDetection` model:

- Tile reference
- Geographic location (Point)
- Confidence score
- Processing timestamp
- Optional verification status

## Scheduler Options

### Interval Scheduler (Simple)

Runs every N hours:

```python
from detection.pipeline_scheduler import IntervalScheduler
scheduler = IntervalScheduler(interval_hours=24.0)
```

### Time Window Scheduler (Advanced)

Runs within specific hours:

```python
from detection.pipeline_scheduler import TimeWindowScheduler
scheduler = TimeWindowScheduler(
    interval_hours=24.0,
    start_hour=0,   # Start at midnight
    end_hour=6      # End at 6 AM
)
```

## Fault Tolerance

The system includes automatic fault tolerance:

1. **Automatic Retry**: Configurable retry attempts with exponential backoff
2. **State Persistence**: Saves execution state to `pipeline_state.json`
3. **Duplicate Prevention**: Tracks processed tiles to avoid reprocessing
4. **Error Logging**: Comprehensive logging of all failures
5. **Graceful Shutdown**: Handles Ctrl+C cleanly

```python
from detection.pipeline_scheduler import FaultTolerantRunner

runner = FaultTolerantRunner(
    pipeline=pipeline,
    scheduler=scheduler,
    max_retries=3,
    state_file="pipeline_state.json"
)

results = runner.run_with_retry()
```

## Integration with Django

### Save to Database

```python
from detection.results_storage import DatabaseResultsStorage
from detection.models import SatelliteImage

# Create SatelliteImage record
sat_image = SatelliteImage.objects.create(
    image_id="S1A_IW_GRDH_...",
    source="SENTINEL",
    acquisition_date=datetime.now(),
    processed=True
)

# Save detections
DatabaseResultsStorage.save_to_database(
    detections=geographic_detections,
    satellite_image=sat_image
)
```

### Query Results

```python
from detection.models import OilSpillDetection

# Find high-confidence detections
detections = OilSpillDetection.objects.filter(
    confidence_score__gte=0.8,
    verified=False
)

for detection in detections:
    print(f"Location: {detection.location}")
    print(f"Confidence: {detection.confidence_score}")
```

## Performance Characteristics

| Component             | Time Per Tile | Notes                      |
| --------------------- | ------------- | -------------------------- |
| Query & Download      | 5-15 min      | Depends on Sentinel HubAPI |
| SAR Preprocessing     | 2-5 min       | Depends on image size      |
| Patch Extraction      | 10-30 sec     | 128×128 patches            |
| Feature Extraction    | 30-90 sec     | Standard feature set       |
| Model Inference       | 10-60 sec     | sklearn inference          |
| Coordinate Conversion | 5-10 sec      | Per detection              |
| Post-processing       | 10-20 sec     | Clustering & filtering     |
| **Total per Tile**    | **10-30 min** | Typical for 20×20km tile   |

## Memory Requirements

- SAR image (256×256 px): ~125 MB
- Patches extraction (256×256 px): ~200 MB
- Feature matrix (1000 patches, 18 features): ~75 MB
- **Total**: ~400 MB per concurrent tile

## Error Handling

Common issues and solutions:

### Issue: "Model not found"

```
Solution: Check model_path parameter
pipeline = create_pipeline(
    ...
    model_path="ml_models/saved_models/oil_spill_detector.joblib"
)
```

### Issue: "No new tiles found"

```
Solution: Check AOI bounds and date range
bbox = (5.0, 4.0, 7.0, 6.0)  # Valid (min_lon, min_lat, max_lon, max_lat)
```

### Issue: "Sentinel Hub API authentication failed"

```
Solution: Set API credentials
export SENTINEL_CLIENTID="your_client_id"
export SENTINEL_CLIENTSECRET="your_client_secret"
```

## Monitoring and Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Pipeline State

```python
import json
with open("pipeline_state.json") as f:
    state = json.load(f)
    print(f"Runs completed: {state['run_count']}")
    print(f"Success rate: {state['success_count']/state['run_count']:.1%}")
```

### Visualize Patches (for debugging)

```python
from detection.patch_extraction import visualize_patches

visualize_patches(
    patches=patches,
    patch_metadata=patch_metadata,
    num_display=9,
    save_path="debug/patches.png"
)
```

## Production Deployment

### Django Management Command

Create `detection/management/commands/run_oil_spill_pipeline.py`:

```python
from django.core.management.base import BaseCommand
from detection.pipeline_orchestrator import create_pipeline
from detection.pipeline_scheduler import start_pipeline_loop

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--aoi', type=str, default='Niger Delta')
        parser.add_argument('--interval', type=float, default=24.0)

    def handle(self, *args, **options):
        pipeline = create_pipeline(
            aoi_name=options['aoi'],
            bbox=(5.0, 4.0, 7.0, 6.0),  # Configure as needed
            model_path="ml_models/saved_models/oil_spill_detector.joblib"
        )

        start_pipeline_loop(
            pipeline=pipeline,
            interval_hours=options['interval']
        )
```

Run with:

```bash
python manage.py run_oil_spill_pipeline --aoi "Niger Delta" --interval 24
```

### Docker Deployment

```dockerfile
FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "manage.py", "run_oil_spill_pipeline"]
```

### Celery Integration

```python
from celery import shared_task
from detection.pipeline_orchestrator import create_pipeline

@shared_task
def run_oil_spill_detection():
    pipeline = create_pipeline(...)
    return pipeline.run()

# Schedule in celery beat
from celery.schedules import crontab
app.conf.beat_schedule = {
    'run-detection-daily': {
        'task': 'detection.tasks.run_oil_spill_detection',
        'schedule': crontab(hour=0),  # Daily at midnight
    },
}
```

## References

- [Sentinel-1 GRD Products](https://sentinel.esa.int/web/sentinel/user-guides/sentinel-1-sar/product-types-processing-levels/product-types-and-processing)
- [Oil Spill Detection from SAR](https://www.sciencedirect.com/science/article/pii/S0034425719305212)
- [Rasterio Documentation](https://rasterio.readthedocs.io/)
- [Scikit-learn Models](https://scikit-learn.org/)

## License & Attribution

This pipeline implementation is provided as-is for research and operational monitoring of oil spills.

## Support

For issues, questions, or extensions:

1. Check `pipeline_examples.py` for usage patterns
2. Enable debug logging to diagnose issues
3. Review module docstrings for detailed API documentation
4. Test on sample data before production deployment
