@echo off
setlocal
echo Applying Crypto Intelligence Platform v11.0.1 Memory Persistence Engine...

python apply_v11_0_1_config.py
if errorlevel 1 (
    echo.
    echo Configuration update failed.
    exit /b 1
)

python upgrade_to_v11_0_1.py
if errorlevel 1 (
    echo.
    echo Memory persistence upgrade failed.
    exit /b 1
)

python test_v11_0_1_memory_persistence.py
if errorlevel 1 (
    echo.
    echo Memory persistence preflight failed.
    exit /b 1
)

echo.
echo v11.0.1 installation complete.
echo Run memory engine: python run_module40.py
echo Inspect memory: python inspect_module40.py
echo Re-run memory engine to confirm idempotency: python run_module40.py
echo Inspect again: python inspect_module40.py
echo Then refresh meta-learning: python run_module41.py
pause
endlocal
