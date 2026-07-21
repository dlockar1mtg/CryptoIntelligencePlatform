@echo off
python run_module1.py
if errorlevel 1 (
  echo.
  echo Module 1 ended with an error. Review the newest file in logs.
  pause
  exit /b 1
)
python inspect_module1.py
pause
