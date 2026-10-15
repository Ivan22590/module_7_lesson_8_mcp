"""
Telegram бот с интеграцией MCP и LLM.

Бот работает по следующему циклу:
1. Пользователь отправляет сообщение
2. Бот отправляет текст в LLM (ProxyAPI)
3. LLM решает, нужно ли вызвать MCP инструмент
4. Если нужно, бот делает запрос к MCP серверу и подставляет ответ
5. Бот отправляет финальный ответ пользователю

Запуск:
    python bot.py

Если Telegram API недоступен напрямую, укажите TELEGRAM_PROXY_URL в .env:
    TELEGRAM_PROXY_URL=socks5://127.0.0.1:1080
    или
    TELEGRAM_PROXY_URL=http://127.0.0.1:8080
"""

import base64
import json
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from aiogram.client.session.aiohttp import AiohttpSession
import aiohttp
from openai import AsyncOpenAI

from config import Config
from mcp_client import MCPClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Создаём сессию с поддержкой прокси (если указан TELEGRAM_PROXY_URL)
def _create_session():
    """Создаёт aiohttp-сессию, используя прокси если он указан."""
    proxy_url = getattr(Config, "TELEGRAM_PROXY_URL", None)
    if proxy_url:
        logger.info(f"Используется прокси: {proxy_url}")
        return AiohttpSession(proxy=proxy_url)
    return AiohttpSession()

# Инициализация бота
bot = Bot(token=Config.TELEGRAM_API_TOKEN, session=_create_session())
dp = Dispatcher()

# MCP клиент (глобальный)
mcp_client: MCPClient | None = None

# LLM клиент (ProxyAPI)
llm_client = AsyncOpenAI(
    api_key=Config.PROXYAPI_API_KEY,
    base_url=Config.LLM_BASE_URL,
)

# История диалогов: user_id -> список сообщений
chat_histories: dict[int, list[dict]] = {}


def get_system_message() -> dict:
    """Возвращает системное сообщение для LLM."""
    return {"role": "system", "content": Config.SYSTEM_PROMPT}


def get_user_message(text: str) -> dict:
    """Возвращает сообщение пользователя."""
    return {"role": "user", "content": text}


def get_assistant_message(content: str | None = None, tool_calls: list | None = None) -> dict:
    """Возвращает сообщение ассистента."""
    msg = {"role": "assistant"}
    if content:
        msg["content"] = content
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def get_tool_message(tool_call_id: str, content: str) -> dict:
    """Возвращает результат вызова инструмента."""
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


async def call_llm(messages: list[dict], tools: list[dict]) -> dict:
    """
    Отправляет запрос к LLM и возвращает ответ.

    Args:
        messages: История диалога.
        tools: Список доступных инструментов.

    Returns:
        dict: Ответ LLM с полями content и/или tool_calls.
    """
    response = await llm_client.chat.completions.create(
        model=Config.LLM_MODEL,
        messages=messages,
        tools=tools,
        temperature=0.7,
        max_tokens=4096,
    )
    return response.choices[0].message


async def resolve_tool_calls(tool_calls: list, tools: list[dict]) -> list[dict]:
    """
    Выполняет вызовы инструментов MCP и возвращает результаты.

    Args:
        tool_calls: Список tool_calls от LLM.
        tools: Список доступных инструментов.

    Returns:
        list[dict]: Результаты вызовов инструментов.
    """
    results = []
    for tc in tool_calls:
        tool_id = tc["id"]
        func_name = tc["function"]["name"]
        func_args = json.loads(tc["function"]["arguments"])

        logger.info(f"Вызов инструмента: {func_name}({func_args})")

        try:
            result = await mcp_client.call_tool(func_name, func_args)
            # Извлекаем content из результата MCP
            content_str = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    content_str += block["text"]
            if not content_str:
                content_str = json.dumps(result, ensure_ascii=False)

            results.append(get_tool_message(tool_id, content_str))
            logger.info(f"Результат {func_name}: {content_str[:200]}...")
        except Exception as e:
            error_msg = f"Ошибка вызова инструмента {func_name}: {e}"
            logger.error(error_msg)
            results.append(get_tool_message(tool_id, f"Ошибка: {error_msg}"))

    return results


def has_qr_code(content: str) -> bool:
    """Проверяет, содержит ли контент QR-код (base64 PNG)."""
    return content.strip().startswith("iVBOR") and len(content.strip()) > 1000


async def send_qr_code(chat_id: int, base64_data: str):
    """Отправляет QR-код как фото."""
    png_bytes = base64.b64decode(base64_data)
    await bot.send_photo(
        chat_id,
        photo=BufferedInputFile(png_bytes, filename="qr_code.png"),
        caption="📱 Ваш QR-код:",
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start — приветствие."""
    welcome_text = (
        "👋 **Привет! Я умный Telegram-ассистент!**\n\n"
        "Я могу:\n"
        "🔍 Аудит сайтов\n"
        "🌐 Поиск в интернете\n"
        "🌤️ Погода в городе\n"
        "💰 Курсы криптовалют\n"
        "💱 Курсы валют\n"
        "📱 Генерация QR-кодов\n"
        "📦 Поиск и добавление товаров\n"
        "🧮 Безопасный калькулятор\n\n"
        "Просто напишите запрос на русском языке!\n"
        "Примеры:\n"
        "• «покажи все товары»\n"
        "• «найди чай»\n"
        "• «погода в Москве»\n"
        "• «сколько биткоин»\n"
        "• «аудит сайта https://example.com»\n"
        "• «сгенерируй QR для https://google.com»"
    )
    await message.answer(welcome_text, parse_mode="Markdown")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Команда /help — справка."""
    help_text = (
        "📖 **Помощь**\n\n"
        "Я работаю через LLM и MCP-инструменты.\n"
        "Просто опишите задачу на русском языке!\n\n"
        "**Доступные команды:**\n"
        "/start — Начать работу\n"
        "/help — Показать справку\n"
        "/clear — Очистить историю диалога"
    )
    await message.answer(help_text, parse_mode="Markdown")


@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    """Команда /clear — очистка истории."""
    if message.from_user.id in chat_histories:
        chat_histories[message.from_user.id] = []
        await message.answer("🗑️ История диалога очищена.")
    else:
        await message.answer("📭 История пуста.")


@dp.message()
async def handle_message(message: types.Message):
    """Обработка обычных сообщений."""
    user_id = message.from_user.id
    text = message.text

    # Инициализируем историю, если нет
    if user_id not in chat_histories:
        chat_histories[user_id] = []

    # Добавляем сообщение пользователя в историю
    chat_histories[user_id].append(get_user_message(text))

    # Получаем инструменты из MCP
    tools = await mcp_client.get_tools_for_llm()

    # Строим полный список сообщений
    messages = [get_system_message()] + chat_histories[user_id]

    # Отправляем индикатор набора текста
    await message.answer("🤔 Думаю...")

    # Цикл: LLM → tool_calls → MCP → LLM → ответ
    final_answer = None
    tool_call_count = 0

    while tool_call_count < Config.MAX_TOOL_CALLS:
        # Запрашиваем ответ у LLM
        response = await call_llm(messages, tools)

        # Проверяем, нужно ли вызывать инструменты
        if response.tool_calls:
            tool_calls = response.tool_calls
            messages.append(get_assistant_message(tool_calls=tool_calls))

            # Выполняем инструменты
            tool_results = await resolve_tool_calls(tool_calls, tools)
            messages.extend(tool_results)

            tool_call_count += len(tool_calls)
            continue

        # LLM вернул текстовый ответ
        final_answer = response.content
        if final_answer:
            messages.append(get_assistant_message(content=final_answer))
        break

    if not final_answer:
        final_answer = "🤖 Превышено максимальное количество шагов. Попробуйте переформулировать запрос."

    # Проверяем, есть ли QR-код в ответе
    if has_qr_code(final_answer):
        # Отправляем QR-код как фото
        await send_qr_code(user_id, final_answer.strip())
        # Убираем base64 из текста, отправляем только подпись
        await message.answer("✅ QR-код сгенерирован!", parse_mode="Markdown")
    else:
        # Отправляем финальный ответ
        await message.answer(final_answer, parse_mode="Markdown")

    # Очищаем индикатор набора
    # (необязательно, aiogram сам убирает)


async def on_startup(dispatcher, *args, **kwargs):
    """Инициализация при запуске бота (колбэк aiogram startup)."""
    global mcp_client

    logger.info("Подключение к MCP серверу...")
    mcp_client = MCPClient(Config.MCP_SERVER_URL)
    await mcp_client.connect()

    # Получаем список инструментов
    tools = await mcp_client.get_tools_for_llm()
    logger.info(f"Доступно {len(tools)} инструментов:")
    for tool in tools:
        func = tool["function"]
        logger.info(f"  - {func['name']}: {func['description'][:60]}...")

    logger.info("✅ Бот готов к работе!")


async def on_shutdown(dispatcher, *args, **kwargs):
    """Закрытие при остановке бота (колбэк aiogram shutdown)."""
    global mcp_client
    if mcp_client and mcp_client.is_connected:
        await mcp_client.close()
        mcp_client = None
    logger.info("Бот остановлен.")


if __name__ == "__main__":
    # Регистрируем колбэки старта и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        logger.info("Запуск Telegram бота...")
        dp.run_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")
