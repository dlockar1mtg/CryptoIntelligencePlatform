@echo off
setlocal
echo Applying Crypto Intelligence Platform v7.0.2 feature-matrix hotfix...

python apply_v7_0_2_hotfix.py
if errorlevel 1 (
    echo.
    echo v7.0.2 hotfix failed.
    exit /b 1
)

echo.
echo v7.0.2 hotfix complete.
echo Run: python run_module25.py
echo Then: python inspect_module25.py
pause
endlocal
