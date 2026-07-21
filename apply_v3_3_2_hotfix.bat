@echo off
setlocal
echo Applying Crypto Intelligence Platform v3.3.2 hotfix...
python apply_v3_3_2_hotfix.py
if errorlevel 1 (
    echo.
    echo Hotfix failed. Review the error above.
    exit /b 1
)
echo.
echo Hotfix complete.
echo Run: python run_module13.py
pause
endlocal
