@echo off
setlocal
echo Installing Crypto Intelligence Platform v5.0...
python -m pip install -r requirements.txt

python apply_v5_0_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v5_0.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

echo.
echo v5.0 installation complete.
echo Run: python run_module21.py
echo Inspect: python inspect_module21.py
pause
endlocal
