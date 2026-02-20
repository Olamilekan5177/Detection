from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

def default_point():
    return {'type': 'Point', 'coordinates': [0, 0]}

def default_polygon():
    return {'type': 'Polygon', 'coordinates': [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}

class SatelliteImage(models.Model):
    """Satellite image ingestion and metadata"""
    
    SOURCE_CHOICES = [
        ('SENTINEL', 'Sentinel-1/2'),
        ('LANDSAT', 'Landsat 8/9'),
        ('CUSTOM', 'Custom Upload'),
    ]
    
    image_id = models.CharField(max_length=255, unique=True, db_index=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    acquisition_date = models.DateTimeField(db_index=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    
    # Image metadata
    cloud_coverage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Cloud coverage percentage"
    )
    resolution = models.FloatField(help_text="Spatial resolution in meters")
    
    # Processing status
    processed = models.BooleanField(default=False, db_index=True)
    processing_date = models.DateTimeField(null=True, blank=True)
    
    # File paths
    image_path = models.FileField(upload_to='satellite_images/', null=True, blank=True)
    thumbnail_path = models.FileField(upload_to='thumbnails/', null=True, blank=True)
    
    # Geographic data - stored as GeoJSON for compatibility
    center_point = models.JSONField(
        default=default_point,
        help_text="Center point as GeoJSON Point"
    )
    bounds = models.JSONField(
        default=default_polygon,
        help_text="Image bounds as GeoJSON Polygon"
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-acquisition_date']
        indexes = [
            models.Index(fields=['-acquisition_date']),
            models.Index(fields=['source', 'processed']),
        ]
    
    def __str__(self):
        return f"{self.image_id} ({self.source}) - {self.acquisition_date}"


class OilSpillDetection(models.Model):
    """Detected oil spills from ML model"""
    
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    
    satellite_image = models.ForeignKey(
        SatelliteImage,
        on_delete=models.CASCADE,
        related_name='detections'
    )
    
    # Detection metadata
    detection_date = models.DateTimeField(auto_now_add=True, db_index=True)
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="ML model confidence score"
    )
    
    # Spill characteristics
    location = models.JSONField(
        default=default_point,
        help_text="Detection location as GeoJSON Point"
    )
    area_size = models.FloatField(help_text="Estimated spill area in km²")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='MEDIUM')
    
    # Verification
    verified = models.BooleanField(default=False, db_index=True)
    false_positive = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_detections'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    # Analysis outputs
    cropped_image_path = models.FileField(upload_to='detections/cropped/', null=True, blank=True)
    heatmap_path = models.FileField(upload_to='detections/heatmaps/', null=True, blank=True)
    geojson_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-detection_date']
        indexes = [
            models.Index(fields=['-detection_date']),
            models.Index(fields=['verified', 'false_positive']),
            models.Index(fields=['confidence_score']),
        ]
    
    def __str__(self):
        return f"Spill at {self.location} - {self.severity} (Confidence: {self.confidence_score:.2f})"
    
    @property
    def latitude(self):
        """Extract latitude from GeoJSON location"""
        try:
            return round(self.location['coordinates'][1], 6) if self.location else 0
        except (KeyError, IndexError, TypeError):
            return 0
    
    @property
    def longitude(self):
        """Extract longitude from GeoJSON location"""
        try:
            return round(self.location['coordinates'][0], 6) if self.location else 0
        except (KeyError, IndexError, TypeError):
            return 0
    
    @property
    def lat_lon_string(self):
        """Format location as 'Lat, Lon' string"""
        try:
            coords = self.location.get('coordinates', [0, 0])
            if len(coords) >= 2:
                return f"{coords[1]:.4f}, {coords[0]:.4f}"
            return "Unknown"
        except (ValueError, TypeError, KeyError, AttributeError):
            return "Unknown"


class MonitoringRegion(models.Model):
    """Geographic regions to monitor for oil spills"""
    
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    
    # Geographic boundary - stored as GeoJSON
    boundary = models.JSONField(
        default=default_polygon,
        help_text="Region boundary as GeoJSON Polygon"
    )
    
    # Monitoring settings
    active = models.BooleanField(default=True, db_index=True)
    check_interval = models.IntegerField(
        default=24,
        help_text="Check interval in hours"
    )
    last_checked = models.DateTimeField(null=True, blank=True)
    
    # Alert settings
    alert_threshold = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Confidence threshold for alerts"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='monitoring_regions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Alert(models.Model):
    """Alerts triggered by detections"""
    
    detection = models.OneToOneField(
        OilSpillDetection,
        on_delete=models.CASCADE,
        related_name='alert'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    
    # Notification tracking
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    recipients = models.JSONField(
        default=list,
        help_text="List of email recipients"
    )
    
    # Response tracking
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Alert for {self.detection.location} - {self.created_at}"
