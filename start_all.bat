@echo off
REM WebMagic - Start All Services (Windows)
REM This script starts all services in separate windows

echo Starting WebMagic services...

REM Check if Redis is running
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo Redis is not running! Please start Redis first.
    echo Download from: https://github.com/microsoftarchive/redis/releases
    echo Or use WSL: wsl redis-server
    pause
    exit /b 1
)

echo Redis is running ✓

REM Start Backend API
start "WebMagic API" cmd /k "cd backend && python start.py"
timeout /t 2 >nul

REM Start Celery Worker
start "WebMagic Celery Worker" cmd /k "cd backend && python start_worker.py"
timeout /t 2 >nul

REM Start Celery Beat
start "WebMagic Celery Beat" cmd /k "cd backend && python start_beat.py"
timeout /t 2 >nul

REM Start Frontend
start "WebMagic Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ======================================
echo WebMagic services started!
echo ======================================
echo.
echo API:      http://localhost:8000
echo Docs:     http://localhost:8000/docs
echo Frontend: http://localhost:3000
echo.
echo Press any key to stop all services...
pause >nul

REM Stop all services
taskkill /FI "WindowTitle eq WebMagic*" /F
echo Services stopped.
