"""
MCP Server «tools-mcp» — основной файл запуска сервера инструментов.

Сервер реализует Model Context Protocol (MCP) и предоставляет
инструменты для аудита сайтов, поиска, погоды, курсов валют,
криптовалют, генерации QR-кодов и работы с базой данных товаров.

Запуск:
    python server.py

Сервер запускается на порту 8000 с SSE-транспортом.
SSE endpoint для подключения клиентов: http://localhost:8000/sse
"""

from mcp.server.fastmcp import FastMCP

from db import init_db
from tools import (
    check_site,
    web_search_tool,
    get_weather_tool,
    get_crypto_price_tool,
    get_fiat_rate_tool,
    generate_qr_code_tool,
    list_products_tool,
    find_product_tool,
    add_product_tool,
    calculate_tool,
)

# Создаём MCP сервер
mcp = FastMCP(
    "tools-mcp",
    host="0.0.0.0",
    port=8000,
)

# ===================== ИНСТРУМЕНТЫ =====================


@mcp.tool()
def check_site_tool(url: str) -> str:
    """Аудит сайта по URL: скорость, вес страницы, HTTPS, мобильная версия,
    заголовок и оффер, Яндекс.Метрика, формы/телефоны/мессенджеры,
    интегральная общая оценка качества сайта (N/100) и рекомендации,
    с чего начать.

    Args:
        url: Полный URL сайта, например https://example.com
    """
    return check_site(url)


@mcp.tool()
def web_search(query: str) -> str:
    """Поиск актуальной информации через DuckDuckGo.
    Возвращает до 5 результатов с заголовками, описаниями и ссылками.

    Args:
        query: Поисковый запрос на русском или английском языке
    """
    return web_search_tool(query)


@mcp.tool()
def get_weather(city: str) -> str:
    """Погода по названию города (геокодинг + Open-Meteo):
    температура (°C), скорость ветра (км/ч), описание погоды.

    Args:
        city: Название города, например Москва или London
    """
    return get_weather_tool(city)


@mcp.tool()
def get_crypto_price(crypto: str) -> str:
    """Курс криптовалюты через CoinGecko. Возвращает цену в USD
    и изменение за 24 часа.

    Args:
        crypto: Идентификатор криптовалюты: bitcoin, ethereum, toncoin, solana и т.д.
    """
    return get_crypto_price_tool(crypto)


@mcp.tool()
def get_fiat_rate(currency: str = "USD") -> str:
    """Курсы фиатных валют (USD → EUR, RUB, GEL) в обоих направлениях.

    Args:
        currency: Код базовой валюты (по умолчанию USD)
    """
    return get_fiat_rate_tool(currency)


@mcp.tool()
def generate_qr_code(data: str) -> str:
    """Генерация QR-кода из текста или URL.
    Возвращает base64-encoded PNG изображение QR-кода,
    которое бот отправляет пользователю как фотографию.

    Args:
        data: Данные для кодирования (URL, текст, телефон)
    """
    return generate_qr_code_tool(data)


@mcp.tool()
def list_products() -> str:
    """Возвращает список всех товаров из базы данных SQLite.

    Используется для запросов вида «покажи все товары».
    """
    return list_products_tool()


@mcp.tool()
def find_product(name: str) -> str:
    """Возвращает товары по совпадению имени из базы данных.
    Поиск нечувствителен к регистру.

    Args:
        name: Подстрока названия товара, например «чай» или «iphone»
    """
    return find_product_tool(name)


@mcp.tool()
def add_product(name: str, category: str, price: float) -> str:
    """Добавляет новый товар в базу данных.

    Args:
        name: Название товара, например «Яблоки»
        category: Категория товара, например «Фрукт»
        price: Цена товара в рублях, например 120.0
    """
    return add_product_tool(name, category, price)


@mcp.tool()
def calculate(expression: str) -> str:
    """Безопасный калькулятор математических выражений.
    Поддерживает: +, -, *, /, //, %, **, abs, round, min, max, sum,
    sqrt, floor, ceil, pi, e, tau. Eval запрещён — используется AST.

    Args:
        expression: Математическое выражение, например "2 + 2 * 3" или "sqrt(144)"
    """
    return calculate_tool(expression)


# ===================== ЗАПУСК =====================

if __name__ == "__main__":
    # Инициализируем базу данных (создаёт products.db и заполняет 100 товарами)
    init_db()

    # Отключаем шумные предупреждения verify=False в check_site
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Запускаем сервер
    print("=" * 60)
    print("  MCP Server «tools-mcp» запускается...")
    print("  SSE endpoint: http://localhost:8000/sse")
    print("=" * 60)

    # SSE-транспорт: клиенты подключаются по HTTP
    mcp.run(transport="sse")
