@echo off
setlocal
echo Installing Crypto Intelligence Platform v7.0...
python -m pip install -r requirements.txt

python apply_v7_0_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v7_0.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

echo.
echo v7.0 installation complete.
echo Run: python run_module25.py
echo Inspect: python inspect_module25.py
pause
endlocal
