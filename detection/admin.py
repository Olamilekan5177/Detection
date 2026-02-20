from django.contrib import admin
from .models import SatelliteImage, OilSpillDetection, Alert, MonitoringRegion

@admin.register(SatelliteImage)
class SatelliteImageAdmin(admin.ModelAdmin):
    list_display = ('image_id', 'source', 'acquisition_date', 'cloud_coverage', 'resolution', 'processed')
    list_filter = ('source', 'acquisition_date', 'processed')
    search_fields = ('image_id',)
    readonly_fields = ('upload_date', 'processing_date')

@admin.register(OilSpillDetection)
class OilSpillDetectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'satellite_image', 'confidence_score', 'severity', 'verified', 'detection_date')
    list_filter = ('severity', 'verified', 'detection_date')
    search_fields = ('id',)
    readonly_fields = ('detection_date',)

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'detection', 'sent', 'sent_at')
    list_filter = ('sent', 'sent_at')
    search_fields = ('id',)
    readonly_fields = ('created_at',)

@admin.register(MonitoringRegion)
class MonitoringRegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'created_at')
    list_filter = ('active', 'created_at')
    search_fields = ('name',)
