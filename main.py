from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import psycopg2
import requests
from typing import Optional
from datetime import datetime
import traceback
import json
import os
from functools import lru_cache
from collections import defaultdict

app = FastAPI(title="Albion Profit Calculator")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "albion_profit"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "123"),
    "port": int(os.getenv("DB_PORT", 5432))
}

ALBION_ITEMS_DATA_URL = "https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/formatted/items.json"
LOCAL_ITEMS_FILE = os.path.join(os.path.dirname(__file__), "items.json")
ALBION_API_BASE = "https://www.albion-online-data.com/api/v2/stats/prices"
ALBION_LOCATIONS = "Thetford,Fort Sterling,Martlock,Bridgewatch,Lymhurst,Caerleon,Black Market"
CITY_MAP = {
    'Thetford': 4, 'Fort Sterling': 5, 'Martlock': 6,
    'Bridgewatch': 7, 'Lymhurst': 8, 'Caerleon': 9, 'Black Market': 10
}


def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SET search_path TO albion")
    cur.close()
    return conn


def build_icon_url(item_id: str) -> str:
    return f"https://render.albiononline.com/v1/item/{item_id}.png?size=64"


@lru_cache(maxsize=1)
def load_items_catalog() -> dict:
    """
    Загружает полный каталог предметов с переводами (RU/EN).
    Кэшируется в памяти процесса.
    """
    catalog = {}

    try:
        response = requests.get(ALBION_ITEMS_DATA_URL, timeout=20)
        response.raise_for_status()
        data = response.json()

        for entry in data:
            unique_name = entry.get("UniqueName")
            if not unique_name:
                continue

            localized = entry.get("LocalizedNames") or {}
            catalog[unique_name] = {
                "name_ru": localized.get("RU-RU") or localized.get("EN-US") or unique_name,
                "name_en": localized.get("EN-US") or unique_name,
                "icon_url": build_icon_url(unique_name)
            }
    except Exception:
        # Фолбэк на локальный список, если внешний источник временно недоступен
        if os.path.exists(LOCAL_ITEMS_FILE):
            with open(LOCAL_ITEMS_FILE, "r", encoding="utf-8") as f:
                grouped = json.load(f)
            for items in grouped.values():
                for item_id in items:
                    catalog[item_id] = {
                        "name_ru": item_id,
                        "name_en": item_id,
                        "icon_url": build_icon_url(item_id)
                    }

    return catalog


def get_item_meta(item_id: str) -> dict:
    catalog = load_items_catalog()
    return catalog.get(item_id, {
        "name_ru": item_id,
        "name_en": item_id,
        "icon_url": build_icon_url(item_id)
    })


def calculate_profit(buy_price: int, sell_price: int, tax_rate: float = 6.5) -> dict:
    """Расчёт прибыли с налогом 6.5%"""
    tax_multiplier = 1 - (tax_rate / 100)
    gross_profit = sell_price - buy_price
    tax_amount = sell_price * (tax_rate / 100)
    net_profit = (sell_price * tax_multiplier) - buy_price
    roi = (net_profit / buy_price * 100) if buy_price > 0 else 0

    return {
        "gross_profit": int(gross_profit),
        "tax": int(tax_amount),
        "net_profit": int(net_profit),
        "roi_percent": round(roi, 2)
    }


# Глобальные переменные для прогресса сканирования
scan_progress = {
    'running': False,
    'total': 0,
    'processed': 0,
    'current_item': '',
    'errors': 0,
    'found_routes': 0,
    'all_items': [],  # Сохраняем список предметов
    'started': False
}


@app.get("/api/scan-all-items")
async def scan_all_items(
        batch_size: int = Query(200, ge=1, le=5000, description="Предметов за один цикл сканирования"),
        api_chunk_size: int = Query(40, ge=1, le=100, description="Сколько item_id объединять в один запрос к Albion API"),
        use_full_catalog: bool = Query(True, description="Использовать полный каталог предметов Albion")
):
    """Сканирует предметы батчами и делает запросы к Albion API пакетами."""
    global scan_progress

    # Загружаем список предметов только один раз
    if not scan_progress['started']:
        all_items = []
        if use_full_catalog:
            all_items = list(load_items_catalog().keys())
        else:
            items_file = os.path.join(os.path.dirname(__file__), 'items.json')
            if not os.path.exists(items_file):
                raise HTTPException(status_code=404, detail="Файл items.json не найден")
            with open(items_file, 'r', encoding='utf-8') as f:
                all_items_dict = json.load(f)
            for _, items in all_items_dict.items():
                all_items.extend(items)

        if not all_items:
            raise HTTPException(status_code=500, detail="Список предметов пуст")

        scan_progress['all_items'] = all_items
        scan_progress['total'] = len(all_items)
        scan_progress['started'] = True
        scan_progress['running'] = True
        scan_progress['processed'] = 0
        scan_progress['errors'] = 0
        scan_progress['found_routes'] = 0

    # Если уже всё обработано
    if scan_progress['processed'] >= scan_progress['total']:
        scan_progress['running'] = False
        return {
            'status': 'completed',
            'progress': scan_progress,
            'message': '✅ Сканирование завершено!'
        }

    # Берём следующую порцию предметов
    start_idx = scan_progress['processed']
    end_idx = min(start_idx + batch_size, scan_progress['total'])
    batch = scan_progress['all_items'][start_idx:end_idx]

    results = []
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        for idx in range(0, len(batch), api_chunk_size):
            chunk = batch[idx:idx + api_chunk_size]
            scan_progress['current_item'] = chunk[0]

            grouped_prices = defaultdict(list)
            chunk_error = False

            try:
                joined_ids = ",".join(chunk)
                response = requests.get(
                    f"{ALBION_API_BASE}/{joined_ids}",
                    params={"locations": ALBION_LOCATIONS, "qualities": "1"},
                    timeout=12
                )
                if response.status_code != 200:
                    chunk_error = True
                else:
                    for price_data in response.json():
                        item_id = price_data.get("item_id")
                        if item_id:
                            grouped_prices[item_id].append(price_data)
            except Exception as e:
                print(f"❌ Batch error ({chunk[0]}...): {e}")
                chunk_error = True

            for item_id in chunk:
                try:
                    item_meta = get_item_meta(item_id)
                    cur.execute("""
                        INSERT INTO albion.items (item_id, name, tier, weight)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (item_id) DO NOTHING
                    """, (item_id, item_meta["name_ru"], 0, 1.0))

                    saved = 0
                    for price_data in grouped_prices.get(item_id, []):
                        city = price_data.get('city')
                        if city not in CITY_MAP:
                            continue
                        sell_price = price_data.get('sell_price_min', 0) or 0
                        if sell_price <= 0:
                            continue

                        cur.execute("""
                            INSERT INTO albion.market_orders (item_id, location_id, order_type, price, quantity, timestamp)
                            VALUES (%s, %s, 'sell', %s, %s, NOW())
                            ON CONFLICT (item_id, location_id, order_type)
                            DO UPDATE SET price = EXCLUDED.price, quantity = EXCLUDED.quantity, timestamp = NOW()
                        """, (item_id, CITY_MAP[city], sell_price, price_data.get('sell_volume', 0)))
                        saved += 1

                    if saved >= 2:
                        scan_progress['found_routes'] += 1
                        results.append({'item': item_id, 'cities': saved})

                    if chunk_error:
                        scan_progress['errors'] += 1
                except Exception as e:
                    print(f"❌ {item_id}: {e}")
                    scan_progress['errors'] += 1
                finally:
                    scan_progress['processed'] += 1

            conn.commit()
    finally:
        cur.close()
        conn.close()

    # Проверяем, завершено ли сканирование
    if scan_progress['processed'] >= scan_progress['total']:
        scan_progress['running'] = False
        return {
            'status': 'completed',
            'batch_processed': len(results),
            'progress': scan_progress,
            'new_items': results[:10]
        }

    return {
        'status': 'running',
        'batch_processed': len(results),
        'progress': scan_progress,
        'new_items': results[:10]
    }


@app.get("/api/scan-progress")
async def get_scan_progress():
    """📊 Получение прогресса сканирования"""
    return scan_progress


@app.get("/api/scan-reset")
async def reset_scan():
    """🔄 Сброс прогресса сканирования"""
    global scan_progress
    scan_progress = {
        'running': False,
        'total': 0,
        'processed': 0,
        'current_item': '',
        'errors': 0,
        'found_routes': 0,
        'all_items': [],
        'started': False
    }
    return {'status': 'reset'}


@app.get("/api/analyze-item/{item_id}")
async def analyze_item(item_id: str):
    """🔥 Анализирует предмет во всех городах"""
    try:
        url = f"https://www.albion-online-data.com/api/v2/stats/prices/{item_id}"
        params = {
            'locations': 'Thetford,Fort Sterling,Martlock,Bridgewatch,Lymhurst,Caerleon,Black Market',
            'qualities': '1'
        }

        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Предмет не найден в API")

        api_data = response.json()

        conn = get_db_connection()
        cur = conn.cursor()

        item_meta = get_item_meta(item_id)
        cur.execute("""
            INSERT INTO albion.items (item_id, name, tier, weight)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (item_id) DO NOTHING
        """, (item_id, item_meta["name_ru"], 0, 1.0))

        city_map = {
            'Thetford': 4, 'Fort Sterling': 5, 'Martlock': 6,
            'Bridgewatch': 7, 'Lymhurst': 8, 'Caerleon': 9, 'Black Market': 10
        }

        all_prices = []
        for price_data in api_data:
            city_name = price_data.get('city')
            if not city_name or city_name not in city_map:
                continue

            location_id = city_map[city_name]
            sell_price = price_data.get('sell_price_min', 0) or 0
            buy_price = price_data.get('buy_price_min', 0) or 0
            sell_volume = price_data.get('sell_volume', 0) or 0
            buy_volume = price_data.get('buy_volume', 0) or 0

            if sell_price > 0:
                cur.execute("""
                    INSERT INTO albion.market_orders (item_id, location_id, order_type, price, quantity, timestamp)
                    VALUES (%s, %s, 'sell', %s, %s, %s)
                    ON CONFLICT (item_id, location_id, order_type)
                    DO UPDATE SET price = EXCLUDED.price, quantity = EXCLUDED.quantity, timestamp = NOW()
                """, (item_id, location_id, sell_price, sell_volume, datetime.now()))

                all_prices.append({
                    'city': city_name,
                    'location_id': location_id,
                    'buy_price': buy_price,
                    'sell_price': sell_price,
                    'buy_volume': buy_volume,
                    'sell_volume': sell_volume
                })

        conn.commit()

        routes = []
        for buy_city in all_prices:
            for sell_city in all_prices:
                if buy_city['location_id'] == sell_city['location_id']:
                    continue
                if buy_city['sell_price'] >= sell_city['sell_price']:
                    continue

                profit = calculate_profit(buy_city['sell_price'], sell_city['sell_price'])
                max_qty = min(buy_city['sell_volume'], sell_city['sell_volume'])
                if max_qty == 0:
                    max_qty = 1

                if profit['net_profit'] > 0:
                    routes.append({
                        'item_id': item_id,
                        'name': item_meta["name_ru"],
                        'name_ru': item_meta["name_ru"],
                        'name_en': item_meta["name_en"],
                        'icon_url': item_meta["icon_url"],
                        'from_city': buy_city['city'],
                        'to_city': sell_city['city'],
                        'from_location_id': buy_city['location_id'],
                        'to_location_id': sell_city['location_id'],
                        'buy_price': buy_city['sell_price'],
                        'sell_price': sell_city['sell_price'],
                        'profit_per_item': profit['net_profit'],
                        'roi': profit['roi_percent'],
                        'max_quantity': max_qty,
                        'total_profit': profit['net_profit'] * max_qty,
                        'gross_profit': profit['gross_profit'],
                        'tax': profit['tax']
                    })

        routes.sort(key=lambda x: x['total_profit'], reverse=True)

        cur.close()
        conn.close()

        return {
            'success': True,
            'item_id': item_id,
            'item_name': item_meta["name_ru"],
            'item_name_ru': item_meta["name_ru"],
            'item_name_en': item_meta["name_en"],
            'icon_url': item_meta["icon_url"],
            'prices': all_prices,
            'routes': routes[:20],
            'best_route': routes[0] if routes else None,
            'total_routes': len(routes),
            'updated': datetime.now().isoformat()
        }

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка API Albion: {str(e)}")
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/transport-routes")
async def get_transport_routes(
        from_location: int = Query(..., description="ID города покупки"),
        to_location: int = Query(..., description="ID города продажи"),
        min_profit: int = Query(0, description="Минимальная прибыль"),
        limit: int = Query(50, description="Максимум результатов")
):
    """Поиск маршрутов между городами из базы данных"""
    try:
        if from_location == to_location:
            raise HTTPException(status_code=400, detail="Города должны быть разными")

        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT 
                b.item_id,
                i.name,
                i.tier,
                i.weight,
                b.price as buy_price,
                b.quantity as buy_quantity,
                s.price as sell_price,
                s.quantity as sell_quantity,
                l1.name as from_city,
                l2.name as to_city,
                l2.tax_rate as tax_rate
            FROM albion.market_orders b
            JOIN albion.market_orders s ON b.item_id = s.item_id
            JOIN albion.items i ON b.item_id = i.item_id
            JOIN albion.locations l1 ON b.location_id = l1.id
            JOIN albion.locations l2 ON s.location_id = l2.id
            WHERE b.location_id = %s 
              AND s.location_id = %s 
              AND b.order_type = 'sell'
              AND s.order_type = 'sell'
              AND b.price < s.price
              AND b.price > 0
              AND s.price > 0
            ORDER BY (s.price - b.price) DESC
            LIMIT %s
        """

        cur.execute(query, (from_location, to_location, limit))
        results = []

        for row in cur.fetchall():
            item_id, name, tier, weight, buy_price, buy_qty, sell_price, sell_qty, from_city, to_city, tax_rate = row
            item_meta = get_item_meta(item_id)

            max_quantity = min(buy_qty, sell_qty)
            profit = calculate_profit(buy_price, sell_price, tax_rate)

            if profit["net_profit"] >= min_profit:
                results.append({
                    "item_id": item_id,
                    "name": item_meta["name_ru"] if name == item_id else name,
                    "name_ru": item_meta["name_ru"],
                    "name_en": item_meta["name_en"],
                    "icon_url": item_meta["icon_url"],
                    "tier": tier,
                    "weight": float(weight),
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "max_quantity": max_quantity,
                    "total_profit": profit["net_profit"] * max_quantity,
                    "profit_per_item": profit["net_profit"],
                    "roi": profit["roi_percent"],
                    "from_city": from_city,
                    "to_city": to_city,
                    "tax_rate": tax_rate
                })

        cur.close()
        conn.close()

        return {"routes": results, "count": len(results)}

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/locations")
async def get_locations():
    """🔥 Только королевские города + Black Market"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, region, tax_rate 
            FROM albion.locations 
            WHERE id IN (4, 5, 6, 7, 8, 9, 10)
            ORDER BY id
        """)
        locations = [{"id": r[0], "name": r[1], "region": r[2], "tax_rate": float(r[3])} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return {"locations": locations}
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise


@app.get("/api/health")
async def health_check():
    """Проверка подключения к базе"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT current_database(), COUNT(*) FROM albion.market_orders WHERE price > 0")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok", "database": result[0], "orders": result[1]}
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.get("/api/items-catalog")
async def get_items_catalog(
        q: Optional[str] = Query(None, description="Поиск по ID или названию"),
        limit: int = Query(200, ge=1, le=20000, description="Максимум элементов")
):
    """
    Возвращает каталог предметов с локализацией и ссылками на PNG.
    """
    catalog = load_items_catalog()
    rows = []
    needle = q.lower().strip() if q else None

    for item_id, meta in catalog.items():
        if needle:
            searchable = f"{item_id} {meta['name_ru']} {meta['name_en']}".lower()
            if needle not in searchable:
                continue
        rows.append({
            "item_id": item_id,
            "name_ru": meta["name_ru"],
            "name_en": meta["name_en"],
            "icon_url": meta["icon_url"]
        })

    rows.sort(key=lambda x: x["item_id"])
    return {
        "count": len(rows),
        "items": rows[:limit]
    }


# Подключение раздачи фронтенда (static files & index.html)
assets_path = os.path.join(os.path.dirname(__file__), "assets")
if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")


@app.get("/", include_in_schema=False)
async def serve_index():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Albion Profit Calculator API is running. See /docs"}


if __name__ == "__main__":
    import uvicorn
    import sys

    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", 8000))

    print("=" * 60)
    print("[*] Albion Profit Calculator")
    print("=" * 60)
    print(f"[*] Web UI:   http://localhost:{port}")
    print(f"[*] API Docs: http://localhost:{port}/docs")
    print("=" * 60)
    uvicorn.run(app, host=host, port=port, reload=False)

