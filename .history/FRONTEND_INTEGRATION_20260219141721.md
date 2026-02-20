# Frontend Integration Guide - Oil Spill Detection System

## Overview

The frontend integrates your complete oil spill detection pipeline with a Django web dashboard that displays:

- **Real-time monitoring status**
- **Sentinel-1 satellite data queries**
- **ML model predictions**
- **Interactive detection maps**
- **Region management**
- **System statistics & analytics**

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Web Dashboard (Django)                  │
│                                                           │
│  ┌──────────┬──────────┬──────────┬──────────┐           │
│  │ Dashboard│Monitoring│  Map     │Statistics│           │
│  │  Home    │ Status   │ View     │ Analytics│           │
│  └──────────┴──────────┴──────────┴──────────┘           │
│                          ↓                                │
├─────────────────────────────────────────────────────────┤
│              Enhanced Views (views_enhanced.py)           │
│                                                           │
│  - dashboard_home()                                      │
│  - monitoring_status()                                   │
│  - detections_map()                                      │
│  - statistics()                                          │
│  - regions_management()                                  │
│  - api_* endpoints                                       │
└─────────────────────────────────────────────────────────┘
         ↓                ↓                ↓
     ┌───────┐      ┌──────────┐      ┌─────────┐
     │Pipeline│      │Results   │      │Config   │
     │Data   │      │Files     │      │Files    │
     └───────┘      └──────────┘      └─────────┘
         ↓                ↓                ↓
  continuous_       results/          monitoring_
  monitoring.py     *.json            regions.json
```

---

## File Structure

```
dashboard/
├── views_enhanced.py              ← New integrated views (400+ lines)
├── urls_enhanced.py               ← New URL routing
├── templates/dashboard/
│   ├── dashboard_home.html        ← Main dashboard
│   ├── monitoring_status.html     ← Pipeline logs & status
│   ├── detections_map.html        ← Interactive map (Leaflet)
│   ├── regions_management.html    ← Region configuration
│   └── [existing templates]
└── [existing models, views, etc.]
```

---

## Setup Instructions

### Step 1: Install Enhanced Views

The enhanced views are already created:

- `dashboard/views_enhanced.py` - Complete view layer (400+ lines)
- `dashboard/urls_enhanced.py` - URL routing

### Step 2: Update Django URLs

Update your main `config/urls.py` to use the enhanced dashboard:

```python
# config/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('detection.urls')),
    path('dashboard/', include('dashboard.urls_enhanced')),  # ← Use enhanced URLs
    path('accounts/', include('users.urls')),
]
```

### Step 3: Install Frontend Dependencies

```powershell
# If using Leaflet for maps (already in templates)
pip install django-cors-headers  # For API calls

# Optional: Celery for background tasks
pip install celery
```

### Step 4: Run Django

```powershell
python manage.py runserver
```

Visit: `http://localhost:8000/dashboard/`

---

## Key Features

### 1. Dashboard Home (`/dashboard/`)

**Shows:**

- ✅ System status (Sentinel Hub, ML Model, Monitoring)
- ✅ Key statistics (total detections, this week, today)
- ✅ Recent detections in a table
- ✅ Active monitoring regions
- ✅ System health (CPU, memory, disk usage)

**Updates in real-time** via `api_system_status()` endpoint

### 2. Monitoring Status (`/dashboard/monitoring/status/`)

**Shows:**

- ✅ Pipeline state (running, idle, errors)
- ✅ Region-by-region monitoring status
- ✅ Real-time monitoring log (last 100 lines)
- ✅ Run count, error count, last run time

**Auto-refreshes** logs from `monitoring.log` file

### 3. Detection Map (`/dashboard/detections/map/`)

**Features:**

- ✅ Interactive Leaflet map showing all detections
- ✅ Color-coded markers (red=high, orange=medium, blue=low confidence)
- ✅ Marker size indicates confidence level
- ✅ Click markers to see detection details
- ✅ Sidebar listing all detections
- ✅ Filter by confidence level
- ✅ Popup with detection metadata

**Data source:** `results/` folder GeoJSON files

### 4. Region Management (`/dashboard/regions/`)

**Manage:**

- ✅ List all monitoring regions
- ✅ Enable/disable regions
- ✅ Add new regions (form modal)
- ✅ Quick-add popular regions (Niger Delta, Gulf of Mexico, etc.)
- ✅ View bounding boxes and statistics

**Updates:** `monitoring_regions.json` config file

### 5. Statistics (`/dashboard/statistics/`)

**Analytics:**

- ✅ Total detections
- ✅ Detections by region
- ✅ Detections by confidence level
- ✅ Average confidence score
- ✅ Detections over time (by day)
- ✅ System resource usage

---

## API Endpoints

All endpoints require Django login (@login_required)

### Get System Status

```
GET /dashboard/api/system-status/

Response:
{
  "sentinel_hub": {
    "connected": true,
    "client": "c45f1d8d-9***",
    "endpoint": "https://sh.dataspace.copernicus.eu"
  },
  "model": {
    "loaded": true,
    "size_mb": 576,
    "accuracy": "90%"
  },
  "monitoring": {
    "running": true,
    "run_count": 5,
    "errors": 0
  }
}
```

### Get Recent Detections

```
GET /dashboard/api/recent-detections/?limit=10

Response:
{
  "count": 10,
  "detections": [
    {
      "id": "001",
      "region": "Niger Delta",
      "latitude": 5.23,
      "longitude": 4.15,
      "confidence": 0.87,
      "timestamp": "2026-02-19T13:59:14"
    },
    ...
  ]
}
```

### Get Detections as GeoJSON

```
GET /dashboard/api/detections-geojson/

Response:
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [4.15, 5.23]
      },
      "properties": {
        "id": "001",
        "confidence": 0.87,
        "region": "Niger Delta",
        "severity": "High"
      }
    },
    ...
  ]
}
```

### Add Region

```
POST /dashboard/api/regions/add/

Body:
{
  "name": "Gulf of Mexico",
  "min_lon": -90,
  "min_lat": 25,
  "max_lon": -88,
  "max_lat": 27,
  "description": "Major oil production area",
  "enabled": true
}

Response:
{
  "status": "success",
  "message": "Region Gulf of Mexico added"
}
```

### Toggle Region

```
POST /dashboard/api/regions/{region_name}/toggle/

Response:
{
  "status": "success",
  "enabled": true
}
```

---

## Integration with Pipeline

### Data Flow

```
continuous_monitoring.py (running 24/7)
         ↓
   Executes pipeline for each region
         ↓
   Processes Sentinel-1 data
         ↓
   Makes predictions with ML model
         ↓
   Saves results to:
   ├── results/*.json
   ├── results/*.geojson
   ├── monitoring.log
   └── pipeline_state.json
         ↓
Dashboard reads these files
and displays in web interface
```

### Real-time Updates

The frontend doesn't need WebSocket. It reads from files that **continuous_monitoring.py** writes:

| File                      | Updated By    | Read By                | Purpose        |
| ------------------------- | ------------- | ---------------------- | -------------- |
| `monitoring.log`          | monitoring.py | monitoring_status view | Logs           |
| `pipeline_state.json`     | monitoring.py | dashboard_home view    | System state   |
| `results/*.json`          | pipeline      | detections_map view    | Detection data |
| `monitoring_regions.json` | web UI        | all views              | Region config  |

---

## Customization

### Change Dashboard Theme

Edit templates to customize colors/layout:

```html
<!-- Change badge color -->
<span class="badge badge-success">Active</span>
<!-- Green -->
<span class="badge badge-danger">High</span>
<!-- Red -->
<span class="badge badge-warning">Medium</span>
<!-- Orange -->
```

### Add Custom Metrics

Add new view and template:

```python
# In views_enhanced.py
@login_required
def custom_metric(request):
    data = calculate_metric()
    return render(request, 'dashboard/custom_metric.html', {'data': data})
```

### Auto-refresh Dashboard

Add AJAX polling in template:

```javascript
setInterval(() => {
  fetch("/dashboard/api/system-status/")
    .then((r) => r.json())
    .then((data) => updateUI(data));
}, 5000); // Refresh every 5 seconds
```

---

## Troubleshooting

### Problem: "Directory exists" error on templates

**Solution:** Templates are updated in-place, should work automatically

### Problem: 404 on `/dashboard/` routes

**Solution:** Make sure `urls_enhanced.py` is imported in `config/urls.py`:

```python
path('dashboard/', include('dashboard.urls_enhanced')),
```

### Problem: No detections showing on map

**Solution:** Ensure `continuous_monitoring.py` is running:

```powershell
.venv\Scripts\python.exe continuous_monitoring.py --interval 24
```

Check if `results/` folder exists with JSON files.

### Problem: Sentinel Hub shows "offline"

**Solution:** Verify credentials in `.env`:

```powershell
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('SENTINEL_HUB_CLIENT_ID'))"
```

---

## Next Steps

1. **Start monitoring:**

   ```powershell
   .venv\Scripts\python.exe continuous_monitoring.py --interval 24
   ```

2. **Run Django:**

   ```powershell
   python manage.py runserver
   ```

3. **Visit dashboard:**

   ```
   http://localhost:8000/dashboard/
   ```

4. **Configure regions:**
   - Go to `/dashboard/regions/`
   - Add monitoring regions
   - Enable automatic detection

5. **Monitor results:**
   - Check `/dashboard/monitoring/status/` for logs
   - View `/dashboard/detections/map/` for detection locations
   - Review `/dashboard/statistics/` for analytics

---

## System Diagram

```
        User Browser
             ↓
    ┌────────────────────┐
    │   Web Dashboard    │
    │   (Django)         │
    │                    │
    │ - Dashboard Home   │
    │ - Monitoring       │
    │ - Map View         │
    │ - Statistics       │
    │ - Region Mgmt      │
    └────────────────────┘
             ↑
        RESTful APIs
             ↑
    ┌────────────────────┐
    │  Enhanced Views    │
    │  views_enhanced.py │
    └────────────────────┘
             ↑
    ┌────────────────────────────┐
    │   Backend Pipeline         │
    │                            │
    │ continuous_monitoring.py   │
    │ - Queries Sentinel-1       │
    │ - Runs ML model            │
    │ - Saves results            │
    └────────────────────────────┘
             ↑
    ┌────────────────────┐
    │   Sentinel Hub     │
    │   Real SAR Data    │
    └────────────────────┘
```

---

## Summary

Your frontend is now **fully integrated** with the oil spill detection pipeline:

✅ Real-time system monitoring
✅ Interactive detection maps
✅ Region management
✅ Performance analytics
✅ Production-ready dashboard
✅ RESTful APIs for external integration

**Everything is connected and ready to use!** 🎉
