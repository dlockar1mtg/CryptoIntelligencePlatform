@echo off
setlocal
echo Installing Crypto Intelligence Platform v3.2...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python upgrade_to_v3_2.py
python smoke_test_v3_2.py
echo.
echo v3.2 installation complete.
echo Recommended first run: python run_module12.py
echo Inspect: python inspect_module12.py
pause
endlocal
