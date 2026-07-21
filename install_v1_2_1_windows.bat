@echo off
setlocal
echo Installing Crypto Intelligence Platform v1.2.1...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
if not exist data mkdir data
if not exist data\cache mkdir data\cache
if not exist data\exports mkdir data\exports
if not exist logs mkdir logs
python upgrade_to_v1_2_1.py
python smoke_test_v1_2_1.py
echo.
echo v1.2.1 installation complete.
echo Run everything: python run_all.py
echo Inspect results: python inspect_module2.py
pause
endlocal
