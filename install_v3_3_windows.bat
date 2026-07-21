@echo off
setlocal
echo Installing Crypto Intelligence Platform v3.3...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python upgrade_to_v3_3.py
python smoke_test_v3_3.py
echo.
echo v3.3 installation complete.
echo Recommended first run: python run_module13.py
echo Inspect: python inspect_module13.py
pause
endlocal
