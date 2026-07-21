@echo off
setlocal
echo Installing Crypto Intelligence Platform v2.1...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
if not exist data mkdir data
if not exist data\cache mkdir data\cache
if not exist data\exports mkdir data\exports
if not exist data\models mkdir data\models
if not exist logs mkdir logs
python upgrade_to_v2_1.py
python smoke_test_v2_1.py
echo.
echo v2.1 installation complete.
echo Run everything: python run_all.py
echo Run calibrated predictive engine: python run_module9.py
echo Inspect calibrated results: python inspect_module9.py
pause
endlocal
