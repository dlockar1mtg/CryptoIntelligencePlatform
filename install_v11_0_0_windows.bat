@echo off
setlocal
echo Installing Crypto Intelligence Platform v11.0.0...
python -m pip install -r requirements.txt
python apply_v11_0_0_config.py
if errorlevel 1 exit /b 1
python upgrade_to_v11_0_0.py
if errorlevel 1 exit /b 1
python test_v11_0_0_schema_and_memory.py
if errorlevel 1 exit /b 1
echo.
echo v11.0.0 installation complete.
echo Refresh memory: python run_module40.py
echo Inspect repaired memory: python inspect_module40.py
echo Run meta-learning: python run_module41.py
echo Inspect meta-learning: python inspect_module41.py
echo Export meta-learning: python export_module41.py
pause
endlocal
