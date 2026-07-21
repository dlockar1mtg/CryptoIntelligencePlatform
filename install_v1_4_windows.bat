@echo off
setlocal
echo Installing Crypto Intelligence Platform v1.4...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
if not exist data mkdir data
if not exist data\cache mkdir data\cache
if not exist data\exports mkdir data\exports
if not exist logs mkdir logs
python upgrade_to_v1_4.py
python smoke_test_v1_4.py
echo.
echo v1.4 installation complete.
echo Run everything: python run_all.py
echo Custom monthly amount: python run_module3.py --monthly 500
echo With holdings: python run_module3.py --holdings-json current_holdings.example.json
pause
endlocal
