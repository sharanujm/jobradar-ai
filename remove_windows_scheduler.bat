@echo off
setlocal
set TASK_NAME=DailyJobHunter

echo =======================================================
echo Removing Windows Task: %TASK_NAME%
echo =======================================================

schtasks /Delete /TN "%TASK_NAME%" /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Task "%TASK_NAME%" has been removed from Windows Task Scheduler.
) else (
    echo.
    echo [INFO] Task was not found or could not be removed.
)

pause
