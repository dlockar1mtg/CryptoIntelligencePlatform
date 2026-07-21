@echo off
setlocal
echo Installing Crypto Intelligence Platform v10.0.0...
python -m pip install -r requirements.txt

python apply_v10_0_0_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v10_0_0.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

python test_v9_2_1_hotfix.py
if errorlevel 1 (
    echo.
    echo v9.2.1 stabilization test failed.
    exit /b 1
)

python test_v10_0_0_module38_schema.py
if errorlevel 1 (
    echo.
    echo Module 38 schema preflight failed.
    exit /b 1
)

echo.
echo v10.0.0 installation complete.
echo Optional stabilized optimizer rerun: python run_module37.py
echo Run predictive engine: python run_module38.py
echo Inspect predictive engine: python inspect_module38.py
echo Export predictive engine: python export_module38.py
pause
endlocal
