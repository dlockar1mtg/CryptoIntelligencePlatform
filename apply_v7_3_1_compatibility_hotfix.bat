@echo off
setlocal
echo Applying Crypto Intelligence Platform v7.3.1 compatibility hotfix...

python apply_v7_3_1_hotfix.py
if errorlevel 1 (
    echo.
    echo v7.3.1 code compatibility patch failed.
    exit /b 1
)

python apply_v7_3_1_config.py
if errorlevel 1 (
    echo.
    echo v7.3.1 version metadata update failed.
    exit /b 1
)

echo.
echo v7.3.1 compatibility hotfix complete.
echo Run: python run_module28.py
echo Then: python inspect_module28.py
pause
endlocal
