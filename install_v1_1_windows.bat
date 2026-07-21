@echo off
setlocal
echo Installing Crypto Intelligence Platform v1.1...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
if not exist data mkdir data
if not exist data\cache mkdir data\cache
if not exist data\exports mkdir data\exports
if not exist logs mkdir logs
python upgrade_to_v1_1.py
python smoke_test.py
echo.
echo v1.1 installation complete.
echo Run: python run_module1.py
pause
endlocal
