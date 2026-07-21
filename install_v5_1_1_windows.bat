@echo off
setlocal
echo Installing Crypto Intelligence Platform v5.1.1...
python -m pip install -r requirements.txt
python apply_v5_1_1_config.py
if errorlevel 1 exit /b 1
python upgrade_to_v5_1_1.py
if errorlevel 1 exit /b 1
echo.
echo v5.1.1 installation complete.
echo Run: python run_module23.py
echo Inspect: python inspect_module23.py
pause
endlocal
