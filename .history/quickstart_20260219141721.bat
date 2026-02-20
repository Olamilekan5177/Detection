@echo off
REM Oil Spill Detection System - Quick Start Script
REM This script automates the deployment process

SETLOCAL ENABLEDELAYEDEXPANSION

ECHO.
ECHO ====================================================================
ECHO   OIL SPILL DETECTION SYSTEM - QUICK START
ECHO ====================================================================
ECHO.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    ECHO ERROR: Python not found. Please install Python 3.11+
    PAUSE
    EXIT /B 1
)

ECHO [1/6] Checking environment...
if not exist ".venv" (
    ECHO Creating virtual environment...
    python -m venv .venv
) else (
    ECHO Virtual environment already exists.
)

ECHO.
ECHO [2/6] Activating virtual environment...
CALL .venv\Scripts\activate.bat

ECHO.
ECHO [3/6] Installing/updating dependencies...
pip install -q django scikit-learn rasterio python-dotenv leaflet >/dev/null 2>&1
ECHO Dependencies ready.

ECHO.
ECHO [4/6] Verifying configuration...
if not exist ".env" (
    ECHO WARNING: .env file not found!
    ECHO Run this to setup Sentinel Hub credentials:
    ECHO   python detection/setup_sentinel_hub.py --setup
)

if not exist "ml_models\saved_models\oil_spill_detector.joblib" (
    ECHO WARNING: Model not found. Training will start...
    ECHO   python train_sklearn_model.py
)

ECHO.
ECHO [5/6] Running Django checks...
python manage.py check >nul 2>&1
if errorlevel 1 (
    ECHO ERROR: Django configuration issue
    python manage.py check
    PAUSE
    EXIT /B 1
) else (
    ECHO Django configuration OK.
)

ECHO.
ECHO [6/6] Ready to start!
ECHO.
ECHO ====================================================================
ECHO   NEXT STEPS - CHOOSE ONE:
ECHO ====================================================================
ECHO.
ECHO Option 1: Start EVERYTHING at once
ECHO   run_dashboard.bat
ECHO.
ECHO Option 2: Start monitoring ONLY (background)
ECHO   python continuous_monitoring.py --interval 24
ECHO.
ECHO Option 3: Start dashboard ONLY
ECHO   python manage.py runserver
ECHO.
ECHO Option 4: Test Sentinel Hub credentials
ECHO   python detection/setup_sentinel_hub.py --test
ECHO.
ECHO Option 5: View this guide
ECHO   START FRONTEND_INTEGRATION.md
ECHO.
ECHO ====================================================================
ECHO.

PAUSE
