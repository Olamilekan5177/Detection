# Render Deployment Guide - Oil Spill Detection System

## Prerequisites
✅ Code pushed to GitHub: https://github.com/Olamilekan5177/Detection  
✅ Sentinel Hub credentials ready  
✅ Model files available locally (will upload separately)

---

## Step 1: Create Render Account (2 minutes)

1. Go to: https://render.com
2. Click **"Get Started"** or **"Sign Up"**
3. Choose **"Sign up with GitHub"**
4. Authorize Render to access your GitHub account
5. Select the repositories you want to give Render access to (choose **Olamilekan5177/Detection**)

---

## Step 2: Create PostgreSQL Database (3 minutes)

1. From Render Dashboard, click **"New +"** → **"PostgreSQL"**
2. Configure:
   - **Name**: `oil-spill-detection-db`
   - **Database**: `oilspill` (auto-generated)
   - **User**: `oilspill` (auto-generated)
   - **Region**: Choose closest to your users (e.g., `Oregon (US West)`)
   - **PostgreSQL Version**: `16` (latest)
   - **Plan**: **Free** (for testing) or **Starter** ($7/month for production)
3. Click **"Create Database"**
4. Wait 2-3 minutes for provisioning
5. **SAVE THESE VALUES** (you'll need them):
   - **Internal Database URL** (starts with `postgresql://`)
   - **External Database URL** (also starts with `postgresql://`)

---

## Step 3: Create Web Service (5 minutes)

1. Click **"New +"** → **"Web Service"**
2. Connect your repository:
   - Choose **"Build and deploy from a Git repository"**
   - Click **"Connect"** next to **Olamilekan5177/Detection**
3. Configure the service:

   **Basic Settings:**
   - **Name**: `oil-spill-detection` (this will be your URL subdomain)
   - **Region**: Same as your database (e.g., `Oregon (US West)`)
   - **Branch**: `main`
   - **Root Directory**: Leave blank
   - **Runtime**: `Python 3`

   **Build Settings:**
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt
     ```
   
   **Start Command**:
     ```bash
     gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
     ```

   **Plan**: 
   - **Free** (for testing - sleeps after 15 min of inactivity)
   - **Starter** ($7/month - recommended for production, always on)

4. Click **"Advanced"** to add environment variables (see Step 4 below)

---

## Step 4: Configure Environment Variables (5 minutes)

In the **"Advanced"** section, add these environment variables:

### Django Settings:
```
SECRET_KEY = django-insecure-your-secret-key-here-change-this-in-production
DEBUG = False
ALLOWED_HOSTS = .onrender.com
```

### Database (copy from Step 2):
```
DATABASE_URL = postgresql://user:password@host/database
```
(Use the **Internal Database URL** from your PostgreSQL instance)

### Sentinel Hub Credentials:
```
SENTINEL_HUB_CLIENT_ID = c45f1d8d-972c-45cb-9e59-aea9d3d6f15d
SENTINEL_HUB_CLIENT_SECRET = 5b2527a7-565b-4442-a805-66fb6526a3cc
```

### Static Files:
```
STATIC_URL = /static/
STATIC_ROOT = staticfiles
```

### Optional (for production):
```
DJANGO_SETTINGS_MODULE = config.settings
PYTHONUNBUFFERED = 1
```

5. Click **"Create Web Service"**

---

## Step 5: Wait for Initial Deployment (5-10 minutes)

Render will now:
1. Clone your GitHub repository
2. Install dependencies from `requirements.txt`
3. Build your application
4. Deploy it

**Watch the build logs** on the Render dashboard - you'll see each step in real-time.

⚠️ **Expected Issue**: The build will succeed, but the app might crash because:
- Database migrations haven't run yet
- ML model files are missing

We'll fix these next!

---

## Step 6: Run Database Migrations (2 minutes)

Once the initial build completes:

1. In your web service dashboard, click **"Shell"** (top right)
2. This opens a terminal directly on your Render server
3. Run these commands:

```bash
python manage.py migrate
python manage.py createsuperuser
```

4. Create your admin account when prompted:
   - Username: (your choice)
   - Email: (your email)
   - Password: (secure password)

---

## Step 7: Upload ML Model Files (IMPORTANT - 10 minutes)

Your model files (`oil_spill_detector.joblib` and `.pkl`) weren't pushed to GitHub because they're too large.

### Option A: Direct Upload via Shell (Recommended for small files)

1. Open **Shell** on your Render service
2. Create the directory:
   ```bash
   mkdir -p ml_models/saved_models
   ```

3. **On your local machine**, encode the model files:
   ```powershell
   # In PowerShell on your local machine
   cd "C:\Users\user\Downloads\Oil Spill Detection"
   
   # Create base64 encoded version (smaller file)
   [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("ml_models/saved_models/oil_spill_detector.joblib")) | Out-File -FilePath "model_encoded.txt"
   ```

4. Upload using Render's file transfer or use a temporary storage service

### Option B: Use Cloud Storage (Recommended for large files - 576 MB)

Since your model is 576 MB, use external storage:

**Using AWS S3 (Free tier available):**

1. Create AWS account: https://aws.amazon.com/free/
2. Go to S3, create bucket: `oil-spill-models`
3. Upload your model files
4. Make them publicly accessible (or use signed URLs)
5. Update your code to download models on startup:

Add to `config/settings.py` or create `ml_models/load_models.py`:

```python
import os
import urllib.request

MODEL_URL = "https://oil-spill-models.s3.amazonaws.com/oil_spill_detector.joblib"
MODEL_PATH = "ml_models/saved_models/oil_spill_detector.joblib"

if not os.path.exists(MODEL_PATH):
    print("Downloading model from S3...")
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Model downloaded successfully!")
```

### Option C: Git LFS (Alternative)

1. Install Git LFS locally: `git lfs install`
2. Track large files: `git lfs track "*.joblib" "*.pkl"`
3. Commit and push: 
   ```bash
   git add .gitattributes
   git add ml_models/saved_models/*.joblib
   git commit -m "Add model files with LFS"
   git push origin main
   ```

---

## Step 8: Create Background Worker for Monitoring (5 minutes)

Your `continuous_monitoring.py` script needs to run continuously in the background.

1. Click **"New +"** → **"Background Worker"**
2. Configure:
   - **Name**: `satellite-monitoring-worker`
   - **Region**: Same as web service
   - **Repository**: **Olamilekan5177/Detection**
   - **Branch**: `main`
   
   **Build Command**:
   ```bash
   pip install -r requirements.txt
   ```
   
   **Start Command**:
   ```bash
   python continuous_monitoring.py
   ```

3. **Environment Variables**: Copy ALL the same variables from your web service
   - Click **"Environment"** tab
   - Add same vars: `DATABASE_URL`, `SENTINEL_HUB_CLIENT_ID`, `SENTINEL_HUB_CLIENT_SECRET`, etc.

4. Click **"Create Background Worker"**

---

## Step 9: Verify Deployment (5 minutes)

### Test Your Web Service:

1. Your app URL will be: `https://oil-spill-detection.onrender.com`
2. Visit: `https://oil-spill-detection.onrender.com/dashboard/`
3. You should see your dashboard!

### Check Logs:

1. **Web Service**: Click "Logs" to see Django server logs
2. **Background Worker**: Check logs to see monitoring activity

### Test Endpoints:

```powershell
# On your local machine
$baseUrl = "https://oil-spill-detection.onrender.com"

# Test homepage
Invoke-WebRequest -Uri "$baseUrl/dashboard/"

# Test API
Invoke-WebRequest -Uri "$baseUrl/dashboard/api/system-status/"
```

---

## Step 10: Configure Custom Domain (Optional)

If you have a custom domain (e.g., `oilspill.yoursite.com`):

1. Go to your service → **"Settings"** → **"Custom Domain"**
2. Click **"Add Custom Domain"**
3. Enter your domain
4. Add the CNAME record to your DNS provider as instructed
5. Wait for DNS propagation (5-60 minutes)

---

## Troubleshooting

### Build Fails:
- Check `requirements.txt` for incompatible packages
- View build logs for specific error messages

### App Crashes After Deploy:
- Check **Logs** for Python errors
- Verify all environment variables are set correctly
- Ensure migrations ran: `python manage.py showmigrations`

### Model Not Found Error:
- Verify model files were uploaded to `ml_models/saved_models/`
- Check file permissions in Shell: `ls -la ml_models/saved_models/`

### Database Connection Error:
- Verify `DATABASE_URL` environment variable is correct
- Check PostgreSQL instance is running
- Ensure both services are in the same region

### Background Worker Not Running:
- Check worker logs for errors
- Verify it has same environment variables as web service
- Check if Sentinel Hub credentials are valid

---

## Cost Estimate (Monthly)

**Free Tier (Testing):**
- Web Service: Free (sleeps after 15 min inactivity, 750 hours/month free)
- PostgreSQL: Free (expires after 90 days)
- Background Worker: Free (750 hours/month free)
- **Total: $0/month** (first 90 days)

**Production (Recommended):**
- Web Service Starter: $7/month (always on)
- PostgreSQL Starter: $7/month (persistent)
- Background Worker: $7/month (always on)
- **Total: $21/month**

---

## Security Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DEBUG = False` in production
- [ ] Update `ALLOWED_HOSTS` with your actual domain
- [ ] Use HTTPS only (Render provides this automatically)
- [ ] Store sensitive credentials as environment variables (not in code)
- [ ] Enable database backups (Render PostgreSQL has automatic backups)
- [ ] Set up monitoring/alerting for service downtime

---

## Next Steps After Deployment

1. **Set up automated backups** for your database
2. **Configure logging** to track errors and usage
3. **Set up monitoring alerts** (Render provides basic metrics)
4. **Optimize for performance**:
   - Enable Django caching
   - Use CDN for static files
   - Add database indexes for frequently queried fields
5. **Documentation**: Update README with your live URL

---

## Your Deployment URLs

After completing these steps, you'll have:

- **Dashboard**: `https://oil-spill-detection.onrender.com/dashboard/`
- **Admin Panel**: `https://oil-spill-detection.onrender.com/admin/`
- **API**: `https://oil-spill-detection.onrender.com/api/`
- **Monitoring Map**: `https://oil-spill-detection.onrender.com/dashboard/map/`

---

✅ **Ready to deploy? Start with Step 1!**

Got stuck? Check the Render documentation: https://render.com/docs
