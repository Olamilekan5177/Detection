from rest_framework import serializers
from .models import SatelliteImage, OilSpillDetection, Alert, MonitoringRegion

# Try to use GeoFeatureModelSerializer if available (requires djangorestframework-gis)
try:
    from rest_framework_gis.serializers import GeoFeatureModelSerializer
    HAS_GIS_SERIALIZERS = True
except ImportError:
    HAS_GIS_SERIALIZERS = False

# Fallback to standard serializers for SQLite compatibility
class SatelliteImageSerializer(serializers.ModelSerializer):
    """Serializer for SatelliteImage"""
    
    detection_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SatelliteImage
        fields = [
            'id', 'image_id', 'source', 'acquisition_date',
            'upload_date', 'cloud_coverage', 'resolution',
            'processed', 'detection_count', 'thumbnail_path',
            'center_point', 'bounds', 'metadata'
        ]
    
    def get_detection_count(self, obj):
        return obj.detections.count()


class OilSpillDetectionSerializer(serializers.ModelSerializer):
    """Serializer for OilSpillDetection"""
    
    satellite_image_id = serializers.CharField(
        source='satellite_image.image_id',
        read_only=True
    )
    verified_by_username = serializers.CharField(
        source='verified_by.username',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = OilSpillDetection
        fields = [
            'id', 'satellite_image_id', 'detection_date',
            'confidence_score', 'area_size', 'severity',
            'verified', 'false_positive', 'verified_by_username',
            'notes', 'cropped_image_path', 'heatmap_path',
            'location', 'geojson_data'
        ]


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert"""
    
    detection_severity = serializers.CharField(
        source='detection.severity',
        read_only=True
    )
    detection_location = serializers.SerializerMethodField()
    
    class Meta:
        model = Alert
        fields = [
            'id', 'detection', 'detection_severity',
            'detection_location', 'created_at', 'message',
            'sent', 'sent_at', 'recipients', 'acknowledged'
        ]
    
    def get_detection_location(self, obj):
        # Handle both GIS Point and JSON location format
        if hasattr(obj.detection.location, 'x'):  # GIS Point
            return {
                'lat': obj.detection.location.y,
                'lon': obj.detection.location.x
            }
        elif isinstance(obj.detection.location, dict):  # JSON format
            coords = obj.detection.location.get('coordinates', [0, 0])
            return {
                'lon': coords[0],
                'lat': coords[1]
            }
        return {'lat': 0, 'lon': 0}


class MonitoringRegionSerializer(serializers.ModelSerializer):
    """Serializer for MonitoringRegion"""
    
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    detection_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MonitoringRegion
        fields = [
            'id', 'name', 'description', 'active',
            'check_interval', 'last_checked', 'alert_threshold',
            'created_by_username', 'created_at', 'updated_at',
            'detection_count', 'boundary'
        ]
    
    def get_detection_count(self, obj):
        # Simplified count without spatial queries
        detections = OilSpillDetection.objects.all()
        
        # Filter by boundary if it's a valid polygon
        if isinstance(obj.boundary, dict) and 'coordinates' in obj.boundary:
            coords = obj.boundary.get('coordinates', [[[[0, 0]]]])
            if coords and coords[0]:
                lons = [c[0] for ring in coords for c in ring]
                lats = [c[1] for ring in coords for c in ring]
                min_lon, max_lon = min(lons), max(lons)
                min_lat, max_lat = min(lats), max(lats)
                
                count = 0
                for d in detections:
                    if isinstance(d.location, dict) and 'coordinates' in d.location:
                        lon, lat = d.location['coordinates']
                        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                            count += 1
                return count
        
        return 0