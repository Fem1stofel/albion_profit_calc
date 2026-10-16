"""
Albion Profit Calculator - Database Initialization Script
==========================================================
Инициализирует базу данных PostgreSQL БЕЗ использования Docker-контейнеров:
1. Проверяет наличие базы данных (по умолчанию albion_profit).
2. Если базы нет — подключается к системной базе postgres и создаёт её.
3. Применяет схему init.sql (создаёт схему albion, таблицы locations, items, market_orders).
4. Наполняет таблицу albion.items базовыми данными из data/items.json.gz (если она пуста).
"""

import os
import sys
import json
import gzip
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import execute_values

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123")
DB_NAME = os.getenv("DB_NAME", "albion_profit")
DB_SCHEMA = os.getenv("DB_SCHEMA", "albion")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INIT_SQL_FILE = os.path.join(BASE_DIR, "init.sql")
COMPRESSED_ITEMS_FILE = os.path.join(BASE_DIR, "data", "items.json.gz")


def get_maintenance_connection():
    """Подключение к системной БД postgres или template1 для проверки/создания целевой базы."""
    for db_candidate in ["postgres", "template1"]:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=db_candidate,
                connect_timeout=5
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except Exception:
            continue
    raise psycopg2.OperationalError(f"Не удалось подключиться к системной базе на {DB_HOST}:{DB_PORT}")


def get_target_connection():
    """Подключение к целевой БД приложения."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        connect_timeout=5
    )
    return conn


def database_exists() -> bool:
    """Проверяет существование базы данных DB_NAME на сервере."""
    try:
        conn = get_maintenance_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cur.fetchone() is not None
        cur.close()
        conn.close()
        return exists
    except Exception as e:
        print(f"[!] Ошибка подключения к серверу PostgreSQL ({DB_HOST}:{DB_PORT}): {e}")
        raise


def create_database():
    """Создаёт базу данных DB_NAME, если её нет."""
    conn = get_maintenance_connection()
    cur = conn.cursor()
    print(f"[*] База данных '{DB_NAME}' не найдена. Создание новой базы данных...")
    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
    cur.close()
    conn.close()
    print(f"[OK] База данных '{DB_NAME}' успешно создана.")


def apply_init_sql():
    """Применяет SQL-скрипт init.sql (схема, таблицы, сиды локаций)."""
    if not os.path.exists(INIT_SQL_FILE):
        print(f"[!] Файл init.sql не найден по пути: {INIT_SQL_FILE}")
        return

    conn = get_target_connection()
    cur = conn.cursor()
    with open(INIT_SQL_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    cur.execute(sql_content)
    conn.commit()
    cur.close()
    conn.close()
    print(f"[OK] Схема '{DB_SCHEMA}' и таблицы из init.sql успешно применены.")


def seed_items_if_needed():
    """Заполняет таблицу items из сжатого файла, если таблица пуста или имена не русифицированы."""
    if not os.path.exists(COMPRESSED_ITEMS_FILE):
        return

    conn = get_target_connection()
    cur = conn.cursor()
    cur.execute(f"SET search_path TO {DB_SCHEMA}, public")
    cur.execute("SELECT COUNT(*) FROM albion.items WHERE name = item_id")
    untranslated_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM albion.items")
    count = cur.fetchone()[0]

    if count == 0 or untranslated_count > 100:
        print(f"[*] Импорт и обновление русских названий предметов из {COMPRESSED_ITEMS_FILE}...")
        with gzip.open(COMPRESSED_ITEMS_FILE, "rt", encoding="utf-8") as f:
            items_data = json.load(f)

        records = []
        for k, v in items_data.items():
            ru_name = v.get("ru", k) if isinstance(v, dict) else (v[0] if isinstance(v, list) else v)
            records.append((k, ru_name, 0, 1.0))

        execute_values(
            cur,
            """
            INSERT INTO albion.items (item_id, name, tier, weight) 
            VALUES %s 
            ON CONFLICT (item_id) DO UPDATE SET name = EXCLUDED.name
            """,
            records,
            page_size=2000
        )
        conn.commit()
        print(f"[OK] Импортировано/обновлено {len(records)} предметов с русскими названиями в albion.items.")
    else:
        print(f"[OK] Таблица {DB_SCHEMA}.items уже содержит {count} локализованных записей.")

    cur.close()
    conn.close()


def verify_database():
    """Проверяет состояние базы и выводит статистику."""
    conn = get_target_connection()
    cur = conn.cursor()
    cur.execute(f"SET search_path TO {DB_SCHEMA}, public")

    cur.execute("SELECT COUNT(*) FROM albion.locations")
    loc_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM albion.items")
    item_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    print("=" * 60)
    print(f"[OK] База данных '{DB_NAME}' готова к работе!")
    print(f"     Хост: {DB_HOST}:{DB_PORT}")
    print(f"     Локаций: {loc_count}")
    print(f"     Предметов: {item_count}")
    print("=" * 60)


def init_database(auto_create: bool = True):
    """
    Главная функция: либо подключается к уже созданной БД, либо создаёт новую.
    """
    print("=" * 60)
    print("[*] Проверка и инициализация базы данных PostgreSQL (без Docker)")
    print(f"    Сервер: {DB_HOST}:{DB_PORT}, База: {DB_NAME}, Пользователь: {DB_USER}")
    print("=" * 60)

    exists = database_exists()
    if exists:
        print(f"[OK] Найдена существующая база данных '{DB_NAME}'. Подключение...")
    else:
        if auto_create:
            create_database()
        else:
            raise RuntimeError(f"База данных '{DB_NAME}' не существует, а auto_create отключен.")

    apply_init_sql()
    seed_items_if_needed()
    verify_database()


if __name__ == "__main__":
    try:
        init_database(auto_create=True)
        sys.exit(0)
    except Exception as exc:
        print(f"\n[!] КРИТИЧЕСКАЯ ОШИБКА инициализации БД: {exc}")
        sys.exit(1)
