from __future__ import annotations

import json
import logging

from aiohttp import ClientSession, ClientTimeout, web


UPSTREAM = "https://text.pollinations.ai/openai"
LOGGER = logging.getLogger("pollinations-proxy")


async def models(_: web.Request) -> web.Response:
    return web.json_response(
        {
            "object": "list",
            "data": [{"id": "openai", "object": "model", "created": 0, "owned_by": "pollinations"}],
        }
    )


async def chat(request: web.Request) -> web.Response:
    payload = await request.json()
    payload["model"] = "openai"
    timeout = ClientTimeout(total=90, connect=10)
    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.post(UPSTREAM, json=payload) as upstream:
                body = await upstream.read()
                content_type = upstream.headers.get("Content-Type", "application/json").split(";", 1)[0]
                return web.Response(status=upstream.status, body=body, content_type=content_type)
    except Exception as exc:
        LOGGER.exception("upstream request failed")
        return web.json_response({"error": {"message": str(exc), "type": "upstream_error"}}, status=502)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = web.Application(client_max_size=2 * 1024 * 1024)
    app.router.add_get("/v1/models", models)
    app.router.add_post("/v1/chat/completions", chat)
    web.run_app(app, host="127.0.0.1", port=18791, print=None)


if __name__ == "__main__":
    main()
