from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('detection/<int:detection_id>/', views.detection_detail, name='detection_detail'),
    path('analytics/', views.analytics, name='analytics'),
    path('map/', views.map_view, name='map'),
    path('monitoring/', views.monitoring, name='monitoring'),
]