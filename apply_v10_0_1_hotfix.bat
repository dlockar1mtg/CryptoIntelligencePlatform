@echo off
setlocal
echo Applying Crypto Intelligence Platform v10.0.1 hotfix...

python apply_v10_0_1_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v10_0_1.py
if errorlevel 1 (
    echo.
    echo Database hotfix failed.
    exit /b 1
)

python test_v10_0_1_adaptive_history.py
if errorlevel 1 (
    echo.
    echo Adaptive-history smoke test failed.
    exit /b 1
)

python test_v10_0_0_module38_schema.py
if errorlevel 1 (
    echo.
    echo Module 38 schema preflight failed.
    exit /b 1
)

echo.
echo v10.0.1 hotfix complete.
echo Run: python run_module38.py
echo Inspect: python inspect_module38.py
echo Export: python export_module38.py
pause
endlocal
