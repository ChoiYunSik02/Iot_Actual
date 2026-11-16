@echo off
rem Week 10 B2/B3 night queue, launched by Task Scheduler. Finished folds/parts are skipped.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set WORKERS=14
if not exist results_b2 mkdir results_b2
"C:\Users\aim88\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\python.exe" b2_night.py all >> results_b2\scheduler_stdout.log 2>&1
