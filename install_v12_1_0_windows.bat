@echo off
setlocal
echo Installing Crypto Intelligence Platform v12.1.0...
python -m pip install -r requirements.txt

python apply_v12_1_0_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v12_1_0.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

python test_v12_1_0_module43_schema.py
if errorlevel 1 (
    echo.
    echo Module 43 schema preflight failed.
    exit /b 1
)

echo.
echo v12.1.0 installation complete.
echo Run institutional intelligence: python run_module43.py
echo Inspect results: python inspect_module43.py
echo Export results: python export_module43.py
pause
endlocal
