@echo off
setlocal
echo Installing Crypto Intelligence Platform v4.2.1...
python -m pip install -r requirements.txt
python apply_v4_2_1_config.py
if errorlevel 1 (
  echo.
  echo Configuration update failed.
  exit /b 1
)
python upgrade_to_v4_2_1.py
if errorlevel 1 (
  echo.
  echo Database upgrade failed.
  exit /b 1
)
echo.
echo v4.2.1 installation complete.
echo Run: python run_module18.py
echo Inspect: python inspect_module18.py
pause
endlocal
