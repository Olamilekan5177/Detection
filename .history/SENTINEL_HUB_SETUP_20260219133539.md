# Sentinel Hub Integration & Setup Guide

## Overview

Your oil spill detection pipeline is now ready to query **real Sentinel-1 satellite data** from Sentinel Hub. This guide walks you through setup.

---

## 3-Minute Quick Start

### Step 1: Get API Credentials (5 minutes)

1. Go to https://www.sentinel-hub.com/
2. Sign up (free tier available) or log in
3. Navigate to **Dashboard → Settings → API Credentials**
4. Click **Create OAuth Client**
5. Name it "oil-spill-detection"
6. Copy your **CLIENT_ID** and **CLIENT_SECRET**

### Step 2: Configure Pipeline (2 minutes)

**Option A: Interactive Setup (Easiest)**

```powershell
python detection/setup_sentinel_hub.py --setup
```

Prompts you for credentials and saves them.

**Option B: Environment Variables (Most Secure)**

```powershell
# Windows PowerShell
$env:SENTINEL_HUB_CLIENT_ID = "your-client-id"
$env:SENTINEL_HUB_CLIENT_SECRET = "your-client-secret"

# Or Linux/Mac
export SENTINEL_HUB_CLIENT_ID="your-client-id"
export SENTINEL_HUB_CLIENT_SECRET="your-client-secret"
```

**Option C: Manual File**

Create `sentinel_hub_credentials.json` in project root:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret"
}
```

⚠️ **DO THIS**: Add to `.gitignore`

```
sentinel_hub_credentials.json
```

### Step 3: Verify Setup (1 minute)

```powershell
python detection/setup_sentinel_hub.py --test
```

Should show:

```
✓ Client ID: Configured
✓ Client Secret: Configured
✓ API Connection: Working
✓ Access token: Obtained
```

---

## What You Have Now

### New Files Created:

| File                                 | Purpose                                        |
| ------------------------------------ | ---------------------------------------------- |
| **detection/sentinel_hub_config.py** | Credential management and authentication       |
| **detection/setup_sentinel_hub.py**  | Interactive setup tool                         |
| **detection/sentinel1_pipeline.py**  | Updated with real Sentinel Hub API integration |

### Key Features:

✅ **Multiple credential sources**

- Environment variables (most secure)
- Local JSON file (easiest)
- Programmatic setup

✅ **Credential validation**

- Tests connection to Sentinel Hub
- Verifies credentials work
- Handles authentication automatically

✅ **Real API integration**

- Queries Sentinel Hub Catalog API
- Uses modern authentication (OAuth2)
- Supports spatial and temporal filtering

---

## Using the Pipeline with Sentinel Hub

### Basic Usage

```python
from detection.pipeline_orchestrator import create_pipeline
from datetime import datetime, timedelta

# Create pipeline
pipeline = create_pipeline(
    aoi_name="Niger Delta",
    bbox=(5.0, 4.0, 7.0, 6.0),
    model_path="ml_models/saved_models/oil_spill_detector.joblib"
)

# Run detection
results = pipeline.run()

# Check results
print(f"Detections found: {len(results['detections'])}")
print(f"Processing time: {results['processing_time_seconds']:.1f}s")
```

### Query Recent Sentinel-1 Data

```python
from detection.sentinel1_pipeline import Sentinel1QueryEngine
from detection.sentinel_hub_config import get_sentinel_hub_config
from datetime import datetime, timedelta

# Get credentials
config = get_sentinel_hub_config()

# Create query engine
query_engine = Sentinel1QueryEngine(config)

# Search for tiles
tiles = query_engine.search_tiles(
    bbox=(5.0, 4.0, 7.0, 6.0),  # Niger Delta
    start_date=datetime.now() - timedelta(days=7),
    end_date=datetime.now(),
    pass_direction="ASCENDING",
    limit=10
)

print(f"Found {len(tiles)} tiles")
for tile in tiles:
    print(f"  - {tile['name']} ({tile['acquisition_date']})")
```

---

## Commands Reference

### Setup

```powershell
# Interactive credential setup
python detection/setup_sentinel_hub.py --setup

# Use environment variables instead of being prompted
$env:SENTINEL_HUB_CLIENT_ID = "your-id"
$env:SENTINEL_HUB_CLIENT_SECRET = "your-secret"
python detection/setup_sentinel_hub.py --setup
```

### Testing

```powershell
# Test current configuration
python detection/setup_sentinel_hub.py --test

# Try example Sentinel-1 query
python detection/setup_sentinel_hub.py --query

# Interactive menu (all options)
python detection/setup_sentinel_hub.py
```

### In Python

```python
from detection.sentinel_hub_config import (
    get_sentinel_hub_config,
    setup_sentinel_hub_interactive
)

# Auto-load credentials
config = get_sentinel_hub_config()
print(config.is_configured())  # True if credentials found

# Interactive setup
setup_sentinel_hub_interactive()

# Validate credentials
if config.validate_credentials():
    print("✓ Working!")
else:
    print("✗ Check credentials")

# Get access token (auto-handled by pipeline)
token = config.get_access_token()
```

---

## Troubleshooting

### Problem: "Credentials not configured"

**Solution 1: Use setup tool**

```powershell
python detection/setup_sentinel_hub.py --setup
```

**Solution 2: Set environment variables**

```powershell
# Windows PowerShell
$env:SENTINEL_HUB_CLIENT_ID = "your-id"
$env:SENTINEL_HUB_CLIENT_SECRET = "your-secret"

# Verify
python detection/setup_sentinel_hub.py --test
```

### Problem: "Authentication failed"

Check that:

- Client ID is copied correctly (no extra spaces)
- Client Secret is copied correctly
- Your Sentinel Hub account is active
- You haven't exceeded API rate limits

**Try creating new OAuth credentials:**

1. Go to https://www.sentinel-hub.com/
2. Dashboard → Settings → API Credentials
3. Delete old ones, create new ones
4. Reconfigure with: `python detection/setup_sentinel_hub.py --setup`

### Problem: "No products found"

This is often OK! Reasons:

- Region has no recent Sentinel-1 coverage
- Date range is too short
- Try different bbox or dates

**Example that should work:**

```powershell
python detection/setup_sentinel_hub.py --query
```

This queries real data to verify everything works.

---

## Security Considerations

### DO ✅

- Add `sentinel_hub_credentials.json` to `.gitignore`
- Use environment variables for production
- Rotate credentials periodically
- Use OAuth Client with limited permissions

### DON'T ❌

- Commit credentials to git
- Share credentials in chat/email
- Use credentials in public code
- Log or print credentials

---

## Next Steps

1. **Get credentials** → https://www.sentinel-hub.com/
2. **Run setup** → `python detection/setup_sentinel_hub.py --setup`
3. **Verify** → `python detection/setup_sentinel_hub.py --test`
4. **Run pipeline** → `python -c "from detection.pipeline_orchestrator import create_pipeline; pipeline = create_pipeline('Test', (5.0,4.0,7.0,6.0), 'ml_models/saved_models/oil_spill_detector.joblib'); results = pipeline.run()"`
5. **Check results** → Look in `results/` folder

---

## API Details

### Sentinel Hub Endpoints Used

| Endpoint      | Purpose          | Status       |
| ------------- | ---------------- | ------------ |
| `oauth/token` | Get access token | ✓ Integrated |
| `Catalog API` | Search products  | ✓ Integrated |
| `Process API` | Order processing | Soon         |
| `Batch API`   | Bulk processing  | Soon         |

### Current Capabilities

✅ Query Sentinel-1 GRD products
✅ Filter by date range, location, pass direction
✅ Get product metadata
✅ Automatic authentication
✅ Error handling and logging

⏳ Coming Soon:

- Direct product download via API
- Batch processing orders
- Product statistics
- Archive search

---

## Questions?

Check:

1. **PIPELINE_IMPLEMENTATION.md** - Complete pipeline guide
2. **QUICK_REFERENCE.py** - API reference with examples
3. Run: `python detection/setup_sentinel_hub.py --help`
