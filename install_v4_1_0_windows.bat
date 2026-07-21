@echo off
setlocal
echo Installing Crypto Intelligence Platform v4.1.0...
python -m pip install -r requirements.txt
python upgrade_to_v4_1_0.py
python smoke_test_v4_1_0.py
if errorlevel 1 (
 echo.
 echo Installation validation failed.
 exit /b 1
)
echo.
echo v4.1.0 installation complete.
echo Run optimization: python run_module16.py
echo Inspect: python inspect_module16.py
pause
endlocal
