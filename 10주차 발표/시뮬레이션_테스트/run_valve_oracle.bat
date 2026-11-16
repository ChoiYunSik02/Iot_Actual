@echo off
rem Week 10 B0': valve oracle trajectories, launched by Task Scheduler. Finished records are skipped.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
if not exist results_valve_oracle mkdir results_valve_oracle
"C:\Users\aim88\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\python.exe" valve_oracle_traj.py >> results_valve_oracle\scheduler_stdout.log 2>&1
