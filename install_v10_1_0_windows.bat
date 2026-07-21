@echo off
setlocal
echo Installing Crypto Intelligence Platform v10.1.0...
python -m pip install -r requirements.txt
python apply_v10_1_0_config.py
if errorlevel 1 exit /b 1
python upgrade_to_v10_1_0.py
if errorlevel 1 exit /b 1
python test_v10_1_0_module39_schema.py
if errorlevel 1 exit /b 1
echo.
echo v10.1.0 installation complete.
echo Run: python run_module39.py
echo Inspect: python inspect_module39.py
echo Export: python export_module39.py
pause
endlocal
