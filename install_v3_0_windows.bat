@echo off
setlocal
echo Installing Crypto Intelligence Platform v3.0...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
if not exist data mkdir data
if not exist data\cache mkdir data\cache
if not exist data\exports mkdir data\exports
if not exist data\models mkdir data\models
if not exist logs mkdir logs
python upgrade_to_v3_0.py
python smoke_test_v3_0.py
echo.
echo v3.0 installation complete.
echo Run everything: python run_all.py
echo Run institutional expansion only: python run_module10.py
echo Inspect institutional data: python inspect_module10.py
pause
endlocal
