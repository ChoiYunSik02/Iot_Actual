@echo off
rem Week 10 plan 15.2: b3s seed repeats. Waits for b3l15 DONE so two jobs never share memory.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set WORKERS=16
if not exist results_b2 mkdir results_b2
:wait
if exist results_b2\b3l15\DONE goto run
ping -n 301 127.0.0.1 >nul
goto wait
:run
"C:\Users\aim88\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\python.exe" b2_night.py b3s >> results_b2\scheduler_stdout_b3s.log 2>&1
