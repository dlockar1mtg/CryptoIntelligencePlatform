@echo off
python run_all.py
if errorlevel 1 (
  echo.
  echo The platform ended with an error. Review the newest log.
  pause
  exit /b 1
)
python inspect_module3.py
pause
