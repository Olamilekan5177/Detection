@echo off
REM Oil Spill Detection System - Complete Deployment Script
REM Starts: Monitoring + Django Dashboard + Opens browser

SETLOCAL ENABLEDELAYEDEXPANSION

ECHO.
ECHO ====================================================================
ECHO   OIL SPILL DETECTION SYSTEM - DEPLOYING...
ECHO ====================================================================
ECHO.

REM Activate virtual environment
CALL .venv\Scripts\activate.bat

ECHO [1/3] Starting monitoring system (background)...
REM Start monitoring in a separate window
START "Oil Spill Monitoring" /MIN ^
    .venv\Scripts\python.exe continuous_monitoring.py --interval 24

ECHO         ✓ Monitoring started (queries real Sentinel-1 data every 24h)
TIMEOUT /T 2 /NOBREAK

ECHO.
ECHO [2/3] Starting Django development server...
REM Start Django in a separate window
START "Oil Spill Dashboard" ^
    .venv\Scripts\python.exe manage.py runserver

ECHO         ✓ Dashboard starting on http://localhost:8000/dashboard/
TIMEOUT /T 3 /NOBREAK

ECHO.
ECHO [3/3] Opening dashboard in browser...
TIMEOUT /T 2 /NOBREAK
START http://localhost:8000/dashboard/

ECHO.
ECHO ====================================================================
ECHO   SYSTEM STARTED!
ECHO ====================================================================
ECHO.
ECHO URLs:
ECHO   Dashboard:    http://localhost:8000/dashboard/
ECHO   Monitoring:   http://localhost:8000/dashboard/monitoring/status/
ECHO   Map:          http://localhost:8000/dashboard/detections/map/
ECHO   Regions:      http://localhost:8000/dashboard/regions/
ECHO   Statistics:   http://localhost:8000/dashboard/statistics/
ECHO   Admin:        http://localhost:8000/admin/
ECHO.
ECHO Monitoring Details:
ECHO   Default Region: Niger Delta (5°E, 4°N to 7°E, 6°N)
ECHO   Interval: Every 24 hours
ECHO   Model: 576 MB neural network (90%% accuracy)
ECHO   Real Data: Sentinel-1 SAR satellite imagery
ECHO.
ECHO To Stop:
ECHO   1. Close the monitoring window (will shutdown gracefully)
ECHO   2. Close the dashboard window (Ctrl+C)
ECHO   Or: Close all Python processes in Task Manager
ECHO.
ECHO ====================================================================
ECHO.
ECHO System is running. Check browser...
PAUSE
