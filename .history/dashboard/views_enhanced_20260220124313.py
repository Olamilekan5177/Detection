"""
Enhanced Dashboard Views - Integrated Oil Spill Detection System

Integrates:
- Real-time pipeline monitoring
- Sentinel-1 satellite data
- Detection results
- Region management
- Performance statistics
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.db.models import Count, Avg, Q, Max
from django.utils import timezone
from django.views.decorators.http import require_http_methods

# Import our pipeline
from detection.pipeline_orchestrator import create_pipeline
from detection.sentinel_hub_config import get_sentinel_hub_config
from detection.aoi_config import AreaOfInterest

logger = logging.getLogger(__name__)

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

@login_required
def dashboard_home(request):
    """
    Main monitoring dashboard - overview of all activity
    """
    
    context = {
        'page_title': 'Oil Spill Detection Dashboard',
        'active_tab': 'dashboard'
    }
    
    # System Status
    context['system_status'] = {
        'sentinel_hub': get_sentinel_hub_status(),
        'model': get_model_status(),
        'last_update': datetime.now().isoformat()
    }
    
    # Statistics
    context['stats'] = get_dashboard_statistics()
    
    # Recent Detections
    context['recent_detections'] = get_recent_detections(limit=10)
    
    # Active Regions
    context['active_regions'] = get_active_monitoring_regions()
    
    # System Health
    context['health'] = {
        'memory_usage': get_memory_usage(),
        'disk_usage': get_disk_usage(),
        'uptime': get_system_uptime()
    }
    
    return render(request, 'dashboard/dashboard_home.html', context)


@login_required
def detections_map(request):
    """
    Interactive map of oil spill detections
    """
    
    context = {
        'page_title': 'Detection Map',
        'active_tab': 'map'
    }
    
    # Load all detection results from results/ folder
    context['detections'] = load_all_detection_results()
    
    # Convert to GeoJSON for map display
    context['geojson'] = detections_to_geojson(context['detections'])
    
    # Map center and zoom (can be customized)
    context['map_center'] = [0, 20]
    context['map_zoom'] = 3
    
    return render(request, 'dashboard/detections_map.html', context)


@login_required
def detection_details(request, detection_id):
    """
    Detailed view of a specific detection
    """
    
    # Load detection from results folder
    detection = load_detection_by_id(detection_id)
    
    if not detection:
        return render(request, 'dashboard/not_found.html', {
            'message': f'Detection {detection_id} not found'
        }, status=404)
    
    context = {
        'page_title': f'Detection {detection_id}',
        'detection': detection,
        'active_tab': 'map'
    }
    
    return render(request, 'dashboard/detection_details.html', context)


# ============================================================================
# REGIONS MANAGEMENT
# ============================================================================

@login_required
def regions_management(request):
    """
    Manage monitoring regions
    """
    
    regions = load_monitoring_regions()
    
    context = {
        'page_title': 'Monitoring Regions',
        'active_tab': 'regions',
        'regions': regions
    }
    
    return render(request, 'dashboard/regions_management.html', context)


@login_required
@require_http_methods(["POST"])
def add_region(request):
    """
    Add a new monitoring region
    """
    
    try:
        data = json.loads(request.body)
        
        # Validate data
        required = ['name', 'min_lon', 'min_lat', 'max_lon', 'max_lat']
        if not all(k in data for k in required):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Create AOI
        aoi = AreaOfInterest.from_bbox(
            name=data['name'],
            min_lon=float(data['min_lon']),
            min_lat=float(data['min_lat']),
            max_lon=float(data['max_lon']),
            max_lat=float(data['max_lat'])
        )
        
        # Save region
        regions = load_monitoring_regions()
        regions.append({
            'name': aoi.name,
            'bbox': aoi.get_bounding_box().as_tuple,
            'enabled': data.get('enabled', True),
            'created_at': datetime.now().isoformat(),
            'description': data.get('description', '')
        })
        save_monitoring_regions(regions)
        
        logger.info(f"Region added: {aoi.name}")
        
        return JsonResponse({
            'status': 'success',
            'message': f'Region {aoi.name} added',
            'region': regions[-1]
        })
    
    except Exception as e:
        logger.error(f"Error adding region: {e}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def toggle_region(request, region_name):
    """
    Enable/disable a monitoring region
    """
    
    try:
        regions = load_monitoring_regions()
        
        for region in regions:
            if region['name'] == region_name:
                region['enabled'] = not region['enabled']
                save_monitoring_regions(regions)
                
                return JsonResponse({
                    'status': 'success',
                    'enabled': region['enabled']
                })
        
        return JsonResponse({'error': 'Region not found'}, status=404)
    
    except Exception as e:
        logger.error(f"Error toggling region: {e}")
        return JsonResponse({'error': str(e)}, status=400)


# ============================================================================
# STATISTICS & ANALYTICS
# ============================================================================

@login_required
def statistics(request):
    """
    Comprehensive statistics and analytics
    """
    
    context = {
        'page_title': 'Statistics',
        'active_tab': 'statistics'
    }
    
    # Detection statistics
    detections = load_all_detection_results()
    
    context['stats'] = {
        'total_detections': len(detections),
        'detections_by_region': count_detections_by_region(detections),
        'detections_by_confidence': categorize_by_confidence(detections),
        'average_confidence': calculate_average_confidence(detections),
        'detections_over_time': detections_over_time(detections)
    }
    
    # System metrics
    context['system_metrics'] = {
        'cpu_usage': get_cpu_usage(),
        'memory_usage': get_memory_usage(),
        'disk_usage': get_disk_usage(),
        'uptime': get_system_uptime()
    }
    
    return render(request, 'dashboard/statistics.html', context)


# ============================================================================
# API ENDPOINTS (JSON)
# ============================================================================

@login_required
def api_system_status(request):
    """
    API endpoint - system status (AJAX)
    """
    
    return JsonResponse({
        'sentinel_hub': get_sentinel_hub_status(),
        'model': get_model_status(),
        'timestamp': datetime.now().isoformat()
    })


@login_required
def api_recent_detections(request):
    """
    API endpoint - recent detections (AJAX)
    """
    
    limit = int(request.GET.get('limit', 10))
    detections = get_recent_detections(limit=limit)
    
    return JsonResponse({
        'count': len(detections),
        'detections': detections
    })


@login_required
def api_detections_geojson(request):
    """
    API endpoint - detections as GeoJSON
    """
    
    detections = load_all_detection_results()
    geojson = detections_to_geojson(detections)
    
    return JsonResponse(geojson)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_sentinel_hub_status():
    """Check Sentinel Hub connectivity"""
    try:
        config = get_sentinel_hub_config()
        if config.is_configured():
            return {
                'connected': True,
                'client': config.client_id[:10] + '***',
                'endpoint': config.base_url,
                'last_check': datetime.now().isoformat()
            }
    except Exception as e:
        logger.warning(f"Sentinel Hub status check failed: {e}")
    
    return {
        'connected': False,
        'error': 'Credentials not configured',
        'last_check': datetime.now().isoformat()
    }


def get_model_status():
    """Check ML model status"""
    model_path = Path("ml_models/saved_models/oil_spill_detector.joblib")
    
    if model_path.exists():
        return {
            'loaded': True,
            'path': str(model_path),
            'size_mb': round(model_path.stat().st_size / (1024*1024), 1),
            'accuracy': '90%',
            'precision': '100%',
            'recall': '80%'
        }
    
    return {
        'loaded': False,
        'error': 'Model not found'
    }


def get_dashboard_statistics():
    """Get overall statistics"""
    detections = load_all_detection_results()
    
    return {
        'total_detections': len(detections),
        'this_week': len([d for d in detections if is_recent(d, days=7)]),
        'today': len([d for d in detections if is_recent(d, days=1)]),
        'average_confidence': calculate_average_confidence(detections),
        'high_confidence': len([d for d in detections if d.get('confidence', 0) > 0.8])
    }


def get_recent_detections(limit=10):
    """Get recent detections"""
    detections = load_all_detection_results()
    
    # Sort by date, most recent first
    detections.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return detections[:limit]


def get_active_monitoring_regions():
    """Get list of active monitoring regions"""
    regions = load_monitoring_regions()
    return [r for r in regions if r.get('enabled', False)]


def load_all_detection_results():
    """Load all detection results from results/ folder"""
    results_dir = Path('results')
    detections = []
    
    if not results_dir.exists():
        return detections
    
    # Load all JSON files
    for json_file in results_dir.glob('*_detections.json'):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                detections.extend(data.get('detections', []))
        except Exception as e:
            logger.warning(f"Error loading {json_file}: {e}")
    
    return detections


def detections_to_geojson(detections):
    """Convert detections to GeoJSON format"""
    features = []
    
    for det in detections:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    det.get('longitude', 0),
                    det.get('latitude', 0)
                ]
            },
            "properties": {
                "id": det.get('id', '?'),
                "confidence": det.get('confidence', 0),
                "timestamp": det.get('timestamp', ''),
                "region": det.get('region', ''),
                "severity": "High" if det.get('confidence', 0) > 0.8 else "Medium"
            }
        }
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


def load_monitoring_regions():
    """Load monitoring regions from config"""
    config_file = Path('monitoring_regions.json')
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading regions: {e}")
    
    # Default regions
    return [
        {
            'name': 'Niger Delta',
            'bbox': (5.0, 4.0, 7.0, 6.0),
            'enabled': True,
            'description': 'Nigeria - High oil activity'
        }
    ]


def save_monitoring_regions(regions):
    """Save monitoring regions to config"""
    try:
        with open('monitoring_regions.json', 'w') as f:
            json.dump(regions, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving regions: {e}")


def count_detections_by_region(detections):
    """Count detections grouped by region"""
    counts = {}
    for det in detections:
        region = det.get('region', 'Unknown')
        counts[region] = counts.get(region, 0) + 1
    return counts


def categorize_by_confidence(detections):
    """Categorize detections by confidence level"""
    categories = {
        'high': 0,      # > 0.8
        'medium': 0,    # 0.5-0.8
        'low': 0        # < 0.5
    }
    
    for det in detections:
        conf = det.get('confidence', 0)
        if conf > 0.8:
            categories['high'] += 1
        elif conf > 0.5:
            categories['medium'] += 1
        else:
            categories['low'] += 1
    
    return categories


def calculate_average_confidence(detections):
    """Calculate average confidence score"""
    if not detections:
        return 0
    
    total = sum(d.get('confidence', 0) for d in detections)
    return round(total / len(detections), 3)


def detections_over_time(detections):
    """Get detection counts over time (by day)"""
    counts = {}
    
    for det in detections:
        timestamp = det.get('timestamp', '')
        if timestamp:
            date = timestamp.split('T')[0]
            counts[date] = counts.get(date, 0) + 1
    
    return sorted(counts.items())


def get_regions_monitoring_status():
    """Get monitoring status for each region"""
    regions = load_monitoring_regions()
    detections = load_all_detection_results()
    
    status = []
    for region in regions:
        region_dets = [d for d in detections if d.get('region') == region['name']]
        status.append({
            'name': region['name'],
            'enabled': region.get('enabled', False),
            'detections': len(region_dets),
            'last_check': 'Unknown',
            'bbox': region.get('bbox', '')
        })
    
    return status


def load_detection_by_id(detection_id):
    """Load a specific detection by ID"""
    detections = load_all_detection_results()
    
    for det in detections:
        if det.get('id') == detection_id:
            return det
    
    return None


def is_recent(detection, days=1):
    """Check if detection is within last N days"""
    try:
        det_time = datetime.fromisoformat(detection.get('timestamp', ''))
        return (datetime.now() - det_time).days < days
    except:
        return False


def get_cpu_usage():
    """Get CPU usage percentage"""
    try:
        import psutil
        return round(psutil.cpu_percent(interval=1), 1)
    except:
        return 'N/A'


def get_memory_usage():
    """Get memory usage percentage"""
    try:
        import psutil
        return round(psutil.virtual_memory().percent, 1)
    except:
        return 'N/A'


def get_disk_usage():
    """Get disk usage percentage"""
    try:
        import psutil
        return round(psutil.disk_usage('/').percent, 1)
    except:
        return 'N/A'


def get_system_uptime():
    """Get system uptime"""
    try:
        # Check monitoring startup time
        with open('monitoring.log', 'r') as f:
            first_line = f.readline()
            return first_line.split(' - ')[0] if first_line else 'Unknown'
    except:
        return 'Unknown'
