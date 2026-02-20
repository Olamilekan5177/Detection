from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

def default_point():
    return {'type': 'Point', 'coordinates': [0, 0]}

def default_polygon():
    return {'type': 'Polygon', 'coordinates': [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}

class SatelliteImage(models.Model):
    """Store satellite image metadata"""
    
    SENTINEL_1 = 'S1'
    SENTINEL_2 = 'S2'
    LANDSAT = 'LS'
    
    SOURCE_CHOICES = [
        (SENTINEL_1, 'Sentinel-1 (SAR)'),
        (SENTINEL_2, 'Sentinel-2 (Optical)'),
        (LANDSAT, 'Landsat'),
    ]
    
    image_id = models.CharField(max_length=255, unique=True)
    source = models.CharField(max_length=2, choices=SOURCE_CHOICES)
    acquisition_date = models.DateTimeField()
    upload_date = models.DateTimeField(auto_now_add=True)
    
    # Spatial data - stored as GeoJSON JSON for SQLite compatibility
    bounds = models.JSONField(
        default=default_polygon,
        help_text="Geographic bounds of image as GeoJSON Polygon"
    )
    center_point = models.JSONField(
        default=default_point,
        help_text="Center point as GeoJSON Point"
    )
    
    # File paths
    image_path = models.CharField(max_length=500)
    thumbnail_path = models.CharField(max_length=500, blank=True)
    
    # Metadata
    cloud_coverage = models.FloatField(null=True, blank=True)
    resolution = models.FloatField(help_text="Spatial resolution in meters")
    
    processed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-acquisition_date']
        indexes = [
            models.Index(fields=['-acquisition_date']),
            models.Index(fields=['source']),
        ]
    
    def __str__(self):
        return f"{self.source} - {self.image_id}"


class OilSpillDetection(models.Model):
    """Store oil spill detection results"""
    
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'
    
    SEVERITY_CHOICES = [
        (LOW, 'Low'),
        (MEDIUM, 'Medium'),
        (HIGH, 'High'),
        (CRITICAL, 'Critical'),
    ]
    
    satellite_image = models.ForeignKey(
        SatelliteImage, 
        on_delete=models.CASCADE,
        related_name='detections'
    )
    
    # Detection details
    detection_date = models.DateTimeField(auto_now_add=True)
    confidence_score = models.FloatField(
        help_text="ML model confidence (0-1)"
    )
    
    # Spatial information - stored as GeoJSON for SQLite compatibility
    location = models.JSONField(
        default=default_point,
        help_text="Center point of detection as GeoJSON Point"
    )
    affected_area = models.JSONField(
        default=default_polygon,
        help_text="Polygon of detected oil spill as GeoJSON"
    )
    area_size = models.FloatField(
        help_text="Estimated area in square kilometers"
    )
    
    # Classification
    severity = models.CharField(
        max_length=10, 
        choices=SEVERITY_CHOICES,
        default=MEDIUM
    )
    
    # Analysis results
    cropped_image_path = models.CharField(max_length=500)
    heatmap_path = models.CharField(max_length=500, blank=True)
    
    # Status
    verified = models.BooleanField(default=False)
    false_positive = models.BooleanField(default=False)
    
    # User interaction
    verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-detection_date']
        indexes = [
            models.Index(fields=['-detection_date']),
            models.Index(fields=['severity']),
            models.Index(fields=['verified']),
        ]
    
    def __str__(self):
        return f"Detection {self.id} - {self.severity} ({self.confidence_score:.2f})"
    
    def save(self, *args, **kwargs):
        # Auto-assign severity based on area and confidence
        if self.area_size > 100:
            self.severity = self.CRITICAL
        elif self.area_size > 50:
            self.severity = self.HIGH
        elif self.area_size > 10:
            self.severity = self.MEDIUM
        else:
            self.severity = self.LOW
        
        super().save(*args, **kwargs)


class Alert(models.Model):
    """Alert notifications for detections"""
    
    detection = models.ForeignKey(
        OilSpillDetection,
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Recipients (could be expanded to email/SMS)
    recipients = models.JSONField(default=list)
    
    def __str__(self):
        return f"Alert for Detection {self.detection.id}"


class MonitoringRegion(models.Model):
    """Define regions to monitor"""
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Geographic area - stored as GeoJSON for SQLite compatibility
    boundary = models.JSONField(
        default=default_polygon,
        help_text="Region boundary as GeoJSON Polygon"
    )
    
    # Monitoring settings
    active = models.BooleanField(default=True)
    check_interval = models.IntegerField(
        default=24,
        help_text="Check interval in hours"
    )
    last_checked = models.DateTimeField(null=True, blank=True)
    
    # Alert settings
    alert_threshold = models.FloatField(
        default=0.7,
        help_text="Confidence threshold for alerts"
    )
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name