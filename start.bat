@echo off
chcp 65001 > nul
title Albion Profit Calculator

echo ======================================================
echo    Albion Profit Calculator - Быстрый запуск
echo ======================================================
echo.

:: 1. Проверяем, установлен и запущен ли Docker
docker info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Обнаружен работающий Docker!
    echo [..] Запуск проекта и базы данных в контейнерах...
    echo.
    docker compose up --build -d
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Ошибка запуска Docker Compose. Попробуем альтернативный запуск...
        goto LOCAL_PYTHON
    )
    echo.
    echo ======================================================
    echo  [OK] Проект успешно запущен!
    echo  Web-интерфейс: http://localhost:8000
    echo  API документация: http://localhost:8000/docs
    echo ======================================================
    timeout /t 3 >nul
    start http://localhost:8000
    echo.
    echo Для остановки проекта выполните в этой папке: docker compose down
    pause
    exit /b 0
)

:LOCAL_PYTHON
:: 2. Если Docker нет, пробуем запустить через локальный Python
echo [..] Проверка Python на компьютере...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] ОШИБКА: На компьютере не найдены ни Docker, ни Python!
    echo.
    echo Чтобы запустить проект, установите одно из двух:
    echo   1. Docker Desktop (рекомендуется): https://www.docker.com/products/docker-desktop/
    echo   ИЛИ
    echo   2. Python 3.10+ (с галочкой 'Add Python to PATH'): https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

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

:: Активируем .venv
echo [..] Активация виртуального окружения...
call .venv\Scripts\activate.bat

:: Проверяем и устанавливаем зависимости
echo [..] Проверка зависимостей Python...
python -m pip install -r requirements.txt

echo.
echo ======================================================
echo  [OK] Запуск сервера Albion Profit Calculator...
echo  Web-интерфейс: http://localhost:8000
echo  API документация: http://localhost:8000/docs
echo ======================================================
echo.

timeout /t 2 >nul
start http://localhost:8000
python main.py

pause
