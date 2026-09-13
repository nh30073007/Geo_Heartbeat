@echo off
setlocal
cd /d "%~dp0"
echo Installing backend dependencies...
cd /d "%~dp0backend"
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo Installing frontend dependencies...
cd /d "%~dp0frontend"
npm install
if errorlevel 1 goto :fail

echo.
echo Setup complete. Run START_WINDOWS.bat
pause
exit /b 0
:fail
echo.
echo Setup failed. Check the error above.
pause
exit /b 1
