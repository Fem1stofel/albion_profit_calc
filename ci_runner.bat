@echo off
setlocal

:: 1. If local .venv already exists in current workspace, use it
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
    goto FOUND
)

:: 2. Find a real base Python installation (specifically EXCLUDING WindowsApps store alias)
set "BASE_PY="

if exist "C:\Users\andrew\AppData\Local\Programs\Python\Python311\python.exe" (
    set "BASE_PY=C:\Users\andrew\AppData\Local\Programs\Python\Python311\python.exe"
    goto CREATE_VENV
)
if exist "C:\Users\andrew\AppData\Local\Programs\Python\Python312\python.exe" (
    set "BASE_PY=C:\Users\andrew\AppData\Local\Programs\Python\Python312\python.exe"
    goto CREATE_VENV
)
if exist "C:\Users\andrew\AppData\Local\Programs\Python\Python313\python.exe" (
    set "BASE_PY=C:\Users\andrew\AppData\Local\Programs\Python\Python313\python.exe"
    goto CREATE_VENV
)
if exist "C:\Users\andrew\AppData\Local\Programs\Python\Python314\python.exe" (
    set "BASE_PY=C:\Users\andrew\AppData\Local\Programs\Python\Python314\python.exe"
    goto CREATE_VENV
)
if exist "C:\Program Files\Python311\python.exe" (
    set "BASE_PY=C:\Program Files\Python311\python.exe"
    goto CREATE_VENV
)
if exist "C:\Program Files\Python312\python.exe" (
    set "BASE_PY=C:\Program Files\Python312\python.exe"
    goto CREATE_VENV
)

:: Search path for any python that is NOT in WindowsApps
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    echo "%%i" | findstr /i "WindowsApps" >nul
    if errorlevel 1 (
        set "BASE_PY=%%i"
        goto CREATE_VENV
    )
)

echo [!] ERROR: Real Python installation was not found.
exit /b 1

:CREATE_VENV
echo [*] Initializing virtual environment in .venv using: %BASE_PY%
"%BASE_PY%" -m venv .venv
if errorlevel 1 (
    echo [!] Failed to create .venv, running with base python: %BASE_PY%
    set "PY=%BASE_PY%"
    goto FOUND
)

set "PY=.venv\Scripts\python.exe"

:FOUND
"%PY%" %*
exit /b %ERRORLEVEL%
