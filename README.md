# Albion Profit Calculator 🚀

Калькулятор и анализатор выгодных торговых маршрутов между городами Albion Online.

---

## ⚡ Быстрый старт с нуля (для друзей)

### Вариант 1: Запуск в 1 клик на Windows (Самый простой)
Если вы скачали проект на Windows:
1. Просто запустите файл **`start.bat`** (двойным кликом).
2. Скрипт сам всё настроит:
   - Если на компьютере есть **Docker** — поднимет базу данных и проект в контейнерах.
   - Если Docker нет — создаст виртуальное окружение Python, установит библиотеки и запустит проект.
3. В браузере автоматически откроется **http://localhost:8000**.

---

### Вариант 2: Запуск через Docker (Рекомендуется для любой ОС)
*Не требует установки Python и PostgreSQL на ваш компьютер.*

1. Убедитесь, что у вас установлен и запущен **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**.
2. В терминале в папке проекта выполните одну команду:
   ```bash
   docker compose up --build
   ```
3. Откройте в браузере:
   - 🌐 **Web-интерфейс:** [http://localhost:8000](http://localhost:8000)
   - 📊 **Swagger API:** [http://localhost:8000/docs](http://localhost:8000/docs)

*Остановить проект: `Ctrl + C` или `docker compose down`.*

---

### Вариант 3: Ручной запуск (Local Python)

1. **Создайте и активируйте виртуальное окружение:**
   - **Windows:**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\activate
     ```
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
2. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Запустите приложение:**
   ```bash
   python main.py
   ```
4. Откройте в браузере: [http://localhost:8000](http://localhost:8000).

---

## 🛠 Стек технологий
- **Backend:** FastAPI, Uvicorn, Psycopg2, Requests
- **Database:** PostgreSQL 16 (схема `albion`)
- **Frontend:** HTML5, CSS3, Vanilla JS
- **Containers:** Docker & Docker Compose

## Изменения тоже тут должны считаться.