"""
Реализация инструментов (tools) для MCP сервера.

Каждая функция — это отдельный инструмент, который будет доступен
через MCP протокол.
"""

import time
import re
import math
import base64
import io

import requests
import qrcode

from db import list_products, find_product, add_product


def _safe_calculate(expression: str) -> str:
    """
    Безопасное вычисление математического выражения с использованием AST.

    Использует только доверенные математические функции и запрещает
    выполнение произвольного кода.

    Args:
        expression: Математическое выражение (например, "2 + 2 * 3").

    Returns:
        str: Результат вычисления в виде строки.

    Raises:
        ValueError: Если выражение содержит недопустимые операции.
    """
    import ast

    # Разрешённые имена для AST
    ALLOWED_NAMES = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "pow": pow, "sqrt": math.sqrt,
        "floor": math.floor, "ceil": math.ceil,
        "pi": math.pi, "e": math.e, "tau": math.tau,
    }

    try:
        tree = ast.parse(expression, mode="eval")

        def _eval_node(node):
            """Рекурсивно вычисляет узел AST."""
            if isinstance(node, ast.Expression):
                return _eval_node(node.body)
            elif isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError(f"Неподдерживаемый тип константы: {type(node.value)}")
            elif isinstance(node, ast.UnaryOp):
                operand = _eval_node(node.operand)
                if isinstance(node.op, ast.USub):
                    return -operand
                elif isinstance(node.op, ast.UAdd):
                    return operand
                elif isinstance(node.op, ast.Invert):
                    return ~operand
                raise ValueError(f"Неподдерживаемый унарный оператор: {type(node.op)}")
            elif isinstance(node, ast.BinOp):
                left = _eval_node(node.left)
                right = _eval_node(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                elif isinstance(node.op, ast.Sub):
                    return left - right
                elif isinstance(node.op, ast.Mult):
                    return left * right
                elif isinstance(node.op, ast.Div):
                    if right == 0:
                        raise ValueError("Деление на ноль")
                    return left / right
                elif isinstance(node.op, ast.FloorDiv):
                    if right == 0:
                        raise ValueError("Деление на ноль")
                    return left // right
                elif isinstance(node.op, ast.Mod):
                    if right == 0:
                        raise ValueError("Деление на ноль")
                    return left % right
                elif isinstance(node.op, ast.Pow):
                    return left ** right
                raise ValueError(f"Неподдерживаемый бинарный оператор: {type(node.op)}")
            elif isinstance(node, ast.Call):
                func_name = node.func.id if isinstance(node.func, ast.Name) else None
                if func_name not in ALLOWED_NAMES:
                    raise ValueError(f"Недопустимая функция: {func_name}")
                args = [_eval_node(a) for a in node.args]
                return ALLOWED_NAMES[func_name](*args)
            elif isinstance(node, ast.Name):
                if node.id not in ALLOWED_NAMES:
                    raise ValueError(f"Недопустимое имя: {node.id}")
                return ALLOWED_NAMES[node.id]
            else:
                raise ValueError(f"Неподдерживаемая конструкция: {type(node).__name__}")

        result = _eval_node(tree)
        # Форматируем результат
        if isinstance(result, float):
            if result.is_integer():
                return str(int(result))
            return f"{result:.4f}".rstrip("0").rstrip(".")
        return str(result)

    except SyntaxError as e:
        return f"Ошибка синтаксиса: {e}"
    except ValueError as e:
        return f"Ошибка: {e}"
    except Exception as e:
        return f"Ошибка вычисления: {e}"


def check_site(url: str) -> str:
    """
    Проводит аудит сайта по URL и возвращает детальную оценку качества.

    Проверяет: скорость загрузки, вес страницы, HTTPS, мобильную версию,
    заголовок и оффер, Яндекс.Метрику, формы/контакты, и выдаёт
    интегральную оценку N/100 с рекомендациями.

    Args:
        url: URL сайта для аудита (например, https://example.com).

    Returns:
        str: Детальный отчёт аудита в формате Markdown.
    """
    score = 0
    checks = []
    recommendations = []

    # 1. Проверка HTTPS
    is_https = url.startswith("https://")
    if is_https:
        score += 15
        checks.append("✅ HTTPS: Используется защищённое соединение")
    else:
        checks.append("❌ HTTPS: Сайт не использует HTTPS")
        recommendations.append("Обязательно настройте SSL-сертификат (HTTPS)")

    # 2. Загрузка и анализ страницы
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        load_time = time.time() - start_time
        page_size = len(response.content)

        # Скорость
        if load_time < 2:
            score += 15
            checks.append(f"✅ Скорость: {load_time:.2f}с — Отлично")
        elif load_time < 5:
            score += 10
            checks.append(f"⚠️ Скорость: {load_time:.2f}с — Удовлетворительно")
        else:
            checks.append(f"❌ Скорость: {load_time:.2f}с — Медленно")
            recommendations.append("Ускорьте загрузку сайта: оптимизируйте изображения, используйте CDN")

        # Вес страницы
        size_mb = page_size / 1024 / 1024
        if size_mb < 1:
            score += 10
            checks.append(f"✅ Вес страницы: {size_mb:.2f} МБ — Отлично")
        elif size_mb < 3:
            score += 5
            checks.append(f"⚠️ Вес страницы: {size_mb:.2f} МБ — Можно лучше")
        else:
            checks.append(f"❌ Вес страницы: {size_mb:.2f} МБ — Слишком тяжело")
            recommendations.append("Сократите вес страницы: сожмите изображения и скрипты")

        # 3. Заголовок и оффер
        soup = response.text
        title_match = re.search(r"<title>(.*?)</title>", soup, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "Не найден"

        if len(title) > 10 and len(title) < 70:
            score += 10
            checks.append(f'✅ Заголовок (title): "{title}" — Оптимальная длина')
        else:
            checks.append(f'⚠️ Заголовок (title): "{title}" — Неоптимальная длина')
            recommendations.append("Настройте SEO-заголовок: 10-70 символов, отражайте суть страницы")

        # Поиск оффера (ключевые слова)
        offer_keywords = ["скидка", "бесплатно", "акция", "купить", "заказать", "предложение"]
        body_text = soup.lower()
        has_offer = any(kw in body_text for kw in offer_keywords)
        if has_offer:
            score += 10
            checks.append("✅ Оффер: Найден призыв к действию / предложение")
        else:
            checks.append("⚠️ Оффер: Не найден явный призыв к действию")
            recommendations.append("Добавьте чёткий оффер: призыв к действию, выгодное предложение")

        # 4. Мобильная версия
        has_viewport = 'viewport' in soup
        if has_viewport:
            score += 15
            checks.append("✅ Мобильная версия: Meta viewport найден")
        else:
            checks.append("❌ Мобильная версия: Meta viewport не найден")
            recommendations.append("Добавьте meta viewport для адаптивной вёрстки")

        # 5. Яндекс.Метрика
        has_metrika = "mc.yandex" in soup or "metrika" in soup.lower()
        if has_metrika:
            score += 10
            checks.append("✅ Яндекс.Метрика: Код аналитики найден")
        else:
            checks.append("⚠️ Яндекс.Метрика: Код не найден")
            recommendations.append("Установите Яндекс.Метрику для отслеживания посетителей")

        # 6. Формы / телефоны / мессенджеры
        phones = re.findall(r"\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}", soup)
        has_phone = len(phones) > 0
        if has_phone:
            score += 10
            checks.append(f"✅ Телефон: {len(phones)} номер(ов) найдено")
        else:
            checks.append("❌ Телефон: Контактный номер не найден")
            recommendations.append("Добавьте номер телефона на сайт")

        has_email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", soup)
        if has_email:
            score += 5
            checks.append("✅ Email: Контактная почта найдена")
        else:
            checks.append("⚠️ Email: Контактная почта не найдена")

        has_form = re.search(r"<form", soup, re.IGNORECASE)
        has_telegram = "t.me/" in soup or "telegram" in soup.lower()
        has_whatsapp = "wa.me/" in soup or "whatsapp" in soup.lower()

        contact_score = 0
        if has_form:
            contact_score += 5
            checks.append("✅ Форма: Форма обратной связи найдена")
        if has_telegram:
            contact_score += 5
            checks.append("✅ Мессенджер: Telegram найден")
        if has_whatsapp:
            contact_score += 5
            checks.append("✅ Мессенджер: WhatsApp найден")

        if contact_score == 0:
            checks.append("❌ Контакты: Формы и мессенджеры не найдены")
            recommendations.append("Добавьте формы обратной связи и кнопки мессенджеров")

    except requests.exceptions.RequestException as e:
        return f"❌ Ошибка при загрузке сайта: {e}\n\nПроверьте URL и попробуйте снова."

    return (
        f"🔍 **Аудит сайта: `{url}`**\n\n"
        f"📊 **Итоговая оценка: {score}/100**\n\n"
        f"---\n\n"
        f"📋 **Результаты проверок:**\n\n" +
        "\n".join(f"  {c}" for c in checks) +
        f"\n\n---\n\n"
        f"💡 **Рекомендации:**\n\n" +
        "\n".join(f"  {i+1}. {r}" for i, r in enumerate(recommendations)) +
        f"\n\n---\n\n"
        f"🎯 **С чего начать:**\n\n" +
        f"  1. {'Настройте HTTPS' if not is_https else 'Оптимизируйте скорость загрузки'}\n" +
        f"  2. {'Добавьте контактные данные' if not has_phone else 'Добавьте мессенджеры'}\n" +
        f"  3. {'Установите Яндекс.Метрику' if not has_metrika else 'Добавьте чёткий оффер'}\n"
    )


def web_search_tool(query: str) -> str:
    """
    Выполняет поиск в интернете через DuckDuckGo.

    Args:
        query: Поисковый запрос на русском или английском языке.

    Returns:
        str: Отформатированные результаты поиска (до 5 ссылок с описаниями).
    """
    from duckduckgo_search import DDGS

    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "❌ Результаты поиска не найдены."

        formatted = f"🔍 **Результаты поиска по запросу: \"{query}\"\n\n"
        for i, r in enumerate(results, 1):
            formatted += f"**{i}. {r.get('title', 'Без заголовка')}**\n"
            formatted += f"   {r.get('body', 'Нет описания')}\n"
            formatted += f"   🔗 {r.get('href', '#')}\n\n"

        return formatted.rstrip()
    except Exception as e:
        return f"❌ Ошибка при поиске: {e}"


def get_weather_tool(city: str) -> str:
    """
    Получает текущую погоду для указанного города через Open-Meteo API.

    Выполняет геокодирование города, затем получает данные о погоде:
    температуру, скорость ветра и код погоды.

    Args:
        city: Название города на русском или английском языке.

    Returns:
        str: Текущая погода в формате: температура, ветер, описание.
    """
    try:
        # Геокодирование города
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=ru"
        geo_resp = requests.get(geo_url, timeout=5)
        geo_data = geo_resp.json()

        if "error" in geo_data or not geo_data.get("results"):
            return f"❌ Город \"{city}\" не найден. Проверьте название."

        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        city_name = location["name"]

        # Получаем погоду
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,wind_speed_10m,weather_code"
            f"&timezone=auto"
        )
        weather_resp = requests.get(weather_url, timeout=5)
        weather_data = weather_resp.json()

        current = weather_data["current"]
        temp = current["temperature_2m"]
        wind = current["wind_speed_10m"]
        code = current["weather_code"]

        # Расшифровка кода погоды (WMO)
        weather_codes = {
            0: "☀️ Ясно", 1: "🌤️ Преимущественно ясно", 2: "⛅ Переменная облачность",
            3: "☁️ Пасмурно", 45: "🌫️ Туман", 48: "🌫️ Иней",
            51: "🌦️ Морось", 53: "🌧️ Морось", 55: "🌧️ Сильная морось",
            61: "🌧️ Небольшой дождь", 63: "🌧️ Дождь", 65: "🌧️ Сильный дождь",
            71: "🌨️ Небольшой снег", 73: "🌨️ Снег", 75: "🌨️ Сильный снег",
            80: "🌦️ Ливень", 81: "🌧️ Сильный ливень", 82: "🌧️ Очень сильный ливень",
            95: "⛈️ Гроза", 96: "⛈️ Гроза с градом", 99: "⛈️ Сильная гроза с градом",
        }
        weather_desc = weather_codes.get(code, f"🌡️ Код погоды: {code}")

        return (
            f"🌤️ **Погода в {city_name}**\n\n"
            f"🌡️ Температура: {temp}°C\n"
            f"💨 Скорость ветра: {wind} км/ч\n"
            f"{weather_desc}"
        )
    except Exception as e:
        return f"❌ Ошибка при получении погоды: {e}"


def get_crypto_price_tool(crypto: str) -> str:
    """
    Получает текущую цену криптовалюты через CoinGecko API.

    Args:
        crypto: Идентификатор или название криптовалюты
                (например, 'bitcoin', 'ethereum', 'toncoin').

    Returns:
        str: Текущая цена в USD с информацией о изменении за 24 часа.
    """
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "error" in data:
            return f"❌ Ошибка: {data['error']}"

        if not data:
            return f"❌ Криптовалюта \"{crypto}\" не найдена. Попробуйте другой идентификатор."

        coin = list(data.keys())[0]
        price = data[coin]["usd"]
        change = data[coin].get("usd_24h_change", 0)

        change_icon = "📈" if change >= 0 else "📉"
        change_sign = "+" if change >= 0 else ""

        return (
            f"💰 **{coin.replace('-', ' ').title()}**\n\n"
            f"💵 Цена: ${price:,.2f}\n"
            f"{change_icon} Изменение за 24ч: {change_sign}{change:.2f}%"
        )
    except requests.exceptions.RequestException:
        return f"❌ Ошибка при запросе к CoinGecko. Попробуйте позже."
    except Exception as e:
        return f"❌ Ошибка: {e}"


def get_fiat_rate_tool(currency: str = "USD") -> str:
    """
    Получает курсы фиатных валют по отношению к USD.

    Запрашивает курсы USD к EUR, RUB и GEL через Open Exchange Rates API.

    Args:
        currency: Код валюты для получения курсов
                  (например, 'USD', 'EUR', 'RUB', 'GEL').

    Returns:
        str: Текущие курсы фиатных валют.
    """
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get("result") != "success":
            return "❌ Ошибка при получении курсов валют."

        rates = data.get("rates", {})

        # Курсы к USD
        usd_rates = {
            "USD": 1.0,
            "EUR": rates.get("EUR", "N/A"),
            "RUB": rates.get("RUB", "N/A"),
            "GEL": rates.get("GEL", "N/A"),
        }

        result = "💱 **Курсы валют к USD**\n\n"
        result += f"🇺🇸 1 USD = {usd_rates['USD']:.4f} USD\n"
        result += f"🇪🇺 1 USD = {usd_rates['EUR']:.4f} EUR\n"
        result += f"🇷🇺 1 USD = {usd_rates['RUB']:.4f} RUB\n"
        result += f"🇬🇪 1 USD = {usd_rates['GEL']:.4f} GEL\n"

        # Инвертированные курсы
        result += "\n**В обратную сторону:**\n\n"
        if usd_rates['EUR'] != "N/A":
            result += f"1 EUR = {1 / usd_rates['EUR']:.4f} USD\n"
        if usd_rates['RUB'] != "N/A":
            result += f"1 RUB = {1 / usd_rates['RUB']:.4f} USD\n"
        if usd_rates['GEL'] != "N/A":
            result += f"1 GEL = {1 / usd_rates['GEL']:.4f} USD\n"

        return result
    except requests.exceptions.RequestException:
        return "❌ Ошибка при запросе курсов валют. Попробуйте позже."
    except Exception as e:
        return f"❌ Ошибка: {e}"


def generate_qr_code_tool(data: str) -> str:
    """
    Генерирует QR-код из переданных данных и возвращает его как base64 PNG.

    Args:
        data: Данные для кодирования в QR-код
              (URL, текст, телефон и т.д.).

    Returns:
        str: Base64-строка PNG-изображения QR-кода.
             Telegram-бот может отправить это как фотографию.
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Конвертируем в PNG base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode("utf-8")

        return img_base64
    except Exception as e:
        return f"❌ Ошибка генерации QR-кода: {e}"


def list_products_tool() -> str:
    """
    Возвращает список всех товаров из базы данных.

    Returns:
        str: Отформатированный список товаров с ID, названием,
             категорией и ценой.
    """
    products = list_products()
    if not products:
        return "📦 База данных пуста."

    result = "📦 **Список товаров:**\n\n"
    for p in products:
        result += f"  #{p['id']} **{p['name']}** — {p['category']} — {p['price']:.2f} ₽\n"

    result += f"\n📊 Всего: {len(products)} товаров"
    return result


def find_product_tool(name: str) -> str:
    """
    Ищет товары по совпадению имени в базе данных.

    Args:
        name: Подстрока для поиска по названию товара.

    Returns:
        str: Отформатированный список найденных товаров.
    """
    products = find_product(name)
    if not products:
        return f"🔍 Товары с названием \"{name}\" не найдены."

    result = f"🔍 **Найдено {len(products)} товар(ов) по запросу \"{name}\":**\n\n"
    for p in products:
        result += f"  #{p['id']} **{p['name']}** — {p['category']} — {p['price']:.2f} ₽\n"

    return result


def add_product_tool(name: str, category: str, price: float) -> str:
    """
    Добавляет новый товар в базу данных.

    Args:
        name: Название товара.
        category: Категория товара.
        price: Цена товара в рублях.

    Returns:
        str: Сообщение о результате добавления.
    """
    try:
        product = add_product(name, category, price)
        return (
            f"✅ **Товар успешно добавлен!**\n\n"
            f"  📦 Название: {product['name']}\n"
            f"  📂 Категория: {product['category']}\n"
            f"  💰 Цена: {product['price']:.2f} ₽\n"
            f"  🆔 ID: {product['id']}"
        )
    except Exception as e:
        return f"❌ Ошибка при добавлении товара: {e}"


def calculate_tool(expression: str) -> str:
    """
    Безопасный калькулятор математических выражений.

    Использует AST для безопасного парсинга и вычисления.
    Поддерживает: +, -, *, /, //, %, **, abs, round, min, max, sum,
    sqrt, floor, ceil, pi, e, tau.

    Args:
        expression: Математическое выражение.

    Returns:
        str: Результат вычисления или сообщение об ошибке.
    """
    result = _safe_calculate(expression)
    return f"🧮 **Результат:** `{expression}` = `{result}`"
