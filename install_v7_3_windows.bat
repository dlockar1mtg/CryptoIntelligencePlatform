@echo off
setlocal
echo Installing Crypto Intelligence Platform v7.3...
python -m pip install -r requirements.txt

python apply_v7_3_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v7_3.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

echo.
echo v7.3 installation complete.
echo Run: python run_module28.py
echo Inspect: python inspect_module28.py
pause
endlocal
