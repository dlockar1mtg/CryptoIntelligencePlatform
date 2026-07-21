@echo off
setlocal
echo Installing Crypto Intelligence Platform v4.2...
python -m pip install -r requirements.txt
python upgrade_to_v4_2.py
python smoke_test_v4_2.py
if errorlevel 1 (
    echo.
    echo Installation validation failed.
    exit /b 1
)
echo.
echo v4.2 installation complete.
echo Run feature expansion: python run_module17.py
echo Inspect: python inspect_module17.py
pause
endlocal
