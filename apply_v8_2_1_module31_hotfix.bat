@echo off
setlocal
echo Applying Crypto Intelligence Platform v8.2.1 Module 31 hotfix...

python test_v8_2_1_module31_schema.py
if errorlevel 1 (
    echo.
    echo Module 31 schema preflight failed.
    exit /b 1
)

python upgrade_to_v8_2_1.py
if errorlevel 1 (
    echo.
    echo v8.2.1 hotfix failed.
    exit /b 1
)

echo.
echo v8.2.1 hotfix complete.
echo Run: python run_module31.py
echo Then: python inspect_module31.py
pause
endlocal
