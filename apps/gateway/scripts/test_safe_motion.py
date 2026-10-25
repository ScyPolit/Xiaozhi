from __future__ import annotations

import asyncio
import json
import sys

import websockets


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8000/dashboard/ws"
    async with websockets.connect(url) as websocket:
        await websocket.recv()
        await websocket.send(json.dumps({"type": "control", "method": "Stop"}))
        await asyncio.sleep(0.3)
        await websocket.send(
            json.dumps(
                {
                    "type": "control",
                    "method": "GoForward",
                    "parameters": {"speed": 70, "duration_ms": 120},
                }
            )
        )
        await asyncio.sleep(0.18)
        await websocket.send(json.dumps({"type": "control", "method": "Stop"}))
        await asyncio.sleep(0.5)
    print("safe motion pulse sent and stopped")


if __name__ == "__main__":
    asyncio.run(main())
