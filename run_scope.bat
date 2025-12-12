@echo off
cd /d "C:\GitRepos\pyScope"
if exist "C:\Users\wollmanlab\miniconda3\envs\pyscope_3.12\python.exe" (
    "C:\Users\wollmanlab\miniconda3\envs\pyscope_3.12\python" -m Scope.scope
) else if exist "C:\Users\wollmanlab\miniconda3\envs\pycro_3.12\python.exe" (
    "C:\Users\wollmanlab\miniconda3\envs\pycro_3.12\python" -m Scope.scope
) else if exist "C:\Users\wollmanlab\.conda\envs\pyscope_3.12\python.exe" (
    "C:\Users\wollmanlab\.conda\envs\pyscope_3.12\python" -m Scope.scope
) else if exist "C:\Users\wollmanlab\.conda\envs\pycro_3.12\python.exe" (
    "C:\Users\wollmanlab\.conda\envs\pycro_3.12\python" -m Scope.scope
) else (
    echo Error: Neither pyscope_3.12 nor pycro_3.12 environment found.
    pause
    exit /b 1
)
pause

