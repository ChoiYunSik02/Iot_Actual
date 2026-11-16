@echo off
rem Week 10 plan 16: linear policy control (b3lin). Uses the desktop Python if present, else python from PATH.
rem On another machine, copy untracked data first: results_ground_ai\data.npz, results_valve_oracle\rec_*.npz, results_b2\b3l, results_b2\b3s
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if "%WORKERS%"=="" set WORKERS=16
set PY=C:\Users\aim88\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\python.exe
if not exist "%PY%" set PY=python
if not exist results_b2 mkdir results_b2
"%PY%" b2_night.py b3lin >> results_b2\scheduler_stdout_b3lin.log 2>&1
