@echo off
setlocal
echo Installing Crypto Intelligence Platform v3.3.4...
python -m pip install -r requirements.txt
python upgrade_to_v3_3_4.py
python smoke_test_v3_3_4.py
if errorlevel 1 (
    echo.
    echo Installation validation failed.
    exit /b 1
)
echo.
echo v3.3.4 installation complete.
echo Run validation: python run_module14.py
echo Inspect validation: python inspect_module14.py
pause
endlocal
