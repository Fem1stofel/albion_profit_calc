@echo off
chcp 65001 > nul
title Albion Profit Calculator

echo ======================================================
echo    Albion Profit Calculator - Быстрый запуск
echo ======================================================
echo.

:: 1. Проверяем Docker
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto LOCAL_PYTHON

docker info >nul 2>&1
if %ERRORLEVEL% EQU 0 goto DOCKER_READY

if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
    echo [..] Docker установлен, но не запущен. Запуск Docker Desktop...
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    echo [..] Ожидание инициализации Docker...
    timeout /t 15 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 16 >nul
)

docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 goto LOCAL_PYTHON

:DOCKER_READY
echo [OK] Обнаружен работающий Docker!
echo [..] Запуск проекта и базы данных в контейнерах...
echo.
docker compose up --build -d
if %ERRORLEVEL% NEQ 0 (
    echo [!] Ошибка запуска через Docker Compose. Переходим к локальному запуску...
    goto LOCAL_PYTHON
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
:: 2. Локальный запуск через Python
echo [..] Проверка Python на компьютере...
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 goto PYTHON_FOUND

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
    echo [..] Создание файла конфигурации .env из примера...
    copy .env.example .env >nul
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

:: Проверяем доступность базы данных PostgreSQL
if not exist ".venv\Scripts\python.exe" goto LAUNCH_SERVER

.venv\Scripts\python.exe -c "import psycopg2, os; from dotenv import load_dotenv; load_dotenv(); psycopg2.connect(host=os.getenv('DB_HOST','localhost'), port=int(os.getenv('DB_PORT',5432)), user=os.getenv('DB_USER','postgres'), password=os.getenv('DB_PASSWORD','123'), database=os.getenv('DB_NAME','albion_profit'), connect_timeout=3)" >nul 2>&1
if %ERRORLEVEL% EQU 0 goto LAUNCH_SERVER

echo.
echo ======================================================
echo  [!] ВНИМАНИЕ: База данных PostgreSQL недоступна!
echo ======================================================
echo.
echo Для работы приложения необходима база данных PostgreSQL.
echo Самый простой способ запустить всё в 1 клик без ручной настройки:
echo   1. Установите Docker Desktop: https://www.docker.com/products/docker-desktop/
echo   2. Запустите start.bat снова - он сам поднимет базу и веб-сервер.
echo.
pause
exit /b 1

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
