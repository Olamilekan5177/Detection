from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

from detection.models import (
    SatelliteImage, OilSpillDetection, Alert, MonitoringRegion
)

@login_required
def dashboard_home(request):
    """Main dashboard view
    
    Why: Single-page overview of system status
    """
    # Time ranges
    now = timezone.now()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Overall statistics
    total_detections = OilSpillDetection.objects.count()
    recent_detections = OilSpillDetection.objects.filter(
        detection_date__gte=week_ago
    ).count()
    
    # Severity breakdown
    severity_stats = OilSpillDetection.objects.values('severity').annotate(
        count=Count('id')
    )
    
    # Recent unverified detections
    unverified = OilSpillDetection.objects.filter(
        verified=False
    ).order_by('-detection_date')[:10]
    
    # Active monitoring regions
    active_regions = MonitoringRegion.objects.filter(active=True).count()
    
    # Recent alerts
    recent_alerts = Alert.objects.order_by('-created_at')[:5]
    
    # Average confidence
    avg_confidence = OilSpillDetection.objects.aggregate(
        avg=Avg('confidence_score')
    )['avg'] or 0
    
    # Processing status
    total_images = SatelliteImage.objects.count()
    processed_images = SatelliteImage.objects.filter(processed=True).count()
    pending_images = total_images - processed_images
    
    # Calculate percentages for progress bars
    if total_images > 0:
        processed_percent = (processed_images / total_images) * 100
        pending_percent = (pending_images / total_images) * 100
    else:
        processed_percent = 0
        pending_percent = 0
    
    context = {
        'total_detections': total_detections,
        'recent_detections': recent_detections,
        'severity_stats': severity_stats,
        'unverified_detections': unverified,
        'active_regions': active_regions,
        'recent_alerts': recent_alerts,
        'avg_confidence': round(avg_confidence, 4),
        'total_images': total_images,
        'processed_images': processed_images,
        'pending_images': pending_images,
        'processed_percent': round(processed_percent, 1),
        'pending_percent': round(pending_percent, 1),
    }
    
    return render(request, 'dashboard/index.html', context)


@login_required
def detection_detail(request, detection_id):
    """Detailed view of a single detection"""
    detection = get_object_or_404(
        OilSpillDetection.objects.select_related('satellite_image'),
        id=detection_id
    )
    
    # Related detections (sorted by detection_date)
    nearby = OilSpillDetection.objects.exclude(id=detection.id).order_by('-detection_date')[:5]
    
    context = {
        'detection': detection,
        'nearby_detections': nearby,
    }
    
    return render(request, 'dashboard/detection_detail.html', context)


@login_required
def analytics(request):
    """Analytics and charts view"""
    
    # Get date range from request
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Detection trend data
    detections = OilSpillDetection.objects.filter(
        detection_date__gte=start_date
    )
    
    # Severity distribution over time
    severity_trend = detections.values('severity').annotate(
        count=Count('id')
    )
    
    context = {
        'days': days,
        'severity_trend': list(severity_trend),
        'total_in_period': detections.count(),
    }
    
    return render(request, 'dashboard/analytics.html', context)


@login_required
def map_view(request):
    """Interactive map view"""
    
    # Get all detections with coordinates
    detections = OilSpillDetection.objects.all()
    
    # Get monitoring regions
    regions = MonitoringRegion.objects.filter(active=True)
    
    context = {
        'detections': detections,
        'regions': regions,
    }
    
    return render(request, 'dashboard/map.html', context)


@login_required
def monitoring(request):
    """Real-time monitoring dashboard for operations team
    
    Shows:
    - Active alerts (unsent)
    - Recent satellite images
    - Detection history
    - Quick actions
    """
    
    # Get pending alerts (unsent)
    pending_alerts = Alert.objects.filter(
        sent=False
    ).select_related(
        'detection__satellite_image'
    ).order_by('-created_at')
    
    # Add confidence percentage and location formatting to alerts
    for alert in pending_alerts:
        alert.detection.confidence_percentage = round(alert.detection.confidence_score * 100, 1)
        # Format location
        if alert.detection.location and isinstance(alert.detection.location, dict):
            coords = alert.detection.location.get('coordinates', [0, 0])
            alert.detection.location_lat = round(coords[1], 4) if len(coords) > 1 else 0
            alert.detection.location_lon = round(coords[0], 4) if len(coords) > 0 else 0
    
    # Get recent images (most recent acquisitions)
    recent_images = SatelliteImage.objects.order_by('-acquisition_date')[:10]
    
    # Get recent detections
    recent_detections = OilSpillDetection.objects.select_related(
        'satellite_image'
    ).order_by('-detection_date')[:10]
    
    # Add confidence percentage and location formatting to detections
    for detection in recent_detections:
        detection.confidence_percentage = round(detection.confidence_score * 100, 1)
        # Format location
        if detection.location and isinstance(detection.location, dict):
            coords = detection.location.get('coordinates', [0, 0])
            detection.location_lat = round(coords[1], 4) if len(coords) > 1 else 0
            detection.location_lon = round(coords[0], 4) if len(coords) > 0 else 0
    
    # Summary stats
    total_images = SatelliteImage.objects.count()
    total_detections = OilSpillDetection.objects.count()
    
    context = {
        'alerts': pending_alerts,
        'images': recent_images,
        'detections': recent_detections,
        'total_images': total_images,
        'total_detections': total_detections,
        'pending_alerts': pending_alerts.count(),
    }
    
    return render(request, 'dashboard/monitoring.html', context)