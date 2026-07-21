@echo off
setlocal
echo Applying Crypto Intelligence Platform v3.3.5 recovery hotfix...
python apply_v3_3_5_recovery_hotfix.py
if errorlevel 1 (
    echo.
    echo Hotfix failed.
    exit /b 1
)
python diagnose_and_recover_v3_3_5.py
if errorlevel 1 (
    echo.
    echo Diagnosis failed.
    exit /b 1
)
echo.
echo Recovery diagnosis complete.
pause
endlocal
