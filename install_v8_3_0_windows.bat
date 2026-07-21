@echo off
setlocal
echo Installing Crypto Intelligence Platform v8.3.0...
python -m pip install -r requirements.txt

python apply_v8_3_0_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v8_3_0.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

python test_v8_3_0_module32_schema.py
if errorlevel 1 (
    echo.
    echo Module 32 schema preflight failed.
    exit /b 1
)

echo.
echo v8.3.0 installation complete.
echo Run: python run_module32.py
echo Inspect: python inspect_module32.py
echo Export: python export_module32.py
pause
endlocal
