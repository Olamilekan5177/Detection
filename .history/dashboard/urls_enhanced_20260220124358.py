"""
Enhanced Dashboard URLs - Integrated with Oil Spill Detection Pipeline

Maps URLpaths to views for:
- Main dashboard
- Real-time monitoring
- Detection results map
- Statistics & analytics
- Region management
- API endpoints
"""

from django.urls import path
from . import views_enhanced as views

app_name = 'dashboard'

# Main dashboard views
urlpatterns = [
    # Dashboard home
    path('', views.dashboard_home, name='dashboard-home'),
    
    # Detection views
    path('detections/map/', views.detections_map, name='detections-map'),
    path('detection/<str:detection_id>/', views.detection_details, name='detection-details'),
    
    # Statistics
    path('statistics/', views.statistics, name='statistics'),
    
    # Regions management
    path('regions/', views.regions_management, name='regions-management'),
    
    # API endpoints
    path('api/system-status/', views.api_system_status, name='api-system-status'),
    path('api/recent-detections/', views.api_recent_detections, name='api-recent-detections'),
    path('api/detections-geojson/', views.api_detections_geojson, name='api-detections-geojson'),
    path('api/regions/add/', views.add_region, name='api-add-region'),
    path('api/regions/<str:region_name>/toggle/', views.toggle_region, name='api-toggle-region'),
]
