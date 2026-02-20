from django.shortcuts import render
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import SatelliteImage, OilSpillDetection, Alert, MonitoringRegion
from .serializers import (
    SatelliteImageSerializer,
    OilSpillDetectionSerializer,
    AlertSerializer,
    MonitoringRegionSerializer
)
from .ml_inference import predict_oil_spill

try:
    from .tasks import process_satellite_image, check_monitoring_region
    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class SatelliteImageViewSet(viewsets.ModelViewSet):
    """API endpoints for satellite images"""
    
    queryset = SatelliteImage.objects.all()
    serializer_class = SatelliteImageSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by source
        source = self.request.query_params.get('source', None)
        if source:
            queryset = queryset.filter(source=source)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(acquisition_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(acquisition_date__lte=end_date)
        
        # Filter by processing status
        processed = self.request.query_params.get('processed', None)
        if processed is not None:
            queryset = queryset.filter(processed=processed.lower() == 'true')
        
        return queryset.order_by('-acquisition_date')
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Trigger processing of a satellite image
        
        Why: Allows manual triggering of analysis
        """
        image = self.get_object()
        
        if image.processed:
            return Response(
                {'message': 'Image already processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if HAS_CELERY:
            # Trigger Celery task
            task = process_satellite_image.delay(image.id)
            task_id = task.id
        else:
            task_id = 'celery-not-configured'
        
        return Response({
            'message': 'Processing started' if HAS_CELERY else 'Celery not configured',
            'task_id': task_id,
            'image_id': image.id
        })
    
    @action(detail=True, methods=['post'])
    def detect_spill(self, request, pk=None):
        """Use ML model to detect oil spills in satellite image
        
        ML inference endpoint.  Automatically creates OilSpillDetection if spill found.
        """
        image = self.get_object()
        
        # Get image file
        if not image.image_path:
            return Response(
                {'error': 'No image file associated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Make prediction
        result = predict_oil_spill(str(image.image_path))
        
        if result is None:
            return Response(
                {'error': 'Model not loaded or prediction failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        response_data = {
            'satellite_image_id': image.id,
            'has_oil_spill': result['has_oil_spill'],
            'confidence': result['confidence'],
            'probability': result['probability']
        }
        
        # If oil spill detected with confidence > 0.5, create Detection record
        if result['has_oil_spill'] and result['probability'] > 0.5:
            detection = OilSpillDetection.objects.create(
                satellite_image=image,
                confidence_score=result['probability'],
                location=image.center_point,
                area_size=100.0,  # Placeholder - would need refined calculation
                severity='HIGH' if result['probability'] > 0.7 else 'MEDIUM'
            )
            response_data['detection_created'] = True
            response_data['detection_id'] = detection.id
            response_data['status'] = 'oil_spill_detected'
            
            # Create alert
            alert = Alert.objects.create(
                detection=detection,
                message=f'Oil spill detected with {result["probability"]:.1%} confidence',
                sent=True
            )
            response_data['alert_id'] = alert.id
        else:
            response_data['detection_created'] = False
            response_data['status'] = 'no_oil_spill_detected'
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get statistics about satellite images"""
        total = self.get_queryset().count()
        processed = self.get_queryset().filter(processed=True).count()
        unprocessed = total - processed
        
        by_source = self.get_queryset().values('source').annotate(
            count=Count('id')
        )
        
        return Response({
            'total': total,
            'processed': processed,
            'unprocessed': unprocessed,
            'by_source': list(by_source)
        })


class OilSpillDetectionViewSet(viewsets.ModelViewSet):
    """API endpoints for oil spill detections"""
    
    queryset = OilSpillDetection.objects.select_related('satellite_image')
    serializer_class = OilSpillDetectionSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by severity
        severity = self.request.query_params.get('severity', None)
        if severity:
            queryset = queryset.filter(severity=severity.upper())
        
        # Filter by verification status
        verified = self.request.query_params.get('verified', None)
        if verified is not None:
            queryset = queryset.filter(verified=verified.lower() == 'true')
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(detection_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(detection_date__lte=end_date)
        
        # Filter by confidence threshold
        min_confidence = self.request.query_params.get('min_confidence', None)
        if min_confidence:
            queryset = queryset.filter(confidence_score__gte=float(min_confidence))
        
        # Note: Spatial filter (radius search) requires PostGIS
        # For SQLite-based development, spatial filters would need to be done in Python
        lat = self.request.query_params.get('lat', None)
        lon = self.request.query_params.get('lon', None)
        radius_km = self.request.query_params.get('radius', 100)  # km
        
        if lat and lon:
            # Simple haversine distance for SQLite (PostGIS would be automatic)
            import math
            lat, lon, radius_km = float(lat), float(lon), float(radius_km)
            
            # Filter in Python (not optimal but works with SQLite)
            def is_within_radius(detection):
                if not detection.location or 'coordinates' not in detection.location:
                    return False
                det_lon, det_lat = detection.location['coordinates']
                
                # Haversine distance roughly
                dx = (det_lon - lon) * 111
                dy = (det_lat - lat) * 111
                dist = math.sqrt(dx**2 + dy**2)
                return dist <= radius_km
            
            queryset = [d for d in queryset if is_within_radius(d)]
        
        return queryset.order_by('-detection_date') if isinstance(queryset, models.QuerySet) else sorted(queryset, key=lambda x: x.detection_date, reverse=True)
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Mark detection as verified
        
        Why: Human-in-the-loop verification reduces false positives
        """
        detection = self.get_object()
        
        is_false_positive = request.data.get('false_positive', False)
        notes = request.data.get('notes', '')
        
        detection.verified = True
        detection.false_positive = is_false_positive
        detection.verified_by = request.user
        detection.notes = notes
        detection.save()
        
        return Response({
            'message': 'Detection verified',
            'detection_id': detection.id,
            'false_positive': is_false_positive
        })

    @action(detail=True, methods=['post'])
    def unverify(self, request, pk=None):
        """Clear verification on a detection"""
        detection = self.get_object()

        detection.verified = False
        detection.false_positive = False
        detection.verified_by = None
        detection.verification_date = None
        detection.notes = ''
        detection.save()

        return Response({
            'message': 'Detection unverified',
            'detection_id': detection.id
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get detection statistics"""
        queryset = self.get_queryset()
        
        total = queryset.count()
        by_severity = queryset.values('severity').annotate(count=Count('id'))
        
        # Recent detections (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent = queryset.filter(detection_date__gte=week_ago).count()
        
        # Average confidence
        avg_confidence = queryset.aggregate(
            avg=models.Avg('confidence_score')
        )['avg'] or 0
        
        # Verification stats
        verified = queryset.filter(verified=True).count()
        false_positives = queryset.filter(false_positive=True).count()
        
        return Response({
            'total': total,
            'recent_7_days': recent,
            'by_severity': list(by_severity),
            'average_confidence': round(avg_confidence, 4),
            'verified': verified,
            'false_positives': false_positives
        })
    
    @action(detail=False, methods=['get'])
    def heatmap_data(self, request):
        """Get data for heatmap visualization
        
        Why: Shows geographic distribution of detections
        """
        queryset = self.get_queryset()
        
        # Get coordinates and metadata
        data = []
        for detection in queryset:
            # Handle both GIS Point objects and JSON location format
            if hasattr(detection.location, 'x'):  # GIS Point
                lat, lon = detection.location.y, detection.location.x
            elif isinstance(detection.location, dict):  # JSON format
                coords = detection.location.get('coordinates', [0, 0])
                lon, lat = coords[0], coords[1]
            else:
                continue  # Skip if location is malformed
            
            data.append({
                'lat': lat,
                'lon': lon,
                'severity': detection.severity,
                'confidence': detection.confidence_score,
                'area': detection.area_size,
                'date': detection.detection_date.isoformat()
            })
        
        return Response(data)


class MonitoringRegionViewSet(viewsets.ModelViewSet):
    """API endpoints for monitoring regions"""
    
    queryset = MonitoringRegion.objects.all()
    serializer_class = MonitoringRegionSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        """Set creator when creating region"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def check_now(self, request, pk=None):
        """Manually trigger monitoring check
        
        Why: Allows on-demand monitoring instead of waiting for schedule
        """
        region = self.get_object()
        
        if HAS_CELERY:
            # Trigger Celery task
            task = check_monitoring_region.delay(region.id)
            task_id = task.id
        else:
            task_id = 'celery-not-configured'
        
        # Update last checked
        region.last_checked = timezone.now()
        region.save()
        
        return Response({
            'message': 'Monitoring check started',
            'task_id': task_id,
            'region_id': region.id
        })
    
    @action(detail=True, methods=['get'])
    def detections(self, request, pk=None):
        """Get all detections within this region"""
        region = self.get_object()
        
        # For SQLite, we need to filter in Python since JSON doesn't support spatial queries
        # In production with PostGIS: location__within=region.boundary
        detections = OilSpillDetection.objects.order_by('-detection_date')
        
        # Filter detections within polygon boundary
        if isinstance(region.boundary, dict) and 'coordinates' in region.boundary:
            # Simple point-in-polygon for rectangular boundaries (simplified)
            coords = region.boundary.get('coordinates', [[[[0, 0]]]])
            if coords and coords[0]:
                lons = [c[0] for ring in coords for c in ring]
                lats = [c[1] for ring in coords for c in ring]
                min_lon, max_lon = min(lons), max(lons)
                min_lat, max_lat = min(lats), max(lats)
                
                filtered = []
                for d in detections:
                    if isinstance(d.location, dict) and 'coordinates' in d.location:
                        lon, lat = d.location['coordinates']
                        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                            filtered.append(d)
                detections = filtered
        
        serializer = OilSpillDetectionSerializer(detections, many=True)
        return Response(serializer.data)


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints for alerts (read-only)"""
    
    queryset = Alert.objects.select_related('detection')
    serializer_class = AlertSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by sent status
        sent = self.request.query_params.get('sent', None)
        if sent is not None:
            queryset = queryset.filter(sent=sent.lower() == 'true')
        
        return queryset.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Mark alert as acknowledged"""
        alert = self.get_object()

        if not alert.acknowledged:
            alert.acknowledged = True
            alert.acknowledged_at = timezone.now()
            if request.user.is_authenticated:
                alert.acknowledged_by = request.user
            alert.save()

        return Response({
            'message': 'Alert acknowledged',
            'alert_id': alert.id,
            'acknowledged': alert.acknowledged
        })

    @action(detail=True, methods=['post'])
    def unacknowledge(self, request, pk=None):
        """Clear alert acknowledgement"""
        alert = self.get_object()

        alert.acknowledged = False
        alert.acknowledged_at = None
        alert.acknowledged_by = None
        alert.save()

        return Response({
            'message': 'Alert unacknowledged',
            'alert_id': alert.id,
            'acknowledged': alert.acknowledged
        })

    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """Mark alert as reported to authorities"""
        alert = self.get_object()

        if not alert.sent:
            alert.sent = True
            alert.sent_at = timezone.now()
            alert.save()

        return Response({
            'message': 'Alert reported to authorities',
            'alert_id': alert.id,
            'reported': alert.sent
        })

    @action(detail=True, methods=['post'])
    def unreport(self, request, pk=None):
        """Clear report status"""
        alert = self.get_object()

        alert.sent = False
        alert.sent_at = None
        alert.save()

        return Response({
            'message': 'Alert unreported',
            'alert_id': alert.id,
            'reported': alert.sent
        })