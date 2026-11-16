@echo off
rem Week 10 ground-motion AI training, launched by Task Scheduler. Finished folds are skipped.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if not exist results_ground_ai mkdir results_ground_ai
"C:\Users\aim88\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\python.exe" ground_ai.py >> results_ground_ai\scheduler_stdout.log 2>&1
