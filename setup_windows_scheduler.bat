@echo off
setlocal
cd /d "%~dp0"

set TASK_NAME=DailyJobHunter
set BATCH_PATH=%~dp0run_scheduled.bat

echo =======================================================
echo Setting up Windows Task Scheduler for Daily 8:00 PM Run
echo =======================================================
echo Task Name: %TASK_NAME%
echo Script:    %BATCH_PATH%
echo Trigger:   Daily at 20:00 (8:00 PM)
echo =======================================================

schtasks /Create /SC DAILY /TN "%TASK_NAME%" /TR "cmd /c \"\"%BATCH_PATH%\"\"" /ST 20:00 /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Daily Job Hunter task has been successfully scheduled!
    echo It will automatically run every night at 8:00 PM (20:00).
    echo You can check or test it anytime in the Windows "Task Scheduler" app.
) else (
    echo.
    echo [ERROR] Failed to schedule task. You might need to right-click and "Run as administrator".
)

pause
