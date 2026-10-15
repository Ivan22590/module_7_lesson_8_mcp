"""
Модуль управления базой данных SQLite для MCP сервера.

Отвечает за инициализацию таблицы products, заполнение тестовыми данными
и выполнение CRUD-операций.
"""

import sqlite3
import os

# Путь к файлу базы данных
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "products.db")

# Тестовые данные для начального заполнения (100 товаров)
TEST_PRODUCTS = [
    ("iPhone 15 Pro", "Смартфоны", 99990),
    ("Samsung Galaxy S24", "Смартфоны", 89990),
    ("Xiaomi Redmi Note 13", "Смартфоны", 24990),
    ("MacBook Air M3", "Ноутбуки", 129990),
    ("ASUS ROG Strix", "Ноутбуки", 159990),
    ("Lenovo ThinkPad X1", "Ноутбуки", 145000),
    ("Sony WH-1000XM5", "Наушники", 29990),
    ("AirPods Pro 2", "Наушники", 24990),
    ("JBL Charge 5", "Наушники", 14990),
    ("iPad Air M2", "Планшеты", 74990),
    ("Samsung Galaxy Tab S9", "Планшеты", 64990),
    ("Xiaomi Pad 6", "Планшеты", 29990),
    ("PlayStation 5", "Игровые консоли", 54990),
    ("Xbox Series X", "Игровые консоли", 49990),
    ("Nintendo Switch OLED", "Игровые консоли", 34990),
    ("Samsung QLED 55\"", "Телевизоры", 79990),
    ("LG OLED 65\"", "Телевизоры", 149990),
    ("TCL 50\"", "Телевизоры", 34990),
    ("Dyson V15", "Пылесосы", 59990),
    ("Roomba j7+", "Пылесосы", 49990),
    ("Xiaomi Robot Vacuum", "Пылесосы", 24990),
    ("Кофе в зёрнах Lavazza", "Продукты", 1290),
    ("Чай Greenfield Earl Grey", "Продукты", 290),
    ("Шоколад Ritter Sport", "Продукты", 190),
    ("Мёд алтайский 1кг", "Продукты", 890),
    ("Кофе Nescafe Gold", "Продукты", 790),
    ("Чай Bahja Gold", "Продукты", 490),
    ("Яблоки Голден 1кг", "Продукты", 180),
    ("Бананы Эквадор 1кг", "Продукты", 120),
    ("Вино красное Dry", "Напитки", 890),
    ("Сок Rich Яблочный", "Напитки", 140),
    ("Вода BonAqua 1.5л", "Напитки", 79),
    ("Кола 2л", "Напитки", 110),
    ("Энергетик Red Bull", "Напитки", 240),
    ("Чайник Bosch", "Бытовая техника", 4990),
    ("Микроволновка Samsung", "Бытовая техника", 7990),
    ("Стиральная машина LG", "Бытовая техника", 34990),
    ("Холодильник Bosch", "Бытовая техника", 49990),
    ("Тостер Philips", "Бытовая техника", 3490),
    ("Утюг Philips", "Бытовая техника", 2990),
    ("Фен Dyson", "Бытовая техника", 39990),
    ("Монитор Dell 27\"", "Компьютеры", 24990),
    ("Клавиатура Logitech", "Компьютеры", 4990),
    ("Мышь Logitech MX", "Компьютеры", 6990),
    ("SSD Samsung 1TB", "Компьютеры", 7990),
    ("Оперативная память 16GB", "Компьютеры", 4490),
    ("Видеокарта RTX 4070", "Компьютеры", 54990),
    ("Процессор Intel i7", "Компьютеры", 32990),
    ("Материнская плата ASUS", "Компьютеры", 18990),
    ("Корпус DeepCool", "Компьютеры", 5990),
    ("Блок питания 750W", "Компьютеры", 7490),
    ("Рубашка мужская", "Одежда", 2990),
    ("Джинсы Levi's", "Одежда", 6990),
    ("Куртка зимняя", "Одежда", 9990),
    ("Кроссовки Nike", "Одежда", 8990),
    ("Футболка Adidas", "Одежда", 2490),
    ("Пальто женское", "Одежда", 12990),
    ("Свитер кашемировый", "Одежда", 5990),
    ("Шапка зимняя", "Одежда", 1490),
    ("Сумка кожаная", "Аксессуары", 7990),
    ("Часы Casio", "Аксессуары", 4990),
    ("Очки Ray-Ban", "Аксессуары", 9990),
    ("Ремень Gucci", "Аксессуары", 14990),
    ("Кошелек мужской", "Аксессуары", 2490),
    ("Блокнот Moleskine", "Канцелярия", 1490),
    ("Ручка Parker", "Канцелярия", 3990),
    ("Набор маркеров", "Канцелярия", 990),
    ("Фломастеры 50 шт", "Канцелярия", 790),
    ("Файлы для документов", "Канцелярия", 290),
    ("Калькулятор инженерный", "Канцелярия", 890),
    ("Рюкзак городской", "Аксессуары", 3990),
    ("Портмоне женское", "Аксессуары", 4990),
    ("Браслет титановый", "Аксессуары", 2990),
    ("Кольцо серебряное", "Аксессуары", 3490),
    ("Наушники JBL Tune", "Наушники", 4990),
    ("Колонка JBL Flip", "Наушники", 7990),
    ("Веб-камера Logitech", "Компьютеры", 4990),
    ("Микрофон Blue Yeti", "Компьютеры", 9990),
    ("USB-хаб 7 портов", "Компьютеры", 1990),
    ("Мышка беспроводная", "Компьютеры", 1490),
    ("Тачпад внешний", "Компьютеры", 3990),
    ("Web-камера 4K", "Компьютеры", 12990),
    ("Монитор 4K 32\"", "Компьютеры", 44990),
    ("Ноутбук HP Pavilion", "Ноутбуки", 64990),
    ("Ноутбук Acer Aspire", "Ноутбуки", 49990),
    ("Планшет Samsung A9", "Планшеты", 34990),
    ("Книга 'Чистый код'", "Книги", 890),
    ("Книга 'Грокаем алгоритмы'", "Книги", 790),
    ("Книга 'Думай медленно'", "Книги", 990),
    ("Книга 'Атомные привычки'", "Книги", 690),
    ("Книга 'Сила воли'", "Книги", 590),
    ("Батарея AA Duracell", "Электроника", 290),
    ("Батарея AAA Energizer", "Электроника", 240),
    ("Удлинитель 5м", "Электроника", 890),
    ("Переходник USB-C", "Электроника", 390),
    ("Кабель HDMI 2м", "Электроника", 490),
    ("Кабель Lightning", "Электроника", 690),
    ("Powerbank 20000mAh", "Электроника", 2990),
    ("Зарядка беспроводная", "Электроника", 1990),
    ("Коврик для мыши", "Компьютеры", 590),
    ("Подставка для ноутбука", "Компьютеры", 2490),
]


def get_connection() -> sqlite3.Connection:
    """
    Создаёт и возвращает подключение к базе данных.

    Returns:
        sqlite3.Connection: Объект подключения к SQLite.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Инициализирует базу данных: создаёт таблицу products и заполняет
    её тестовыми данными, если таблица пуста.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Создаём таблицу
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL
            )
        """)

        # Проверяем, есть ли уже данные
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]

        if count == 0:
            # Заполняем тестовыми данными
            cursor.executemany(
                "INSERT INTO products (name, category, price) VALUES (?, ?, ?)",
                TEST_PRODUCTS
            )
            conn.commit()
            print(f"[DB] База данных инициализирована: {len(TEST_PRODUCTS)} товаров загружено.")
        else:
            print(f"[DB] База данных уже содержит {count} товаров.")
    finally:
        conn.close()


def list_products() -> list[dict]:
    """
    Возвращает список всех товаров из базы данных.

    Returns:
        list[dict]: Список словарей с информацией о товарах.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, price FROM products")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def find_product(name: str) -> list[dict]:
    """
    Ищет товары по совпадению имени (нечувствительно к регистру).

    Args:
        name: Подстрока для поиска по названию товара.

    Returns:
        list[dict]: Список найденных товаров.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, category, price FROM products WHERE name LIKE ? COLLATE NOCASE",
            (f"%{name}%",)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def add_product(name: str, category: str, price: float) -> dict:
    """
    Добавляет новый товар в базу данных.

    Args:
        name: Название товара.
        category: Категория товара.
        price: Цена товара.

    Returns:
        dict: Информация о добавленном товаре с присвоенным ID.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, category, price) VALUES (?, ?, ?)",
            (name, category, price)
        )
        conn.commit()
        return {
            "id": cursor.lastrowid,
            "name": name,
            "category": category,
            "price": price
        }
    finally:
        conn.close()
