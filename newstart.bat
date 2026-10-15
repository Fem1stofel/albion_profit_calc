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
echo.

:: 2. Запуск основного проекта (ручная среда 8000/5432)
echo [..] Запуск проекта и базы данных в контейнерах...
echo.
docker compose up --build -d
if %ERRORLEVEL% NEQ 0 (
    echo [!] Ошибка запуска через Docker Compose. Переходим к локальному запуску...
    goto LOCAL_PYTHON
)

:: 3. Запуск Jenkins (CI/CD)
echo.
echo ======================================================
echo    Настройка CI/CD (Jenkins)
echo ======================================================
echo.

:: 3.1. Проверяем наличие образа my-jenkins
docker image inspect my-jenkins >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [..] Образ Jenkins не найден. Собираем (первый раз 2-5 минут)...
    docker build -t my-jenkins -f Dockerfile.jenkins .
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Не удалось собрать образ Jenkins. CI/CD пропущен.
        goto SKIP_JENKINS
    )
    echo [OK] Образ Jenkins собран.
) else (
    echo [OK] Образ my-jenkins найден.
)

:: 3.2. Контейнер jenkins-server уже запущен?
docker ps --filter "name=^jenkins-server$" --filter "status=running" | findstr jenkins-server >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Jenkins уже запущен.
    goto JENKINS_READY
)

:: 3.3. Контейнер существует, но остановлен?
docker ps -a --filter "name=^jenkins-server$" | findstr jenkins-server >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [..] Запуск существующего контейнера Jenkins...
    docker start jenkins-server >nul 2>&1
    goto JENKINS_WAIT
)

:: 3.4. Контейнера нет — создаём новый
echo [..] Создание контейнера Jenkins...
docker run -d --name jenkins-server --restart=on-failure -p 8081:8080 -p 50000:50000 -v jenkins_home:/var/jenkins_home -v //var/run/docker.sock:/var/run/docker.sock --user root my-jenkins
if %ERRORLEVEL% NEQ 0 (
    echo [!] Не удалось запустить Jenkins. CI/CD пропущен.
    goto SKIP_JENKINS
)

:JENKINS_WAIT
echo [..] Ожидание запуска Jenkins (30 секунд)...
timeout /t 30 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 31 >nul

:JENKINS_READY
echo.
echo ======================================================
echo    Всё готово!
echo ======================================================
echo.
echo  Ручная среда (для разработки):
echo    Web-интерфейс:   http://localhost:8000
echo    Swagger API:     http://localhost:8000/docs
echo.
echo  CI/CD Jenkins:
echo    Jenkins:         http://localhost:8081
echo    CI-приложение:   http://localhost:8001  (появится после первой сборки)
echo.
echo ======================================================
echo  Команды для управления:
echo    docker compose down             - остановить ручную среду
echo    docker stop jenkins-server      - остановить Jenkins
echo    docker rm -f jenkins-server     - удалить Jenkins
echo ======================================================
echo.

:: 3.5. Если Jenkins только что создан — выведем пароль администратора
echo [..] Если Jenkins запускается впервые, пароль администратора:
docker exec jenkins-server cat /var/jenkins_home/secrets/initialAdminPassword 2>nul
echo.

timeout /t 3 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 4 >nul
start http://localhost:8000
timeout /t 2 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 3 >nul
start http://localhost:8081
pause
exit /b 0

:SKIP_JENKINS
echo.
echo ======================================================
echo  Проект запущен, но Jenkins не настроен.
echo  CI/CD пропущен. Ручная среда работает:
echo    http://localhost:8000
echo ======================================================
echo.
echo  Чтобы починить CI/CD, проверьте:
echo    1. Файл Dockerfile.jenkins существует в папке проекта.
echo    2. Свободны порты 8081 и 50000.
echo    3. Запустите вручную: docker build -t my-jenkins -f Dockerfile.jenkins .
echo.
timeout /t 3 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 4 >nul
start http://localhost:8000
pause
exit /b 0

:LOCAL_PYTHON
:: 4. Локальный запуск через Python (без Docker)
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
echo Примечание: CI/CD (Jenkins) требует Docker Desktop.
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
echo Примечание: CI/CD (Jenkins) требует Docker Desktop.
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
echo [i] Jenkins (CI/CD) не запущен - для этого нужен Docker Desktop.
echo.

timeout /t 2 /nobreak >nul 2>&1 || ping 127.0.0.1 -n 3 >nul
start http://localhost:8000

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe main.py
) else (
    python main.py
)

pause