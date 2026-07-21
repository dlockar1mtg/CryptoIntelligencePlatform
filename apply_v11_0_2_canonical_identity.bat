@echo off
setlocal
echo Applying Crypto Intelligence Platform v11.0.2 Canonical Forecast Identity...

python apply_v11_0_2_config.py
if errorlevel 1 exit /b 1

python upgrade_to_v11_0_2.py
if errorlevel 1 exit /b 1

python test_v11_0_2_canonical_identity.py
if errorlevel 1 exit /b 1

echo.
echo v11.0.2 installation complete.
echo Run memory engine: python run_module40.py
echo Inspect memory: python inspect_module40.py
echo Run memory engine again and confirm the count remains unchanged.
echo Refresh meta-learning: python run_module41.py
pause
endlocal
