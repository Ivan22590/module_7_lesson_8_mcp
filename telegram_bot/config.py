"""
Конфигурация Telegram бота.

Загружает переменные окружения из .env файла:
- TELEGRAM_API_TOKEN — токен бота от BotFather
- PROXYAPI_API_KEY — API-ключ для ProxyAPI (LLM)
- MCP_SERVER_URL — URL MCP сервера (по умолчанию http://localhost:8000)
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из корня проекта
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


class Config:
    """Конфигурация бота, загружаемая из переменных окружения."""

    TELEGRAM_API_TOKEN: str = os.getenv("TELEGRAM_API_TOKEN", "")
    PROXYAPI_API_KEY: str = os.getenv("PROXYAPI_API_KEY", "")
    MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    
    # Прокси для Telegram Bot API (если api.telegram.org недоступен напрямую)
    # Примеры:
    #   TELEGRAM_PROXY_URL=http://127.0.0.1:8080
    #   TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080
    TELEGRAM_PROXY_URL: str | None = os.getenv("TELEGRAM_PROXY_URL") or None

    # LLM-параметры
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-5.6-luna")
    LLM_BASE_URL: str = "https://api.proxyapi.ru/v1"

    # Системная инструкция для LLM
    SYSTEM_PROMPT: str = """
Ты — умный и дружелюбный ассистент в Telegram.
Ты обладаешь набором инструментов (tools) и можешь вызывать их по необходимости.

Твои инструменты:
1. **check_site_tool(url)** — Аудит сайта по URL: скорость, вес, HTTPS, мобильная версия,
   заголовок, оффер, Яндекс.Метрика, формы/телефоны, общая оценка N/100 и рекомендации.

2. **web_search(query)** — Поиск в интернете через DuckDuckGo. Возвращает до 5 результатов.

3. **get_weather(city)** — Текущая погода в городе: температура, ветер, описание.

4. **get_crypto_price(crypto)** — Курс криптовалюты в USD с изменением за 24ч.

5. **get_fiat_rate(currency)** — Курсы фиатных валют (USD→EUR, RUB, GEL).

6. **generate_qr_code(data)** — Генерация QR-кода из текста или URL.

7. **list_products()** — Список всех товаров из базы данных.

8. **find_product(name)** — Поиск товаров по названию.

9. **add_product(name, category, price)** — Добавить товар в базу.

10. **calculate(expression)** — Безопасный калькулятор.

Правила:
- Отвечай на русском языке, если пользователь пишет на русском.
- Используй инструменты, когда это уместно — не бойся их вызывать.
- Форматируй ответы красиво, с эмодзи и структурой.
- Если запрос непонятен — задай уточняющий вопрос.
- Для QR-кода: после генерации сообщи боту, что нужно отправить изображение.
- Для калькулятора: передавай только математические выражения.
- Не добавляй инструменты, которых нет в списке выше.
- Всегда используй tool_calls, когда инструмент может помочь.
    """.strip()

    # Максимальное количество шагов tool_calls за один ответ LLM
    MAX_TOOL_CALLS: int = 5
