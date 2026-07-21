@echo off
setlocal
echo Installing Crypto Intelligence Platform v7.1...
python -m pip install -r requirements.txt
python apply_v7_1_config.py
if errorlevel 1 exit /b 1
python upgrade_to_v7_1.py
if errorlevel 1 exit /b 1
echo.
echo v7.1 installation complete.
echo Run: python run_module26.py
echo Inspect: python inspect_module26.py
pause
endlocal
