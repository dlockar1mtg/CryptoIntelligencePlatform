@echo off
setlocal
echo Installing Crypto Intelligence Platform v13.0.0...
python -m pip install -r requirements.txt
python apply_v13_0_0_config.py
if errorlevel 1 exit /b 1
python upgrade_to_v13_0_0.py
if errorlevel 1 exit /b 1
python test_v13_0_0_module44_schema.py
if errorlevel 1 exit /b 1
echo.
echo v13.0.0 installation complete.
echo Run economic value engine: python run_module44.py
echo Inspect results: python inspect_module44.py
echo Export results: python export_module44.py
pause
endlocal
