# Albion Profit Calculator

Калькулятор и анализатор выгодных торговых маршрутов между городами Albion Online.

## Стек технологий
- **Backend:** FastAPI, Uvicorn, Psycopg2, Requests, Python-dotenv
- **Database:** PostgreSQL (схема `albion`)
- **Frontend:** HTML5, CSS3, Vanilla JS

---

## Быстрый старт

### 1. Запуск базы данных (PostgreSQL)

#### Вариант A: Через Docker (рекомендуется)
```bash
docker compose up -d
```
Скрипт [init.sql](file:///C:/Users/andrew/Desktop/albion-profit-calculator/init.sql) применится автоматически при первом запуске (создаст схему `albion`, таблицы и города).

#### Вариант B: Локальный PostgreSQL
Создайте базу `albion_profit` и накатите схему:
```bash
psql -U postgres -d albion_profit -f init.sql
```

---

### 2. Запуск бэкенда

1. Активируйте виртуальное окружение:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
2. Установите зависимости (если еще не установлены):
   ```bash
   pip install -r requirements.txt
   ```
3. Запустите сервер:
   ```bash
   python main.py
   ```
   API будет доступно по адресу: http://127.0.0.1:8000  
   Документация Swagger: http://127.0.0.1:8000/docs

---

### 3. Запуск фронтенда
Откройте [index.html](file:///C:/Users/andrew/Desktop/albion-profit-calculator/index.html) в браузере (или через расширение Live Server в VS Code).
