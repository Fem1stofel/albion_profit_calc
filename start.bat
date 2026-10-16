@echo off
chcp 65001 > nul
title Albion Profit Calculator

echo ======================================================
echo    Albion Profit Calculator - Быстрый запуск
echo ======================================================
echo.

:: 1. Проверяем локальный Python (основной режим без Docker-контейнеров)
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 goto LOCAL_PYTHON

:: 2. Если Python не найден, проверяем Docker
where docker >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    docker info >nul 2>&1
    if %ERRORLEVEL% EQU 0 goto DOCKER_READY
    if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
        echo [..] Docker установлен, но не запущен. Запуск Docker Desktop...
        start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
        echo [..] Ожидание инициализации Docker...
        timeout /t 15 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 16 >nul
        docker info >nul 2>&1
        if %ERRORLEVEL% EQU 0 goto DOCKER_READY
    )
)

echo.
echo [!] ОШИБКА: На компьютере не найдены ни Python, ни Docker!
echo.
echo Чтобы запустить проект, установите Python 3.10+:
echo   https://www.python.org/downloads/
echo   (Обязательно отметьте галочку Add Python to PATH при установке!)
echo.
pause
exit /b 1

:DOCKER_READY
echo [OK] Обнаружен работающий Docker!
echo [..] Запуск проекта и базы данных в контейнерах...
echo.
docker compose up --build -d
if %ERRORLEVEL% NEQ 0 (
    echo [!] Ошибка запуска через Docker Compose.
    pause
    exit /b 1
)

echo.
echo ======================================================
echo  [OK] Проект успешно запущен в Docker!
echo  Web-интерфейс: http://localhost:8000
echo  API документация: http://localhost:8000/docs
echo ======================================================
timeout /t 3 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 4 >nul
start http://localhost:8000
echo.
echo Для остановки проекта выполните в этой папке: docker compose down
pause
exit /b 0

:LOCAL_PYTHON
echo [OK] Обнаружен Python на компьютере!
goto PYTHON_FOUND

echo.
echo [!] ОШИБКА: На компьютере не найдены ни Docker, ни Python!
echo.
echo Чтобы запустить проект, установите одно из двух:
echo   1. Docker Desktop: https://www.docker.com/products/docker-desktop/
echo   ИЛИ
echo   2. Python 3.10+: https://www.python.org/downloads/
echo      Обязательно отметьте галочку Add Python to PATH при установке!
echo.
pause
exit /b 1

:PYTHON_FOUND
:: Создаём .env, если его нет
if not exist ".env" (
    echo [..] Создание файла конфигурации .env...
    (
        echo DB_HOST=localhost
        echo DB_PORT=5432
        echo DB_NAME=albion_profit
        echo DB_USER=postgres
        echo DB_PASSWORD=123
    ) > .env
)

:: Создаём .venv, если его нет
if not exist ".venv" (
    echo [..] Создание виртуального окружения .venv...
    python -m venv .venv
)

:: Проверяем и устанавливаем зависимости
echo [..] Проверка зависимостей Python...
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m pip install -r requirements.txt
) else (
    python -m pip install -r requirements.txt
)

:: Проверяем доступность и подготавливаем базу данных PostgreSQL (подключаем существующую или создаем новую)
echo [..] Проверка и подготовка базы данных PostgreSQL...
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe init_db.py
) else (
    python init_db.py
)
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ======================================================
    echo  [!] ВНИМАНИЕ: База данных PostgreSQL недоступна!
    echo ======================================================
    echo.
    echo Для работы приложения необходима база данных PostgreSQL.
    echo Убедитесь, что служба PostgreSQL запущена на порту 5432
    echo и реквизиты в файле .env указаны корректно.
    echo.
    pause
    exit /b 1
)
goto LAUNCH_SERVER

:LAUNCH_SERVER
echo.
echo ======================================================
echo  [OK] Запуск сервера Albion Profit Calculator...
echo  Web-интерфейс: http://localhost:8000
echo  API документация: http://localhost:8000/docs
echo ======================================================
echo.

timeout /t 2 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 3 >nul
start http://localhost:8000

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe main.py
) else (
    python main.py
)

pause
