from __future__ import annotations

import argparse
import json
import signal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


PINS = {1: 17, 2: 18, 3: 27, 4: 22, 5: 23, 6: 24}
NAMES = {1: "客厅灯", 2: "卧室灯", 3: "厨房灯", 4: "卫生间灯", 5: "梳妆台灯", 6: "空调"}


class GpioController:
    def __init__(self, simulate: bool) -> None:
        self.simulate = simulate
        self.states = {device_id: False for device_id in PINS}
        self.gpio = None
        if not simulate:
            from gpiozero import LED

            self.gpio = {device_id: LED(pin) for device_id, pin in PINS.items()}

    def set(self, device_id: int, state: bool) -> None:
        if device_id not in self.states:
            raise ValueError("invalid device id")
        self.states[device_id] = state
        if self.gpio:
            self.gpio[device_id].on() if state else self.gpio[device_id].off()

    def set_lights(self, state: bool) -> None:
        for device_id in range(1, 6):
            self.set(device_id, state)

    def snapshot(self) -> list[dict]:
        return [
            {"id": device_id, "name": NAMES[device_id], "pin": f"BCM{pin}", "state": self.states[device_id]}
            for device_id, pin in PINS.items()
        ]


class Handler(BaseHTTPRequestHandler):
    controller: GpioController

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/health":
                self.reply({"ok": True, "device": "RaspberryPi-GPIO", "simulate": self.controller.simulate})
            elif parsed.path == "/api/leds":
                self.reply({"ok": True, "leds": self.controller.snapshot()})
            elif parsed.path == "/api/led":
                device_id = int(query.get("id", ["0"])[0])
                state = self._state(query)
                self.controller.set(device_id, state)
                self.reply({"ok": True, "id": device_id, "state": state})
            elif parsed.path == "/api/all":
                state = self._state(query)
                self.controller.set_lights(state)
                self.reply({"ok": True, "state": state})
            elif parsed.path == "/api/ac":
                state = self._state(query)
                self.controller.set(6, state)
                self.reply({"ok": True, "id": 6, "state": state})
            else:
                self.reply({"ok": False, "error": "not found"}, 404)
        except (ValueError, KeyError) as exc:
            self.reply({"ok": False, "error": str(exc)}, 400)

    @staticmethod
    def _state(query: dict) -> bool:
        value = query.get("state", [""])[0].lower()
        if value not in {"on", "off"}:
            raise ValueError("state must be on or off")
        return value == "on"

    def _headers(self) -> None:
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Cache-Control", "no-store")

    def reply(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._headers()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[smart-home] {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18880)
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()
    Handler.controller = GpioController(args.simulate)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    signal.signal(signal.SIGTERM, lambda *_: server.shutdown())
    print(f"smart-home API listening on http://{args.host}:{args.port} simulate={args.simulate}")
    server.serve_forever()


if __name__ == "__main__":
    main()
