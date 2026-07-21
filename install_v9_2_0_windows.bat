@echo off
setlocal
echo Installing Crypto Intelligence Platform v9.2.0...
python -m pip install -r requirements.txt

python apply_v9_2_0_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v9_2_0.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

python test_v9_2_0_module37_schema.py
if errorlevel 1 (
    echo.
    echo Module 37 schema preflight failed.
    exit /b 1
)

echo.
echo v9.2.0 installation complete.
echo Run optimizer: python run_module37.py
echo Inspect optimizer: python inspect_module37.py
echo Export optimizer: python export_module37.py
echo Re-run fixed Module 35 export: python export_module35.py
echo Re-run fixed Module 36 export: python export_module36.py
pause
endlocal
