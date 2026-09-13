@echo off
setlocal
cd /d "%~dp0"

echo ===============================================
echo       Strategic AI Nexus / GeoPolis
 echo       Windows development launcher
 echo ===============================================

echo.
echo [1/2] Starting FastAPI backend on port 8000...
start "Strategic AI Nexus - Backend" /D "%~dp0backend" cmd /k "python run.py"

timeout /t 2 /nobreak >nul

echo [2/2] Preparing Next.js frontend on port 3000...
if not exist "%~dp0frontend\node_modules\.bin\next.cmd" (
  echo Frontend dependencies not found. Installing...
  start /wait "Strategic AI Nexus - Frontend Install" /D "%~dp0frontend" cmd /c "npm install"
  if errorlevel 1 echo WARNING: npm install failed. Run npm install manually.
)
start "Strategic AI Nexus - Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo.
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo Docs:     http://localhost:8000/docs
echo.
echo If frontend dependencies are missing, run: npm install
pause
