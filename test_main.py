"""
Unit and Integration Tests for Albion Profit Calculator
=======================================================
Запуск: pytest test_main.py -v
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Добавляем текущую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (
    app,
    calculate_profit,
    build_icon_url,
    get_item_meta,
    load_items_catalog,
    CITY_MAP,
    ALBION_LOCATIONS
)
from fastapi.testclient import TestClient


class TestCalculateProfit(unittest.TestCase):
    """Тесты функции calculate_profit - расчёт прибыли с налогом"""

    def test_basic_profit_calculation(self):
        """Тест базового расчёта: покупка 1000 серебра, продажа 1500"""
        result = calculate_profit(1000, 1500, tax_rate=6.5)

        self.assertEqual(result['gross_profit'], 500)  # 1500 - 1000
        self.assertEqual(result['tax'], 97)  # 1500 * 0.065 = 97.5 -> int(97)
        self.assertEqual(result['net_profit'], 402)  # (1500 * 0.935) - 1000 = 402.5 -> int(402)
        self.assertAlmostEqual(result['roi_percent'], 40.25, places=0)

    def test_no_profit_scenario(self):
        """Тест при покупке и продаже по одной цене"""
        result = calculate_profit(1000, 1000, tax_rate=6.5)

        self.assertEqual(result['gross_profit'], 0)
        self.assertEqual(result['net_profit'], -65)  # Только налог
        self.assertLess(result['roi_percent'], 0)

    def test_loss_scenario(self):
        """Тест убыточной сделки: покупка 1500, продажа 1000"""
        result = calculate_profit(1500, 1000, tax_rate=6.5)

        self.assertEqual(result['gross_profit'], -500)
        self.assertLess(result['net_profit'], -500)
        self.assertLess(result['roi_percent'], 0)

    def test_zero_buy_price(self):
        """Тест при цене покупки = 0 (ROI должен быть 0)"""
        result = calculate_profit(0, 100, tax_rate=6.5)

        self.assertEqual(result['roi_percent'], 0)  # Деление на 0 защищено

    def test_custom_tax_rate(self):
        """Тест с нестандартным налогом (3%)"""
        result = calculate_profit(1000, 1100, tax_rate=3.0)

        expected_net = (1100 * 0.97) - 1000  # 1067 - 1000 = 67
        self.assertAlmostEqual(result['net_profit'], expected_net, places=0)

    def test_zero_tax_rate(self):
        """Тест без налога"""
        result = calculate_profit(1000, 1500, tax_rate=0)

        self.assertEqual(result['tax'], 0)
        self.assertEqual(result['net_profit'], 500)  # Чистая прибыль = валовой прибыли

    def test_high_tax_rate(self):
        """Тест с высоким налогом (20%)"""
        result = calculate_profit(1000, 1100, tax_rate=20.0)

        self.assertEqual(result['tax'], 220)  # 1100 * 0.20
        self.assertLess(result['net_profit'], 0)  # Убыток из-за налога

    def test_large_numbers(self):
        """Тест с большими числами (1 млн серебра)"""
        result = calculate_profit(1000000, 1500000, tax_rate=6.5)

        self.assertEqual(result['gross_profit'], 500000)
        self.assertAlmostEqual(result['roi_percent'], 40.25, places=0)

    def test_return_types(self):
        """Тест типов возвращаемых значений"""
        result = calculate_profit(1000, 1500)

        self.assertIsInstance(result, dict)
        self.assertIsInstance(result['gross_profit'], int)
        self.assertIsInstance(result['tax'], int)
        self.assertIsInstance(result['net_profit'], int)
        self.assertIsInstance(result['roi_percent'], float)


class TestBuildIconUrl(unittest.TestCase):
    """Тесты функции build_icon_url - генерация URL иконок предметов"""

    def test_basic_icon_url(self):
        """Тест генерации базового URL иконки"""
        url = build_icon_url("T4_ARMOR_CLOTH")

        self.assertIn("render.albiononline.com", url)
        self.assertIn("T4_ARMOR_CLOTH", url)
        self.assertIn("size=64", url)

    def test_url_format(self):
        """Проверка формата URL"""
        url = build_icon_url("T4_BAG")
        expected = "https://render.albiononline.com/v1/item/T4_BAG.png?size=64"

        self.assertEqual(url, expected)

    def test_special_characters_in_id(self):
        """Тест с ID содержащим спецсимволы"""
        url = build_icon_url("T4_ARMOR_CLOTH_SET")

        self.assertIsInstance(url, str)
        self.assertTrue(url.startswith("https://"))

    def test_empty_item_id(self):
        """Тест с пустой строкой item_id"""
        url = build_icon_url("")

        self.assertIn("render.albiononline.com", url)


class TestCityMap(unittest.TestCase):
    """Тесты константы CITY_MAP - соответствие городов и ID"""

    def test_all_locations_in_map(self):
        """Проверка что все города из ALBION_LOCATIONS есть в CITY_MAP"""
        locations = ALBION_LOCATIONS.split(",")

        for city in locations:
            self.assertIn(city, CITY_MAP, f"Город {city} отсутствует в CITY_MAP")

    def test_city_ids_are_integers(self):
        """Проверка что ID городов - целые числа"""
        for city, city_id in CITY_MAP.items():
            self.assertIsInstance(city_id, int)
            self.assertGreater(city_id, 0)

    def test_unique_city_ids(self):
        """Проверка что все ID городов уникальны"""
        ids = list(CITY_MAP.values())
        self.assertEqual(len(ids), len(set(ids)))


class TestGetItemMeta(unittest.TestCase):
    """Тесты функции get_item_meta - получение метаданных предмета"""

    @patch('main.load_items_catalog')
    def test_existing_item(self, mock_load):
        """Тест получения метаданных существующего предмета"""
        mock_load.return_value = {
            "T4_BAG": {
                "name_ru": "Сумка адепта",
                "name_en": "Journeyman's Bag",
                "icon_url": "https://example.com/icon.png"
            }
        }

        meta = get_item_meta("T4_BAG")

        self.assertEqual(meta["name_ru"], "Сумка адепта")
        self.assertEqual(meta["name_en"], "Journeyman's Bag")
        self.assertIn("icon_url", meta)

    @patch('main.load_items_catalog')
    def test_nonexistent_item_fallback(self, mock_load):
        """Тест что несуществующий предмет получит item_id как имя"""
        mock_load.return_value = {}

        meta = get_item_meta("UNKNOWN_ITEM")

        self.assertEqual(meta["name_ru"], "UNKNOWN_ITEM")
        self.assertEqual(meta["name_en"], "UNKNOWN_ITEM")
        self.assertIn("icon_url", meta)

    @patch('main.load_items_catalog')
    def test_meta_structure(self, mock_load):
        """Тест что мета всегда содержит требуемые ключи"""
        mock_load.return_value = {"T4_BAG": {
            "name_ru": "Сумка",
            "name_en": "Bag",
            "icon_url": "url"
        }}

        meta = get_item_meta("T4_BAG")

        required_keys = {"name_ru", "name_en", "icon_url"}
        self.assertTrue(required_keys.issubset(set(meta.keys())))


class TestLoadItemsCatalog(unittest.TestCase):
    """Тесты функции load_items_catalog - загрузка каталога предметов"""

    @patch('main.requests.get')
    def test_catalog_loading_success(self, mock_get):
        """Тест успешной загрузки каталога с внешнего источника"""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "UniqueName": "T4_BAG",
                "LocalizedNames": {"RU-RU": "Сумка адепта", "EN-US": "Journeyman's Bag"}
            },
            {
                "UniqueName": "T4_ARMOR_CLOTH",
                "LocalizedNames": {"EN-US": "Cloth Armor"}
            }
        ]
        mock_get.return_value = mock_response

        load_items_catalog.cache_clear()
        catalog = load_items_catalog()

        self.assertIn("T4_BAG", catalog)
        self.assertEqual(catalog["T4_BAG"]["name_ru"], "Сумка адепта")
        self.assertIn("icon_url", catalog["T4_BAG"])

    @patch('main.os.path.exists')
    @patch('main.requests.get')
    def test_catalog_fallback_to_local(self, mock_get, mock_exists):
        """Тест фолбэка на локальный файл при ошибке API"""
        mock_get.side_effect = Exception("API Timeout")
        mock_exists.return_value = False

        load_items_catalog.cache_clear()
        catalog = load_items_catalog()

        self.assertIsInstance(catalog, dict)


class TestAlbionLocationsConstant(unittest.TestCase):
    """Тесты константы ALBION_LOCATIONS"""

    def test_locations_not_empty(self):
        """Проверка что список локаций не пуст"""
        self.assertTrue(ALBION_LOCATIONS)
        self.assertIsInstance(ALBION_LOCATIONS, str)

    def test_locations_comma_separated(self):
        """Проверка что локации разделены запятыми"""
        locations = ALBION_LOCATIONS.split(",")

        self.assertGreater(len(locations), 0)
        for loc in locations:
            self.assertTrue(loc.strip())


class TestEdgeCases(unittest.TestCase):
    """Тесты граничных случаев и обработки ошибок"""

    def test_negative_prices(self):
        """Тест с отрицательными ценами"""
        result = calculate_profit(-1000, 500, tax_rate=6.5)
        self.assertIsInstance(result, dict)

    def test_very_small_prices(self):
        """Тест с очень маленькими ценами (1 серебро)"""
        result = calculate_profit(1, 2, tax_rate=6.5)
        self.assertIsInstance(result, dict)
        self.assertGreaterEqual(result['roi_percent'], 0)

    def test_float_inputs_converted_to_int(self):
        """Тест что функция работает с float входными значениями"""
        result = calculate_profit(1000.5, 1500.7, tax_rate=6.5)
        self.assertIsInstance(result['gross_profit'], int)
        self.assertIsInstance(result['net_profit'], int)


class TestApiEndpoints(unittest.TestCase):
    """Интеграционные тесты API через FastAPI TestClient"""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        """Тест корневого URL /"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_docs_endpoint(self):
        """Тест документации Swagger /docs"""
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)

    def test_health_endpoint(self):
        """Тест эндпоинта проверки работоспособности /api/health"""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ok")

    def test_locations_endpoint(self):
        """Тест API эндпоинта /api/locations"""
        response = self.client.get("/api/locations")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("locations", data)
        self.assertGreater(len(data["locations"]), 0)

    def test_scan_progress_endpoint(self):
        """Тест API эндпоинта /api/scan-progress"""
        response = self.client.get("/api/scan-progress")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("running", data)
        self.assertIn("processed", data)
        self.assertIn("total", data)

    def test_items_catalog_endpoint(self):
        """Тест API эндпоинта /api/items-catalog"""
        response = self.client.get("/api/items-catalog", params={"limit": 10})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("count", data)
        self.assertIn("items", data)


class TestDatabaseInit(unittest.TestCase):
    """Тест модуля инициализации БД без контейнеров"""

    def test_database_init_module(self):
        from init_db import init_database
        # Вызов init_database должен завершиться успешно (подключиться к существующей или создать)
        init_database(auto_create=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
