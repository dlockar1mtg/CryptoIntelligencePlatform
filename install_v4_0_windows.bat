@echo off
setlocal
echo Installing Crypto Intelligence Platform v4.0...
python -m pip install -r requirements.txt
python upgrade_to_v4_0.py
python smoke_test_v4_0.py
if errorlevel 1 (
    echo.
    echo Installation validation failed.
    exit /b 1
)
echo.
echo v4.0 installation complete.
echo Run calibration: python run_module15.py
echo Inspect calibration: python inspect_module15.py
pause
endlocal
