# 🤖 Telegram Bot + MCP Server

Полнофункциональный проект, состоящий из двух компонентов:

1. **MCP Server** (`mcp_server/`) — набор инструментов (tools) через Model Context Protocol
2. **Telegram Bot** (`telegram_bot/`) — умный бот, подключённый к LLM и MCP-инструментам

## 📦 Архитектура

```
┌─────────────────┐     SSE/HTTP      ┌──────────────────┐
│  Telegram Bot   │ ────────────────▶ │  MCP Server      │
│  (aiogram)      │                   │  (FastMCP + SSE) │
│                 │                   │                  │
│  LLM (ProxyAPI) │                   │  Tools:          │
│  ──────────────▶│                   │  • check_site    │
│  (gpt-5.6-luna) │                   │  • web_search    │
│                 │                   │  • get_weather   │
│  Tool Calls ◀───│                   │  • get_crypto    │
│                 │                   │  • get_fiat      │
│                 │                   │  • qr_code       │
│                 │                   │  • products DB   │
│                 │                   │  • calculate     │
└─────────────────┘                   └──────────────────┘
```

## 🚀 Быстрый старт

### 1. Клонирование и подготовка

```bash
# Создаём .env файл из примера
cp .env.example .env
```

### 2. Настройка .env

Откройте `.env` и заполните переменные:

```env
# Токен от BotFather (Telegram)
TELEGRAM_API_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# API-ключ ProxyAPI (получить на https://proxyapi.ru)
PROXYAPI_API_KEY=your_proxyapi_key_here

# URL MCP сервера (по умолчанию локальный)
MCP_SERVER_URL=http://localhost:8000

# Модель LLM
LLM_MODEL=openai/gpt-5.6-luna
```

### 3. Создание виртуальных окружений

```bash
# MCP Server
python -m venv .venv-mcp
.venv-mcp\Scripts\activate
pip install -r mcp_server/requirements.txt

# Telegram Bot
python -m venv .venv-bot
.venv-bot\Scripts\activate
pip install -r telegram_bot/requirements.txt
```

### 4. Запуск MCP Server

```bash
# Активируем окружение MCP
.venv-mcp\Scripts\activate

# Запускаем сервер
cd mcp_server
python server.py
```

Сервер запустится на `http://localhost:8000` с SSE-эндпоинтом `http://localhost:8000/sse`.

### 5. Запуск Telegram Bot

```bash
# Открываем новое окно терминала, активируем окружение бота
.venv-bot\Scripts\activate

# Запускаем бота
cd telegram_bot
python bot.py
```

### 6. Взаимодействие с ботом

Откройте Telegram и найдите своего бота. Напишите `/start` для приветствия.

Примеры команд:
- `покажи все товары` — список всех товаров
- `найди чай` — поиск товаров по названию
- `добавь товар яблоки 120 фрукт` — добавление товара
- `погода в Москве` — текущая погода
- `сколько биткоин` — курс криптовалюты
- `аудит сайта https://example.com` — аудит сайта
- `генерируй QR для https://google.com` — QR-код
- `посчитай 2 + 2 * 3` — калькулятор

## 📂 Структура проекта

```
├── .env.example              # Пример конфигурации
├── .env                      # Ваша конфигурация (не в git)
├── .gitignore                # Исключённые файлы
├── README.md                 # Этот файл
├── mcp_server/               # MCP Server
│   ├── server.py             # Точка входа, FastMCP, SSE
│   ├── tools.py              # Реализация 10 инструментов
│   ├── db.py                 # SQLite: инициализация, CRUD
│   ├── products.db           # БД создаётся автоматически
│   └── requirements.txt      # Зависимости
└── telegram_bot/             # Telegram Bot
    ├── bot.py                # aiogram: цикл LLM → tool_calls → MCP
    ├── config.py             # Конфигурация из .env
    ├── mcp_client.py         # MCP клиент (SSE)
    └── requirements.txt      # Зависимости
```

## 🛠 Инструменты MCP

| Инструмент | Описание |
|------------|----------|
| `check_site_tool(url)` | Аудит сайта: скорость, HTTPS, SEO, оценка N/100 |
| `web_search(query)` | Поиск через DuckDuckGo |
| `get_weather(city)` | Погода: температура, ветер, описание |
| `get_crypto_price(crypto)` | Курс крипты в USD с изменением за 24ч |
| `get_fiat_rate(currency)` | Курсы фиатных валют (USD→EUR/RUB/GEL) |
| `generate_qr_code(data)` | Генерация QR-кода (base64 PNG) |
| `list_products()` | Список всех товаров из БД |
| `find_product(name)` | Поиск товаров по названию |
| `add_product(name, category, price)` | Добавление товара |
| `calculate(expression)` | Безопасный калькулятор (AST) |

## 🔧 Технологии

- **MCP Server:** Python MCP SDK, FastMCP, SSE transport
- **Telegram Bot:** aiogram 3, OpenAI SDK (ProxyAPI)
- **LLM:** ProxyAPI (OpenAI-compatible, модель `openai/gpt-5.6-luna`)
- **База данных:** SQLite3
- **Связь:** MCP Client → SSE → HTTP POST

## ⚙️ Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TELEGRAM_API_TOKEN` | Токен бота от BotFather | — |
| `PROXYAPI_API_KEY` | API-ключ ProxyAPI | — |
| `MCP_SERVER_URL` | URL MCP сервера | `http://localhost:8000` |
| `LLM_MODEL` | Модель LLM | `openai/gpt-5.6-luna` |

## 🐛 Решение проблем

### MCP Server не запускается

```bash
# Проверьте, что все зависимости установлены
pip install -r mcp_server/requirements.txt

# Проверьте порт 8000
netstat -ano | findstr :8000
```

### Бот не подключается к MCP

```bash
# Убедитесь, что MCP сервер запущен
curl http://localhost:8000/sse
# Должен вернуть SSE-поток

# Проверьте MCP_SERVER_URL в .env
```

### LLM не отвечает

```bash
# Проверьте PROXYAPI_API_KEY
# Проверьте доступ к https://api.proxyapi.ru/v1
curl -H "Authorization: Bearer your_key" https://api.proxyapi.ru/v1/models
```

## 📄 Лицензия

MIT

## 👨‍💻 Автор

Проект создан для демонстрации интеграции Telegram бота, LLM и MCP-инструментов.
