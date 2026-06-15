@echo off
title LatticeFlow EDM
cd /d "%~dp0"

echo.
echo ================================================
echo   LatticeFlow EDM  (UI v5)
echo ================================================
echo   URL:  http://localhost:5050
echo   Look for "UI v5" badge top-right corner
echo   Keep this window OPEN while using the site
echo ================================================
echo.

echo Stopping old servers (ports 5000, 5050, 8501)...
for %%P in (5000 5050 8501) do (
  for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :%%P ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
  )
)

echo Installing dependencies...
python -m pip install -r requirements.txt -q

echo Loading ML model...
python -c "from circularity_predictor import train_and_save; train_and_save(); print('Ready.')"

echo.
echo Starting server at http://localhost:5050
echo.
start http://localhost:5050
python web_server.py
pause
