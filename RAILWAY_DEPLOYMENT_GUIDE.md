# Railway Deployment Guide - Oil Spill Detection System

## Why Railway?

✅ **Better Free Tier**: $5/month free credits (covers small deployment)  
✅ **No Sleep**: Apps don't sleep like Render free tier  
✅ **Simple Setup**: Just connect GitHub and deploy  
✅ **Generous Limits**: Plenty for testing and small production  
✅ **PostgreSQL Included**: Free databases available

---

## Step 1: Create Railway Account (2 minutes)

1. Go to: https://railway.app
2. Click **"Start for Free"** or **"Sign Up"**
3. Choose **"Sign up with GitHub"**
4. Authorize Railway to access your GitHub account
5. Allow Railway to access **Olamilekan5177/Detection** repository

---

## Step 2: Create Your First Project (1 minute)

1. Click **"New Project"**
2. Click **"Deploy from GitHub repo"**
3. Select **Olamilekan5177/Detection**
4. Railway will auto-detect it's a Django app

---

## Step 3: Add PostgreSQL Database (2 minutes)

1. In your project, click **"Add Service"** (+ button)
2. Choose **"Add from Marketplace"**
3. Click **"PostgreSQL"**
4. Railway will create a PostgreSQL database automatically
5. **Copy these values** from the database service:
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`
   - `POSTGRES_DB`
   - Connection URL will auto-populate as `DATABASE_URL`

---

## Step 4: Configure Environment Variables (5 minutes)

In your **Django Web Service** (not the database), add these variables:

### Django Settings:

```
SECRET_KEY = your-secret-key-here
DEBUG = False
ALLOWED_HOSTS = *.railway.app
DJANGO_SETTINGS_MODULE = config.settings
PYTHONUNBUFFERED = 1
```

### Sentinel Hub (YOUR CREDENTIALS):

```
SENTINEL_HUB_CLIENT_ID = c45f1d8d-972c-45cb-9e59-aea9d3d6f15d
SENTINEL_HUB_CLIENT_SECRET = 5b2527a7-565b-4442-a805-66fb6526a3cc
```

### Database (Auto-linked):

```
DATABASE_URL = (Railway auto-generates this from PostgreSQL service)
```

**How to add variables in Railway:**

1. Go to your **Django service** → **Variables** tab
2. Click **"Add Variable"**
3. Paste each variable above

---

## Step 5: Configure Build & Start Commands (3 minutes)

In the **Django Web Service**, go to **"Settings"** tab:

### Build Command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

### Start Command:

```bash
gunicorn config.wsgi:application
```

Railway automatically assigns the `$PORT` variable, no need to specify it.

---

## Step 6: Deploy! (5-10 minutes)

1. Click the **"Deploy"** button
2. Watch the deployment logs in real-time
3. Once complete, you'll get a URL like: `https://oil-spill-detection-production.up.railway.app/`

**Your Live URLs:**

- **Dashboard**: `https://your-app.up.railway.app/dashboard/`
- **Admin**: `https://your-app.up.railway.app/admin/`
- **API**: `https://your-app.up.railway.app/api/`

---

## Step 7: Create Admin User (1 minute)

Once deployed:

1. Go to your project dashboard
2. Click your **Django service**
3. Click **"Shell"** tab
4. Run:

```bash
python manage.py createsuperuser
```

5. Enter username, email, password when prompted

---

## Step 8: Upload ML Model Files (Important!)

Your model files (576 MB) need to be hosted separately.

### Option A: Use AWS S3 (Easiest & Free)

1. Create AWS account: https://aws.amazon.com/free/
2. Create S3 bucket: `oil-spill-models`
3. Upload your `.joblib` and `.pkl` files
4. Make bucket public (or use signed URLs)
5. Get the model URL

### Upload Code to Automatically Download Models

Create `ml_models/download_models.py`:

```python
import os
import urllib.request

def download_model_if_needed():
    """Download model from S3 if not present locally"""
    model_path = "ml_models/saved_models/oil_spill_detector.joblib"

    if os.path.exists(model_path):
        print("✓ Model already exists")
        return

    os.makedirs(os.path.dirname(model_path), exist_ok=True)

    # Your S3 URL or alternative storage
    model_url = "https://your-aws-bucket.s3.amazonaws.com/oil_spill_detector.joblib"

    print(f"⬇️ Downloading model from {model_url}...")
    try:
        urllib.request.urlretrieve(model_url, model_path)
        print("✓ Model downloaded successfully!")
    except Exception as e:
        print(f"❌ Failed to download model: {e}")
        raise
```

Then call it in `config/settings.py` or `manage.py`:

```python
# At the top of config/settings.py
from ml_models.download_models import download_model_if_needed

if not os.environ.get('DEBUG', False):  # Only download in production
    download_model_if_needed()
```

### Option B: Railway Volumes (Persistent Storage)

1. In your Django service, go to **"Settings"** → **"Volumes"**
2. Click **"Add Volume"**
3. Mount path: `/app/ml_models/saved_models`
4. Size: 1GB (enough for model files)
5. Upload models via Shell or SFTP

---

## Step 9: Set Up Cron Job for Satellite Monitoring (5 minutes)

Since Railway free tier doesn't include cron services, use one of these alternatives:

### Option A: External Cron Service (FREE)

Use **cron-job.org** (free external service):

1. Go to: https://cron-job.org
2. Create account
3. Add new cron job:
   - **URL**: `https://your-app.up.railway.app/dashboard/api/trigger-monitoring/`
   - **Schedule**: Every 6 hours (0 _/6 _ \* \*)
4. This will trigger your monitoring via API

### Option B: Scheduled GitHub Action (FREE)

Create `.github/workflows/run-monitoring.yml`:

```yaml
name: Run Satellite Monitoring

on:
  schedule:
    - cron: "0 */6 * * *" # Every 6 hours

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Trigger monitoring
        run: |
          curl -X POST https://your-app.up.railway.app/dashboard/api/trigger-monitoring/
```

### Option C: Railway Cron Workaround

Add to your Django app a management command that runs periodically:

```bash
python manage.py run_satellite_monitoring
```

Then use external cron service (Option A) to call it via API.

---

## Step 10: Custom Domain (Optional)

To use your own domain:

1. Go to your **Django service** → **"Settings"**
2. Scroll to **"Domains"**
3. Click **"Add Domain"**
4. Enter your domain (e.g., `oilspill.com`)
5. Add the **CNAME record** to your DNS provider:
   - **Host**: `oilspill.com`
   - **CNAME**: `cname-value-from-railway.railway.app`
6. Wait for DNS propagation (5-60 minutes)

---

## Step 11: Monitor Your App

Railway gives you built-in monitoring:

1. Click your **Django service**
2. View **"Metrics"** tab:
   - CPU usage
   - Memory usage
   - Network activity
   - Logs

3. View **"Logs"** tab for real-time debugging

---

## Troubleshooting

### App Crashes After Deploy

**Check Logs:**

1. Go to service → **"Logs"** tab
2. Look for error messages
3. Common issues:
   - `ModuleNotFoundError`: Missing dependency in `requirements.txt`
   - `OperationalError`: Database migrations not run
   - Model file not found: Upload via S3 or volumes

### Database Connection Error

1. Verify **DATABASE_URL** is auto-set by PostgreSQL service
2. Check PostgreSQL service is **running** (green status)
3. Restart both services in order: Database first, then Django

### High Memory Usage

1. Reduce gunicorn workers: `gunicorn config.wsgi:application --workers 2`
2. Enable caching in Django settings
3. Upgrade to paid Railway plan for more memory

### Monitoring Not Running

1. Check API endpoint works: Visit `/dashboard/api/trigger-monitoring/`
2. Check monitoring logs in Django Logs tab
3. Verify Sentinel Hub credentials are correct

---

## Cost Breakdown (Monthly)

| Service             | Railway Cost   | Note                        |
| ------------------- | -------------- | --------------------------- |
| Django Web App      | ~$2-3          | Within $5 free credits      |
| PostgreSQL Database | ~$1-2          | Within $5 free credits      |
| Storage (models)    | Free           | With S3 or volumes          |
| **TOTAL**           | **$0-5/month** | Free tier usually covers it |

✅ **You get $5/month free credits automatically!**

---

## Quick Commands Reference

```bash
# View logs
railway logs

# Open shell on Railway
railway shell

# Run migrations
railway run python manage.py migrate

# Create superuser
railway run python manage.py createsuperuser

# Collect static files
railway run python manage.py collectstatic --noinput
```

---

## Next Steps

1. ✅ Deploy on Railway (10 minutes)
2. ✅ Set up Sentinel Hub credentials
3. ✅ Upload model files to S3 or volumes
4. ✅ Configure satellite monitoring via API/cron
5. ✅ Test dashboard at your Railway URL
6. ✅ (Optional) Add custom domain
7. ✅ Monitor and scale as needed

---

## Getting Help

- **Railway Docs**: https://docs.railway.app
- **Django on Railway**: https://docs.railway.app/guides/django
- **Our GitHub**: https://github.com/Olamilekan5177/Detection

---

✅ **Ready to deploy on Railway? You've got this! 🚀**
