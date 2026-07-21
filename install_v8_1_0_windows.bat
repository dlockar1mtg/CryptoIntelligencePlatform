@echo off
setlocal
echo Installing Crypto Intelligence Platform v8.1.0...
python -m pip install -r requirements.txt

python test_v8_1_0_compatibility.py
if errorlevel 1 (
    echo.
    echo Machine-learning compatibility test failed.
    exit /b 1
)

python apply_v8_1_0_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v8_1_0.py
if errorlevel 1 (
    echo.
    echo Database upgrade failed.
    exit /b 1
)

echo.
echo v8.1.0 installation complete.
echo Run: python run_module30.py
echo Inspect: python inspect_module30.py
pause
endlocal
