"""
MCP клиент для Telegram бота.

Подключается к MCP серверу через SSE-транспорт и позволяет
вызывать инструменты удалённо через HTTP.
Использует официальный MCP SDK client API.

Важно: ClientSession должен быть открыт через async context manager,
иначе фоновый _receive_loop не запустится и любой запрос зависнет.
"""

from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client


class MCPClient:
    """Клиент для общения с MCP сервером через SSE."""

    def __init__(self, server_url: str):
        """
        Инициализирует MCP клиент.

        Args:
            server_url: URL MCP сервера, например http://localhost:8000
        """
        self.server_url = server_url.rstrip("/")
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    @property
    def is_connected(self) -> bool:
        """Подключено ли состояние клиента к серверу."""
        return self._session is not None

    async def connect(self):
        """
        Устанавливает SSE-подключение и инициализирует MCP сессию.

        Сессия остаётся открытой до вызова close().
        Фоновый _receive_loop запускается внутри ClientSession.__aenter__.

        Raises:
            Exception: Если не удалось подключиться к серверу.
        """
        sse_url = f"{self.server_url}/sse"
        self._exit_stack = AsyncExitStack()

        # Открываем SSE-транспорт
        read_stream, write_stream = await self._exit_stack.enter_async_context(
            sse_client(sse_url)
        )

        # Открываем MCP-сессию — это запускает _receive_loop!
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        # Рукопожатие: сервер отвечает, receive_loop перехватывает
        await self._session.initialize()

    async def close(self):
        """Закрывает сессию и SSE-соединение."""
        if self._exit_stack is not None:
            await self._exit_stack.aclose()
            self._exit_stack = None
        self._session = None

    async def list_tools(self) -> list[dict]:
        """
        Запрашивает у сервера список доступных инструментов.

        Returns:
            list[dict]: Список инструментов с их схемами параметров.
        """
        if not self._session:
            raise RuntimeError("Не подключено к серверу. Вызовите connect() сначала.")

        result = await self._session.list_tools()
        tools = []
        for tool in result.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "inputSchema": tool.inputSchema or {},
            })
        return tools

    async def call_tool(self, tool_name: str, tool_args: dict) -> dict:
        """
        Вызывает инструмент на MCP сервере.

        Args:
            tool_name: Имя инструмента, например "check_site_tool".
            tool_args: Аргументы инструмента в виде словаря.

        Returns:
            dict: Результат вызова со списком блоков "content".
        """
        if not self._session:
            raise RuntimeError("Не подключено к серверу. Вызовите connect() сначала.")

        result = await self._session.call_tool(tool_name, tool_args)

        # Собираем текстовые блоки ответа в plain-строку
        content_blocks = []
        for block in result.content:
            item = {"type": getattr(block, "type", "text")}
            text = getattr(block, "text", None)
            if text is not None:
                item["text"] = text
            content_blocks.append(item)

        return {
            "content": content_blocks,
            "isError": bool(getattr(result, "isError", False)),
        }

    async def get_tools_for_llm(self) -> list[dict]:
        """
        Получает список инструментов в формате OpenAI function calling.

        Returns:
            list[dict]: Инструменты с name, description и parameters.
        """
        tools = await self.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("inputSchema") or {"type": "object", "properties": {}},
                },
            }
            for tool in tools
        ]
