import asyncio
import json
import psycopg2
from nats.aio.client import Client as NATS
from datetime import datetime
import traceback
import os
from dotenv import load_dotenv

load_dotenv()

# ================= НАСТРОЙКИ =================
NATS_URL = os.getenv("NATS_URL", "nats://public:thenewalbiondata@nats.albion-online-data.com:34222")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "albion_profit"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "123"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "options": "-c search_path=albion"
}


# =============================================

def convert_ticks_to_datetime(ticks: int) -> datetime:
    if not ticks or ticks < 621355968000000000:
        return datetime.now()
    seconds = (ticks - 621355968000000000) / 10000000
    return datetime.fromtimestamp(seconds)


async def save_market_order(dict, default_order_type: str):
    """Сохраняет рыночный ордер"""
    conn = None
    try:
        # 🔥 Используем dict вместо data
        item_id = dict.get('ItemTypeId', dict.get('item_id', ''))
        location_id = dict.get('LocationId', dict.get('location_id', 0))
        order_type = default_order_type

        # Правильное извлечение цены
        price = dict.get('UnitPriceSilver', dict.get('UnitPrice', 0))
        if price == 0:
            price = dict.get('BuyPrice', dict.get('SellPrice', 0))
        if price == 0:
            price = dict.get('price', 0)

        quantity = dict.get('Amount', dict.get('Quantity', 0))
        if quantity == 0:
            quantity = dict.get('quantity', 0)

        timestamp = convert_ticks_to_datetime(dict.get('Timestamp', dict.get('timestamp', 0)))

        # Отладка
        print(f"\n💡 {item_id} @ {location_id} | price={price}, qty={quantity}")

        # Проверки
        if not item_id:
            return

        if location_id == 0:
            return

        if price == 0:
            print(f"⚠️  {item_id} - price=0")
            return

        print(f"💾 {item_id} @ {location_id} | {order_type}: {price}")

        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Добавляем предмет
        cur.execute("SELECT 1 FROM items WHERE item_id = %s", (item_id,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO items (item_id, name, category, tier, weight)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (item_id) DO NOTHING
            """, (item_id, item_id, 'Unknown', 0, 1.0))

        # Добавляем локацию
        cur.execute("SELECT 1 FROM locations WHERE id = %s", (location_id,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO locations (id, name, region, is_black_zone, tax_rate)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (location_id, f'Location_{location_id}', 'Unknown', False, 4.00))
            conn.commit()

        # Сохраняем ордер
        cur.execute("""
            INSERT INTO market_orders 
            (item_id, location_id, order_type, price, quantity, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (item_id, location_id, order_type) 
            DO UPDATE SET 
                price = EXCLUDED.price,
                quantity = EXCLUDED.quantity,
                timestamp = EXCLUDED.timestamp
        """, (item_id, location_id, order_type, price, quantity, timestamp))

        conn.commit()
        print(f"✅ {item_id} @ {location_id} | {price:,}")

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


async def message_handler(msg):
    """Обработчик сообщений"""
    try:
        data = json.loads(msg.data.decode())

        # Определяем тип ордера
        default_order_type = 'sell'
        if 'buy' in msg.subject.lower():
            default_order_type = 'buy'
        elif 'sell' in msg.subject.lower():
            default_order_type = 'sell'

        if isinstance(data, list):
            for order in data:
                await save_market_order(order, default_order_type)
        else:
            await save_market_order(data, default_order_type)

    except Exception as e:
        print(f"❌ Message error: {e}")
        traceback.print_exc()


async def main():
    print("=" * 60)
    print("🚀 ALBION MARKET DATA CONSUMER")
    print("=" * 60)

    nc = NATS()

    try:
        await nc.connect(NATS_URL)
        print("✅ Connected to NATS")

        await nc.subscribe("marketorders.deduped", cb=message_handler)
        print("✓ marketorders.deduped")

        await nc.subscribe("markethistories.deduped", cb=message_handler)
        print("✓ markethistories.deduped")

        print("\n🟢 Waiting for data...\n")

        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n⛔ Stopping...")
        await nc.close()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        await nc.close()


if __name__ == "__main__":
    asyncio.run(main())