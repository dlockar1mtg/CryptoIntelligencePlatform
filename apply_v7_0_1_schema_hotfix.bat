@echo off
setlocal
echo Applying Crypto Intelligence Platform v7.0.1 schema hotfix...

python apply_v7_0_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v7_0.py
if errorlevel 1 (
    echo.
    echo v7.0.1 schema hotfix failed.
    exit /b 1
)

echo.
echo v7.0.1 schema hotfix complete.
echo Run: python run_module25.py
echo Then: python inspect_module25.py
pause
endlocal
