from __future__ import annotations

from collections.abc import Callable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class _RequestBodyTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    """Reject an oversized request before multipart parsing or endpoint execution."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limit_getter: Callable[[], int],
        paths: frozenset[str],
    ) -> None:
        self.app = app
        self.limit_getter = limit_getter
        self.paths = paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") not in self.paths:
            await self.app(scope, receive, send)
            return

        limit = self.limit_getter()
        if limit < 1:
            await self._error(scope, receive, send, 503, "Request limit is not configured.")
            return

        content_length = self._content_length(scope)
        if content_length is None:
            await self._error(scope, receive, send, 400, "Content-Length is invalid.")
            return
        if content_length > limit:
            await self._error(scope, receive, send, 413, "Request exceeds the upload limit.")
            return

        received = 0
        exceeded = False
        response_started = False

        async def limited_receive() -> Message:
            nonlocal exceeded, received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    raise _RequestBodyTooLarge
            return message

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            # Starlette converts multipart receive failures into a generic 400.
            # Suppress that response after our limiter has fired so the boundary
            # can return the correct fail-closed 413 contract instead.
            if exceeded:
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            if response_started:
                raise
            await self._error(scope, receive, send, 413, "Request exceeds the upload limit.")
        else:
            if exceeded:
                if response_started:
                    raise RuntimeError("Request limit was exceeded after the response started")
                await self._error(
                    scope, receive, send, 413, "Request exceeds the upload limit."
                )

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        values = [
            value
            for name, value in scope.get("headers", [])
            if name.lower() == b"content-length"
        ]
        if not values:
            return 0
        if len(values) != 1:
            return None
        try:
            value = int(values[0])
        except ValueError:
            return None
        return value if value >= 0 else None

    @staticmethod
    async def _error(
        scope: Scope,
        receive: Receive,
        send: Send,
        status_code: int,
        detail: str,
    ) -> None:
        response = JSONResponse(
            status_code=status_code,
            content={"detail": detail},
            headers={"Cache-Control": "no-store"},
        )
        await response(scope, receive, send)
