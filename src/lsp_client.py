# https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/

from asyncio import Future, Task
from asyncio.streams import StreamReader, StreamWriter
from asyncio.subprocess import Process
from collections.abc import AsyncGenerator, Callable, Coroutine, Mapping
from typing import Any
import asyncio

# import difflib
import json
import logging
import uuid
import lsp_types as lsp

logger = logging.getLogger(__name__)


class JsonRpcDispatcher:
    """A JSON-RPC dispatcher.

    Attributes:
      on_close: A callback function for connection close events.
      on_notification: A callback function for incoming notifications.
    """

    def __init__(self, reader: StreamReader, writer: StreamWriter):
        self.on_close: Callable[[], None] | None = None
        self.on_notification: Callable[[str, Any], None] | None = None
        self._callback_id: int = 1
        self._callbacks: dict[int, Future] = {}
        self._reader: StreamReader = reader
        self._writer: StreamWriter = writer
        self._read_loop_task: Task | None = None

    async def start(self) -> None:
        """Start listening for messages from the JSON-RPC server."""
        self._read_loop_task = asyncio.create_task(self._read_loop())

    def stop(self) -> None:
        """Stop processing messages from the JSON-RPC server."""
        if self._read_loop_task:
            self._read_loop_task.cancel()
        for _, callback in self._callbacks.items():
            callback.cancel()
        self._callback_id = 1
        self._callbacks.clear()

    async def send(
        self, method: str, params: lsp.LSPArray | lsp.LSPObject | None
    ) -> Any:
        """Send a request to the server.

        Args:
          method: The name of the method to invoke.
          params: The parameters used to invoke the method.

        Raises:
          ValueError: If method is empty or None.
        """
        if not method:
            raise ValueError("Method must be given a value")
        callback_id = self._callback_id
        self._callback_id += 1
        self._callbacks[callback_id] = asyncio.Future()
        payload = {
            "jsonrpc": "2.0",
            "id": callback_id,
            "method": method,
            "params": params,
        }
        await self._send(payload)

        data = await self._callbacks[callback_id]
        del self._callbacks[callback_id]

        return data

    async def send_error(
        self, code: int, message: str, data: lsp.LSPAny | None
    ) -> None:
        """Send a error response to the server.

        Args:
          code: The error code.
          message: The error message.
          data: Optional data.
        """
        payload = {code: code, message: message}
        if data:
            payload["data"] = data
        await self._send(payload)

    async def send_notification(
        self, method: str, params: lsp.LSPArray | lsp.LSPObject | None = None
    ) -> None:
        """Send a notification to the server.

        Args:
          method: The name of the method to invoke.
          params: The parameters used to invoke the method.

        Raises:
          ValueError: If method is empty or None.
        """
        message: Any = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        await self._send(message)

    async def _send(self, message: dict):
        content = json.dumps(message)
        data = f"Content-Length: {len(content)}\r\n\r\n{content}"
        self._writer.write(data.encode())
        try:
            await self._writer.drain()
        except ConnectionResetError:
            if self.on_close:
                self.on_close()
        return

    async def _read_loop(self) -> Coroutine[None, None, None]:
        async for message in self._read_messages():
            if message.get("jsonrpc") != "2.0":
                logger.error("Invalid JSON-RPC version")
                await self.send_error(
                    lsp.ErrorCodes.InvalidRequest, "Invalid JSON-RPC version", None
                )
                continue
            if callback_id := message.get("id"):
                if callback_id not in self._callbacks:
                    continue
                future = self._callbacks[callback_id]
                if "result" in message:
                    future.set_result(message["result"])
                elif "error" in message:
                    future.set_exception(ValueError(message["error"]))
                else:
                    future.set_exception(ValueError("Invalid message"))
            else:
                if self.on_notification is not None:
                    self.on_notification(message["method"], message.get("params"))
        return

    async def _read_messages(self) -> AsyncGenerator[Any, None]:
        while not self._reader.at_eof():
            headers = {}
            while True:
                line = await self._reader.readline()
                if line == b"\r\n":
                    break
                name, value = line.decode("ascii").rstrip().split(":")
                headers[name] = value.lstrip()
            if value := headers.get("Content-Type"):
                if "utf-8" not in value:
                    logger.error("Unexpected Content-Type header")
                    await self.send_error(
                        lsp.ErrorCodes.InvalidRequest,
                        "Unexpected Content-Type header",
                        None,
                    )
                    continue
            if value := headers.get("Content-Length"):
                content_length = int(value)
                message = await self._reader.readexactly(content_length)
                try:
                    message = json.loads(message)
                except json.decoder.JSONDecodeError as e:
                    await self.send_error(
                        lsp.ErrorCodes.ParseError, "Could not deserialize JSON", e.msg
                    )
                    continue
                yield message
            else:
                logger.error("Missing Content-Length header")
                await self.send_error(
                    lsp.ErrorCodes.InvalidRequest, "Missing Content-Length header", None
                )
        return


class LspClient:
    """A Language Server Protocol (LSP) client.

    Args:
      json_rpc_client: The JSON-RPC client.

    Attributes:
      on_notification: A callback function for incoming notifications.
      server_capabilities: The LSP capabilities advertised by the LSP server.
      notifications: Functions that send notifications.
      requests: Functions that send requests.
    """

    def __init__(self, reader: StreamReader, writer: StreamWriter):
        super().__init__()
        self.on_notification: Callable[[str, Any], None] | None
        self.server_capabilities: lsp.ServerCapabilities | None = None
        self._client = JsonRpcDispatcher(reader, writer)
        self._documents: dict[lsp.DocumentUri, dict[str, Any]] = {}
        self.notifications = lsp.NotificationFunctions(
            self._client.send_notification, lambda method, timeout: asyncio.Future()
        )
        self.requests = lsp.RequestFunctions(self._send)
        self.work_progress: dict[str, Any] = {}
        asyncio.create_task(self._client.start())

    def set_notification_handler(
        self, callback: Callable[[str, Any], None] | None
    ) -> None:
        self._client.on_notification = callback

    async def initialize(self, params: lsp.InitializeParams):
        """Initialize the client."""
        data: lsp.InitializeResult = await self.requests.initialize(params)
        self.server_capabilities = data["capabilities"]
        await self.notifications.initialized({})

    async def open_document(self, uri: lsp.DocumentUri, text: str) -> None:
        """Open document.

        Args:
          uri: The document URI.
          text: The text of the document.

        Raises:
          ValueError: If the document is already open.
        """
        if uri in self._documents:
            raise ValueError("URI already exist")
        self._documents[uri] = {"text": text, "version": 0}
        params: lsp.DidOpenTextDocumentParams = {
            "textDocument": {
                "uri": uri,
                "languageId": lsp.LanguageKind.Python,
                "version": 0,
                "text": text,
            }
        }
        await self.notifications.did_open_text_document(params)

    async def close_document(self, uri: lsp.DocumentUri) -> None:
        """Close document.

        Args:
          uri: The document URI.

        Raises:
          ValueError: If the document is not open.
        """
        if uri not in self._documents:
            raise ValueError("URI does not exist")
        del self._documents[uri]
        params: lsp.DidCloseTextDocumentParams = {"textDocument": {"uri": uri}}
        await self.notifications.did_close_text_document(params)

    async def update_document(self, uri: lsp.DocumentUri, text: str) -> None:
        """Update document with new text.

        Args:
          uri: The document URI.
          text: The new text to update the document with.

        Raises:
          ValueError: If the document is not open.
        """
        if uri not in self._documents:
            raise ValueError("URI does not exist")
        document = self._documents[uri]
        content_changes: list[lsp.TextDocumentContentChangeEvent] = []
        assert self.server_capabilities is not None

        match self.server_capabilities["textDocumentSync"]:
            case lsp.TextDocumentSyncKind.None_:
                pass
            case lsp.TextDocumentSyncKind.Full:
                content_changes.append({"text": text})
            case lsp.TextDocumentSyncKind.Incremental:
                # content_changes = get_string_differences(document["text"], text)
                content_changes = get_lazy_cheat_diff(document["text"], text)

        document["version"] += 1
        self._documents[uri] = document
        params: lsp.DidChangeTextDocumentParams = {
            "textDocument": {"uri": uri, "version": document["version"]},
            "contentChanges": content_changes,
        }

        await self.notifications.did_change_text_document(params)

    async def exit(self) -> None:
        """Tell the LSP server to exit."""
        if self._client._writer:
            await self.notifications.exit()
            self._client.stop()

    async def _send(
        self, method: str, params: lsp.LSPArray | lsp.LSPObject | None
    ) -> Any:
        work_done_token = str(uuid.uuid4())
        self.work_progress[work_done_token] = None
        if isinstance(params, Mapping):
            params["workDoneToken"] = work_done_token  # type: ignore
        result = await self._client.send(method, params)
        del self.work_progress[work_done_token]
        return result


def get_lazy_cheat_diff(
    string_old: str, string_new: str
) -> list[lsp.TextDocumentContentChangeEvent]:
    """The lazy way of doing it.

    TODO: Write a real implementation using difflib without cheating.
    """
    differences: list[lsp.TextDocumentContentChangeEvent] = []

    if string_old != "":
        lines = string_old.splitlines()
        end_line = len(lines)
        end_char = len(lines[-1]) if lines else 0
        differences.append(
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": end_line, "character": end_char},
                },
                "text": "",
            }
        )

    if string_new != "":
        lines = string_new.splitlines()
        end_line = len(lines)
        end_char = len(lines[-1]) if lines else 0
        differences.append(
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": end_line, "character": end_char},
                },
                "text": string_new,
            }
        )

    return differences


async def start_lsp_process(program, args: list[str]) -> Process:
    """Start a LSP process.

    Args:
      program: The LSP process.
      args: The command-line arguments to pass to the process.

    Returns:
      The LSP process.
    """
    process = await asyncio.create_subprocess_exec(
        program,
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def log_stderr(reader):
        while not reader.at_eof():
            line = await reader.readline()
            logger.debug(line)

    asyncio.create_task(log_stderr(process.stderr))

    return process
