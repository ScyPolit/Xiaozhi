from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
XIAOZHI_CONFIG_URL = "http://192.168.31.219/xiaozhi_config"
EXPECTED_TOKEN = "test-token"
PROXY_TARGET_HOST = "192.168.31.163"
PROXY_TARGET_PORT = "8000"
TOOL_BRIDGE_PORT = "18790"


def port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def local_lan_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect((PROXY_TARGET_HOST, int(PROXY_TARGET_PORT)))
        return sock.getsockname()[0]


def expected_ws_url() -> str:
    return f"ws://{local_lan_ip()}:8000/xiaozhi/v1/"


def start_hidden(args: list[str], stdout_name: str, stderr_name: str) -> None:
    with (ROOT / stdout_name).open("ab") as stdout, (ROOT / stderr_name).open("ab") as stderr:
        subprocess.Popen(
            args,
            cwd=str(ROOT.parent),
            stdout=stdout,
            stderr=stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )


def ensure_proxy() -> None:
    if port_open("127.0.0.1", 8000):
        return
    start_hidden(
        [
            PYTHON,
            str(ROOT / "scripts" / "tcp_proxy.py"),
            "--listen-host",
            "0.0.0.0",
            "--listen-port",
            "8000",
            "--target-host",
            PROXY_TARGET_HOST,
            "--target-port",
            PROXY_TARGET_PORT,
        ],
        "tcp_proxy.log",
        "tcp_proxy.err.log",
    )


def ensure_tool_bridge() -> None:
    if port_open("127.0.0.1", int(TOOL_BRIDGE_PORT)):
        return
    start_hidden(
        [
            PYTHON,
            str(ROOT / "scripts" / "windows_tool_bridge.py"),
            "--host",
            "0.0.0.0",
            "--port",
            TOOL_BRIDGE_PORT,
            "--project-root",
            str(ROOT.parent),
            "--allow-commands",
        ],
        "windows_tool_bridge.log",
        "windows_tool_bridge.err.log",
    )


def http_get_json(url: str, timeout: float = 4.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def http_post_json(url: str, payload: dict, timeout: float = 4.0) -> str:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def ensure_xiaozhi_config() -> None:
    try:
        config = http_get_json(XIAOZHI_CONFIG_URL)
    except Exception as exc:
        log(f"xiaozhi config check failed: {exc}")
        return
    try:
        ws_url = expected_ws_url()
    except Exception as exc:
        log(f"local lan ip check failed: {exc}")
        return
    if config.get("websocket_url") == ws_url and config.get("websocket_token") == EXPECTED_TOKEN:
        return
    try:
        http_post_json(
            XIAOZHI_CONFIG_URL,
            {"websocket_url": ws_url, "websocket_token": EXPECTED_TOKEN},
        )
        log(f"fixed xiaozhi websocket url: {config.get('websocket_url')} -> {ws_url}")
    except Exception as exc:
        log(f"xiaozhi config fix failed: {exc}")


def log(message: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + message + "\n"
    with (ROOT / "xiaozhi_watchdog.log").open("a", encoding="utf-8") as file:
        file.write(line)


def main() -> None:
    log("watchdog started")
    while True:
        try:
            ensure_proxy()
            ensure_tool_bridge()
            ensure_xiaozhi_config()
        except Exception as exc:
            log(f"watchdog loop error: {exc}")
        time.sleep(20)


if __name__ == "__main__":
    main()
