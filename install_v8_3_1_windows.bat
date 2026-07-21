@echo off
setlocal
echo Installing Crypto Intelligence Platform v8.3.1...
python -m pip install -r requirements.txt

python apply_v8_3_1_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v8_3_1.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

python test_v8_3_1_module33_schema.py
if errorlevel 1 (
    echo.
    echo Module 33 schema preflight failed.
    exit /b 1
)

echo.
echo v8.3.1 installation complete.
echo Run: python run_module33.py
echo Inspect: python inspect_module33.py
echo Export: python export_module33.py
pause
endlocal
