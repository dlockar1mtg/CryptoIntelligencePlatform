@echo off
setlocal
echo Scanning Crypto DuckDB databases...
python recover_crypto_database.py
if errorlevel 1 (
    echo.
    echo Database scan failed.
    exit /b 1
)
echo.
echo Review the report before restoring.
pause
endlocal
