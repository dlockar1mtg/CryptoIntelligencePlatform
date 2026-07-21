@echo off
setlocal
echo Installing Crypto Intelligence Platform v9.1.0...
python -m pip install -r requirements.txt
python apply_v9_1_0_config.py
if errorlevel 1 exit /b 1
python upgrade_to_v9_1_0.py
if errorlevel 1 exit /b 1
python test_v9_1_0_schema.py
if errorlevel 1 exit /b 1
echo.
echo v9.1.0 installation complete.
echo Run: python run_module35.py
echo Then: python inspect_module35.py
echo Then: python run_module36.py
echo Then: python inspect_module36.py
pause
endlocal
