#!/usr/bin/env python
"""
Continuous Real-Time Oil Spill Monitoring

Monitors real Sentinel-1 satellite data for oil spills in specified regions.
Runs continuously on schedule with fault tolerance.

Usage:
    python continuous_monitoring.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path


def setup_monitoring_regions():
    """Define regions to monitor with real Sentinel-1 data"""
    
    regions = {
        "Niger Delta": {
            "bbox": (5.0, 4.0, 7.0, 6.0),  # (min_lon, min_lat, max_lon, max_lat)
            "description": "Niger Delta, Nigeria - High oil activity region",
            "enabled": True
        },
        "Gulf of Mexico": {
            "bbox": (-90.0, 25.0, -88.0, 27.0),
            "description": "Gulf of Mexico - Major oil production area",
            "enabled": False  # Set to True to monitor
        },
        "North Sea": {
            "bbox": (2.0, 55.0, 4.0, 57.0),
            "description": "North Sea - Significant offshore operations",
            "enabled": False  # Set to True to monitor
        },
        "Caspian Sea": {
            "bbox": (50.0, 40.0, 55.0, 44.0),
            "description": "Caspian Sea - Important shipping lanes",
            "enabled": False  # Set to True to monitor
        }
    }
    
    return regions


def create_pipeline_for_region(region_name: str, bbox: tuple, model_path: str):
    """Create pipeline instance for a specific region"""
    
    from detection.pipeline_orchestrator import create_pipeline
    
    try:
        pipeline = create_pipeline(
            aoi_name=region_name,
            bbox=bbox,
            model_path=model_path
        )
        return pipeline
    except Exception as e:
        return None


def run_monitoring_iteration(regions: dict, model_path: str):
    """Run one complete monitoring iteration for all regions"""
    
    from detection.sentinel_hub_config import get_sentinel_hub_config
    
    # Check Sentinel Hub credentials
    config = get_sentinel_hub_config()
    if not config.is_configured():
        return False
    
    # Process each region
    results_summary = {
        "processed": 0,
        "detections": 0,
        "errors": 0,
        "regions": {}
    }
    
    for region_name, config_data in regions.items():
        if not config_data.get("enabled", False):
            continue
        
        try:
            # Create pipeline
            pipeline = create_pipeline_for_region(
                region_name,
                config_data['bbox'],
                model_path
            )
            
            if pipeline is None:
                results_summary["errors"] += 1
                continue
            
            # Run detection
            results = pipeline.run()
            
            # Check results
            if results and results.get("status") == "success":
                detections = len(results.get("detections", []))
                processing_time = results.get("processing_time_seconds", 0)
                
                results_summary["processed"] += 1
                results_summary["detections"] += detections
                results_summary["regions"][region_name] = {
                    "status": "success",
                    "detections": detections,
                    "time_seconds": processing_time
                }
            else:
                results_summary["errors"] += 1
        
        except Exception as e:
            results_summary["errors"] += 1
    
    return results_summary["errors"] == 0


def start_continuous_monitoring(interval_hours: int = 24, max_iterations: int = None):
    """
    Start continuous monitoring loop.
    
    Args:
        interval_hours: Hours between monitoring iterations (default 24)
        max_iterations: Max iterations to run (None = infinite)
    """
    
    import time
    
    # Verify model exists
    model_path = "ml_models/saved_models/oil_spill_detector.joblib"
    if not Path(model_path).exists():
        return False
    
    # Load regions
    regions = setup_monitoring_regions()
    
    iteration = 0
    interval_seconds = interval_hours * 3600
    
    try:
        while True:
            iteration += 1
            
            # Check max iterations
            if max_iterations and iteration > max_iterations:
                logger.info(f"Reached max iterations ({max_iterations})")
                break
            
            # Run monitoring
            success = run_monitoring_iteration(regions, model_path)
            
            # If next iteration would happen, sleep
            if max_iterations is None or iteration < max_iterations:
                # Sleep with progress updates
                for remaining in range(interval_seconds, 0, -3600):
                    try:
                        time.sleep(3600)  # Sleep 1 hour at a time
                    except KeyboardInterrupt:
                        return True
            else:
                break
    
    except KeyboardInterrupt:
        return True
    except Exception as e:
        return False


def main():
    """Main entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Continuous Real-Time Oil Spill Monitoring"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=24,
        help="Hours between monitoring iterations (default: 24)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum iterations to run (default: infinite)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run single test iteration"
    )
    
    args = parser.parse_args()
    
    if args.test:
        regions = setup_monitoring_regions()
        model_path = "ml_models/saved_models/oil_spill_detector.joblib"
        run_monitoring_iteration(regions, model_path)
    else:
        success = start_continuous_monitoring(
            interval_hours=args.interval,
            max_iterations=args.max_iterations
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
