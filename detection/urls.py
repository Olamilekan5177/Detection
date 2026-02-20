from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'satellite-images', views.SatelliteImageViewSet)
router.register(r'detections', views.OilSpillDetectionViewSet)
router.register(r'monitoring-regions', views.MonitoringRegionViewSet)
router.register(r'alerts', views.AlertViewSet)

app_name = 'detection'

urlpatterns = [
    path('', include(router.urls)),
]