@echo off
setlocal
echo Installing Crypto Intelligence Platform v12.0.0...
python -m pip install -r requirements.txt

python apply_v12_0_0_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v12_0_0.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

python test_v12_0_0_module42_schema.py
if errorlevel 1 (
    echo.
    echo Module 42 schema preflight failed.
    exit /b 1
)

echo.
echo v12.0.0 installation complete.
echo Run decision engine: python run_module42.py
echo Inspect recommendations: python inspect_module42.py
echo Export outputs: python export_module42.py
pause
endlocal
