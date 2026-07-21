@echo off
setlocal
echo Applying Crypto Intelligence Platform v11.0.3 Canonical Memory Rebuild...

python apply_v11_0_3_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v11_0_3.py
if errorlevel 1 (
    echo.
    echo Canonical memory rebuild failed.
    exit /b 1
)

python test_v11_0_3_canonical_rebuild.py
if errorlevel 1 (
    echo.
    echo Canonical rebuild preflight failed.
    exit /b 1
)

echo.
echo v11.0.3 installation complete.
echo Run memory engine: python run_module40.py
echo Inspect memory: python inspect_module40.py
echo Run memory engine again and confirm the count remains unchanged.
echo Refresh meta-learning: python run_module41.py
pause
endlocal
