@echo off
setlocal
echo Installing Crypto Intelligence Platform v8.2...
python -m pip install -r requirements.txt
python apply_v8_2_config.py
if errorlevel 1 exit /b 1
python upgrade_to_v8_2.py
if errorlevel 1 exit /b 1
echo.
echo v8.2 installation complete.
echo Run: python run_module31.py
echo Inspect: python inspect_module31.py
pause
endlocal
