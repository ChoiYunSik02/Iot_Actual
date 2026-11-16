@echo off
rem Week 10 plan 17: full 62-pair training + freeze. Uses the desktop Python if present, else python from PATH.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if "%WORKERS%"=="" set WORKERS=3
set PY=C:\Users\aim88\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\python.exe
if not exist "%PY%" set PY=python
if not exist results_b2 mkdir results_b2
"%PY%" b2_night.py full >> results_b2\scheduler_stdout_full.log 2>&1
