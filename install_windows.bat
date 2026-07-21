@echo off
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
python smoke_test.py
echo.
echo Installation complete. Run: python run_module1.py
pause
