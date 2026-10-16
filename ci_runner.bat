@echo off
setlocal

:: 1. Search for python executable
set "PY="

:: Check local .venv in current directory
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
    goto FOUND
)

:: Check python in PATH
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY=python"
    goto FOUND
)

:: Check workspace .venv
if exist "C:\Users\andrew\Desktop\albion-profit-calculator\.venv\Scripts\python.exe" (
    set "PY=C:\Users\andrew\Desktop\albion-profit-calculator\.venv\Scripts\python.exe"
    goto FOUND
)

:: Check user installations
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto FOUND
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto FOUND
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto FOUND
)
if exist "C:\Users\andrew\AppData\Local\Programs\Python\Python311\python.exe" (
    set "PY=C:\Users\andrew\AppData\Local\Programs\Python\Python311\python.exe"
    goto FOUND
)
if exist "C:\Users\andrew\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PY=C:\Users\andrew\AppData\Local\Programs\Python\Python312\python.exe"
    goto FOUND
)
if exist "C:\Users\andrew\AppData\Local\Programs\Python\Python313\python.exe" (
    set "PY=C:\Users\andrew\AppData\Local\Programs\Python\Python313\python.exe"
    goto FOUND
)

echo [!] ERROR: Python executable was not found.
exit /b 1

:FOUND
"%PY%" %*
exit /b %ERRORLEVEL%
