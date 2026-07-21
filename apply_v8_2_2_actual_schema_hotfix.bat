@echo off
setlocal
echo Applying Crypto Intelligence Platform v8.2.2 actual-schema hotfix...

python test_v8_2_2_module31_schema.py
if errorlevel 1 (
    echo.
    echo Module 31 actual-schema preflight failed.
    exit /b 1
)

python upgrade_to_v8_2_2.py
if errorlevel 1 (
    echo.
    echo v8.2.2 hotfix failed.
    exit /b 1
)

echo.
echo v8.2.2 hotfix complete.
echo Run: python run_module31.py
echo Then: python inspect_module31.py
echo Then: python export_module31.py
pause
endlocal
