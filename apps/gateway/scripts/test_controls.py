from __future__ import annotations

import asyncio
import json

import websockets


async def main() -> None:
    async with websockets.connect("ws://127.0.0.1:8000/dashboard/ws") as websocket:
        await websocket.recv()
        for method, wait in (("TurnLeft", 0.5), ("Stop", 0.2), ("TurnRight", 0.5), ("Stop", 0.2), ("Dance", 1.0)):
            await websocket.send(json.dumps({"type": "control", "method": method, "parameters": {"speed": 60, "duration_ms": 300}}))
            await asyncio.sleep(wait)
    print("left, right, stop, and dance commands sent")


if __name__ == "__main__":
    asyncio.run(main())
