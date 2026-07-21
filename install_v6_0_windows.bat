@echo off
setlocal
echo Installing Crypto Intelligence Platform v6.0...
python -m pip install -r requirements.txt
python apply_v6_0_config.py
if errorlevel 1 exit /b 1
python apply_v6_0_module22_fix.py
if errorlevel 1 exit /b 1
python upgrade_to_v6_0.py
if errorlevel 1 exit /b 1
echo.
echo v6.0 installation complete.
echo Run: python run_module24.py
echo Inspect: python inspect_module24.py
pause
endlocal
