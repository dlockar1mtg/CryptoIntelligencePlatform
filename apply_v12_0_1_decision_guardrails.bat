@echo off
setlocal
echo Applying Crypto Intelligence Platform v12.0.1 Decision Guardrails...

python apply_v12_0_1_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v12_0_1.py
if errorlevel 1 (
    echo.
    echo Decision guardrail upgrade failed.
    exit /b 1
)

python test_v12_0_1_decision_guardrails.py
if errorlevel 1 (
    echo.
    echo Decision guardrail preflight failed.
    exit /b 1
)

echo.
echo v12.0.1 installation complete.
echo Run: python run_module42.py
echo Inspect: python inspect_module42.py
echo Export: python export_module42.py
pause
endlocal
