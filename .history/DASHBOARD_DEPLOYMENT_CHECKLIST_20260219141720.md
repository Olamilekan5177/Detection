# Dashboard Deployment Checklist

Complete this checklist to deploy your frontend dashboard.

---

## Pre-Deployment (5 minutes)

- [ ] **Verify monitoring is running**

  ```powershell
  # Check if continuous_monitoring.py is still running
  Get-Process python | Where-Object {$_.CommandLine -like "*continuous_monitoring*"}
  ```

- [ ] **Verify results folder exists**

  ```powershell
  Test-Path results/
  ```

- [ ] **Verify model is available**

  ```powershell
  Test-Path ml_models/saved_models/oil_spill_detector.joblib
  # Should show True
  ```

- [ ] **Verify .env has credentials**
  ```powershell
  Get-Content .env
  # Should show SENTINEL_HUB_CLIENT_ID and CLIENT_SECRET
  ```

---

## Django Configuration (5 minutes)

- [ ] **Update main urls.py**

  Edit `config/urls.py` and verify it includes:

  ```python
  from django.urls import path, include

  urlpatterns = [
      path('admin/', admin.site.urls),
      path('dashboard/', include('dashboard.urls_enhanced')),  # ← VERIFY THIS EXISTS
      path('api/', include('detection.urls')),
      path('accounts/', include('users.urls')),
  ]
  ```

- [ ] **Run migrations (if needed)**

  ```powershell
  python manage.py migrate
  ```

- [ ] **Collect static files**
  ```powershell
  python manage.py collectstatic --noinput
  ```

---

## Frontend Verification (5 minutes)

- [ ] **Templates exist**

  ```powershell
  Test-Path dashboard/templates/dashboard/dashboard_home.html
  Test-Path dashboard/templates/dashboard/monitoring_status.html
  Test-Path dashboard/templates/dashboard/detections_map.html
  Test-Path dashboard/templates/dashboard/regions_management.html
  # All should show True
  ```

- [ ] **Views module imported**

  ```powershell
  python -c "from dashboard.views_enhanced import dashboard_home; print('OK')"
  ```

- [ ] **URLs module works**
  ```powershell
  python -c "from dashboard.urls_enhanced import urlpatterns; print(f'Routes: {len(urlpatterns)}')"
  ```

---

## Developer Server Test (2 minutes)

- [ ] **Start Django**

  ```powershell
  python manage.py runserver
  ```

- [ ] **Access dashboard**
      Visit: http://localhost:8000/dashboard/
  - Should show "Dashboard Home" page
  - Should display system status cards
  - Should show recent detections (if any)

- [ ] **Check monitoring logs**
      Visit: http://localhost:8000/dashboard/monitoring/status/
  - Should show pipeline state
  - Should show monitoring log

- [ ] **View detection map**
      Visit: http://localhost:8000/dashboard/detections/map/
  - Should load Leaflet map
  - Should show detected oil spills (if any)

- [ ] **Manage regions**
      Visit: http://localhost:8000/dashboard/regions/
  - Should show "Niger Delta" region
  - Should allow adding new regions

---

## API Testing (2 minutes)

- [ ] **Test API endpoints**

  In a new PowerShell window:

  ```powershell
  $headers = @{"Content-Type"="application/json"}

  # Test system status
  Invoke-WebRequest -Uri "http://localhost:8000/dashboard/api/system-status/" -Headers $headers

  # Test recent detections
  Invoke-WebRequest -Uri "http://localhost:8000/dashboard/api/recent-detections/" -Headers $headers

  # Test GeoJSON (for map)
  Invoke-WebRequest -Uri "http://localhost:8000/dashboard/api/detections-geojson/" -Headers $headers
  ```

---

## Monitoring System Test (5 minutes)

- [ ] **Trigger a monitoring run**

  ```powershell
  python -c "
  from detection.aoi_config import AreaOfInterest
  from detection.pipeline_orchestrator import create_pipeline

  region = AreaOfInterest.from_bbox((5, 4, 7, 6), 'Niger Delta')
  pipeline = create_pipeline(region)
  results = pipeline.run()
  print(f'Detection complete: {len(results)} results')
  "
  ```

- [ ] **Check results were saved**

  ```powershell
  Get-ChildItem results/ -Filter "*.json" | Select-Object -First 1
  # Should show at least one JSON file
  ```

- [ ] **Verify results appear on dashboard**
      Refresh http://localhost:8000/dashboard/
  - Should see updated detection count
  - Map should show new markers

---

## Production Deployment (varies)

When ready for production:

- [ ] **Use production WSGI server**

  ```powershell
  pip install gunicorn
  gunicorn config.wsgi:application
  ```

- [ ] **Setup SSL/HTTPS**
  - Install certificate
  - Update ALLOWED_HOSTS in settings.py
  - Set SECURE_SSL_REDIRECT = True

- [ ] **Enable database backend**
  - Optional: Store detections in PostgreSQL instead of JSON files
  - Run migrations: `python manage.py migrate`

- [ ] **Setup background task runner**

  ```powershell
  # Instead of continuous_monitoring.py, use Celery:
  pip install celery redis
  celery -A config worker -l info
  ```

- [ ] **Configure monitoring to run automatically**
  - Windows Task Scheduler: Schedule continuous_monitoring.py
  - Or: Use Celery Beat for scheduled tasks

---

## Quick Troubleshooting

| Issue                    | Solution                                                                   |
| ------------------------ | -------------------------------------------------------------------------- |
| 404 on `/dashboard/`     | Verify `urls_enhanced.py` is imported in `config/urls.py`                  |
| No detections showing    | Run `continuous_monitoring.py` to generate results                         |
| Map doesn't load         | Check browser console (F12) for JavaScript errors                          |
| Login required           | Create admin user: `python manage.py createsuperuser`                      |
| Static files not loading | Run: `python manage.py collectstatic`                                      |
| Sentinel Hub offline     | Verify `.env` credentials: `python detection/setup_sentinel_hub.py --test` |

---

## What Each Page Does

| Page       | URL                             | Purpose                    |
| ---------- | ------------------------------- | -------------------------- |
| Dashboard  | `/dashboard/`                   | System overview, key stats |
| Monitoring | `/dashboard/monitoring/status/` | Real-time pipeline logs    |
| Map        | `/dashboard/detections/map/`    | Geographic visualization   |
| Regions    | `/dashboard/regions/`           | Configure monitoring areas |
| Statistics | `/dashboard/statistics/`        | Analytics & metrics        |

---

## Estimated Time

- Setup: **5 minutes**
- Testing: **10 minutes**
- Total: **15 minutes** to fully deployed dashboard

✅ **You're ready to go!**
