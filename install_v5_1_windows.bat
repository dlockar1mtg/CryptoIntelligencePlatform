@echo off
setlocal
echo Installing Crypto Intelligence Platform v5.1...
python -m pip install -r requirements.txt

python apply_v5_1_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v5_1.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

echo.
echo v5.1 installation complete.
echo Run: python run_module22.py
echo Inspect: python inspect_module22.py
pause
endlocal
