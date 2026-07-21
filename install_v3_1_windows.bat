@echo off
setlocal
echo Installing Crypto Intelligence Platform v3.1...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
if not exist data mkdir data
if not exist data\cache mkdir data\cache
if not exist data\exports mkdir data\exports
if not exist data\models mkdir data\models
if not exist logs mkdir logs
python upgrade_to_v3_1.py
python smoke_test_v3_1.py
echo.
echo v3.1 installation complete.
echo Run everything: python run_all.py
echo Run reliability upgrades only: python run_module11.py
echo Inspect reliability results: python inspect_module11.py
pause
endlocal
