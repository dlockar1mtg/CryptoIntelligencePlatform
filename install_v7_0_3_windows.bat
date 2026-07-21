@echo off
setlocal
echo Installing Crypto Intelligence Platform v7.0.3...
python apply_v7_0_3_config.py
if errorlevel 1 exit /b 1
python upgrade_to_v7_0_3.py
if errorlevel 1 exit /b 1
echo.
echo v7.0.3 installation complete.
echo Run: python run_module25_validation.py
echo Inspect: python inspect_module25_validation.py
pause
endlocal
