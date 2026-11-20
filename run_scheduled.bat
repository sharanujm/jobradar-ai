@echo off
cd /d "%~dp0"
echo [%date% %time%] Starting scheduled job execution... >> job_automation.log
"%~dp0venv\Scripts\python.exe" "%~dp0run_now.py" >> job_automation.log 2>&1
echo [%date% %time%] Finished job execution. >> job_automation.log
