@echo off
setlocal
echo Installing Crypto Intelligence Platform v4.2.3...
python -m pip install -r requirements.txt
python apply_v4_2_3_config.py
if errorlevel 1 (echo Configuration update failed.& exit /b 1)
python upgrade_to_v4_2_3.py
if errorlevel 1 (echo Database upgrade failed.& exit /b 1)
echo.
echo v4.2.3 installation complete.
echo Run: python run_module20.py
echo Inspect: python inspect_module20.py
pause
endlocal
