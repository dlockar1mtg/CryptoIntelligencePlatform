@echo off
setlocal
echo Installing Crypto Intelligence Platform v10.2.0...
python -m pip install -r requirements.txt

python apply_v10_2_0_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v10_2_0.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

python test_v10_1_1_module39_schema.py
if errorlevel 1 (
    echo.
    echo Module 39 schema preflight failed.
    exit /b 1
)

python test_v10_2_0_module40_schema.py
if errorlevel 1 (
    echo.
    echo Module 40 schema preflight failed.
    exit /b 1
)

echo.
echo v10.2.0 installation complete.
echo Re-run evidence-aware validation: python run_module39.py
echo Inspect validation: python inspect_module39.py
echo Run forecast memory: python run_module40.py
echo Inspect memory: python inspect_module40.py
echo Export memory: python export_module40.py
pause
endlocal
