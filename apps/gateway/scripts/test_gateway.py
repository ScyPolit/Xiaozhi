from __future__ import annotations

import asyncio
import inspect
import json
import sys
import time

import websockets


async def run(text: str) -> dict[str, float | int]:
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8000/xiaozhi/v1/"
    token = sys.argv[2] if len(sys.argv) > 2 else "test-token"
    headers = {"Authorization": f"Bearer {token}", "Protocol-Version": "1", "Device-Id": "test-device", "Client-Id": "test-client"}
    header_arg = "additional_headers" if "additional_headers" in inspect.signature(websockets.connect).parameters else "extra_headers"
    started = time.perf_counter()
    first_text = 0.0
    first_audio = 0.0
    audio_frames = 0
    async with websockets.connect(url, **{header_arg: headers}) as ws:
        await ws.send(json.dumps({"type": "hello", "version": 1, "transport": "websocket", "audio_params": {"format": "opus", "sample_rate": 16000, "channels": 1, "frame_duration": 60}}))
        hello = json.loads(await ws.recv())
        assert hello["type"] == "hello"
        await ws.send(json.dumps({"type": "listen", "state": "start", "mode": "manual"}))
        await ws.send(json.dumps({"type": "listen", "state": "stop", "test_text": text}, ensure_ascii=False))
        while True:
            message = await asyncio.wait_for(ws.recv(), timeout=30)
            elapsed = time.perf_counter() - started
            if isinstance(message, bytes):
                audio_frames += 1
                first_audio = first_audio or elapsed
                continue
            data = json.loads(message)
            if data.get("text_delta") and not first_text:
                first_text = elapsed
            if data.get("type") == "tts" and data.get("state") == "stop":
                return {"first_text_ms": round(first_text * 1000), "first_audio_ms": round(first_audio * 1000), "total_ms": round(elapsed * 1000), "audio_frames": audio_frames}


async def main() -> None:
    text = sys.argv[3] if len(sys.argv) > 3 else "请用一句话介绍你自己。"
    metrics = await run(text)
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
