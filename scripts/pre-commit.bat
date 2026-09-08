@echo off
REM Git Pre-commit Hook for Windows
echo [Quality Gate] Running Architecture & Quality Checks...
python scripts/check_all.py
if %ERRORLEVEL% NEQ 0 (
    echo [Quality Gate] Commit rejected due to quality check failures!
    exit /b 1
)
echo [Quality Gate] All checks passed!
exit /b 0

