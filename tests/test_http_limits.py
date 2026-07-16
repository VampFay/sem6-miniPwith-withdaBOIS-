from __future__ import annotations

import anyio
import pytest
from starlette.responses import PlainTextResponse

from src.http_limits import RequestBodyLimitMiddleware


async def echo_body(scope, receive, send) -> None:
    total = 0
    while True:
        message = await receive()
        total += len(message.get("body", b""))
        if not message.get("more_body", False):
            break
    await PlainTextResponse(str(total))(scope, receive, send)


def invoke(headers: list[tuple[bytes, bytes]], chunks: list[bytes]) -> tuple[int, bytes]:
    async def run() -> tuple[int, bytes]:
        messages = [
            {
                "type": "http.request",
                "body": chunk,
                "more_body": index < len(chunks) - 1,
            }
            for index, chunk in enumerate(chunks)
        ]
        sent: list[dict] = []

        async def receive() -> dict:
            return messages.pop(0)

        async def send(message: dict) -> None:
            sent.append(message)

        app = RequestBodyLimitMiddleware(
            echo_body,
            limit_getter=lambda: 8,
            paths=frozenset({"/api/analyze"}),
        )
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/analyze",
            "headers": headers,
        }
        await app(scope, receive, send)
        status = next(
            message["status"]
            for message in sent
            if message["type"] == "http.response.start"
        )
        body = b"".join(
            message.get("body", b"") for message in sent if message["type"] == "http.response.body"
        )
        return status, body

    return anyio.run(run)


@pytest.mark.parametrize(
    "headers",
    [
        [(b"content-length", b"not-a-number")],
        [(b"content-length", b"-1")],
        [(b"content-length", b"1"), (b"content-length", b"1")],
    ],
)
def test_request_limit_rejects_ambiguous_content_length(headers) -> None:
    status, _ = invoke(headers, [b""])
    assert status == 400


def test_request_limit_rejects_stream_that_exceeds_declared_or_absent_length() -> None:
    status, body = invoke([], [b"12345", b"6789"])
    assert status == 413
    assert b"Request exceeds" in body


def test_request_limit_allows_bounded_stream() -> None:
    status, body = invoke([(b"content-length", b"8")], [b"1234", b"5678"])
    assert status == 200
    assert body == b"8"
