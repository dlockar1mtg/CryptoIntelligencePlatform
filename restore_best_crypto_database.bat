@echo off
setlocal
echo Restoring the strongest Crypto DuckDB backup...
python recover_crypto_database.py --restore-best
if errorlevel 1 (
    echo.
    echo Database recovery failed.
    exit /b 1
)
echo.
echo Recovery complete.
pause
endlocal
