"""Quick LAN scan: find Xiaozhi ESP32 (/xiaozhi_config) and OpenClaw (:18789)."""
from __future__ import annotations

import concurrent.futures as cf
import socket
import urllib.request

SUBNET = "192.168.203"


def tcp_probe(host_port: tuple[str, int], timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host_port[0], host_port[1]), timeout=timeout):
            return True
    except OSError:
        return False


def http_probe(url: str, timeout: float = 0.5) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read(512).decode("utf-8", errors="ignore")
    except Exception:
        return None


def scan(ip: str) -> list[str]:
    found = []
    if tcp_probe((ip, 18789)):
        found.append(f"OPENCLAW {ip}:18789")
    body = http_probe(f"http://{ip}/xiaozhi_config")
    if body and "websocket" in body:
        found.append(f"XIAOZHI {ip} -> {body[:200].replace(chr(10), ' ')}")
    health = http_probe(f"http://{ip}/api/health")
    if health and "STM32" in health:
        found.append(f"STM32 {ip} -> {health[:160]}")
    return found


def main() -> None:
    ips = [f"{SUBNET}.{i}" for i in range(1, 255)]
    with cf.ThreadPoolExecutor(max_workers=120) as pool:
        for results in pool.map(scan, ips):
            for line in results:
                print(line, flush=True)
    print("scan done", flush=True)


if __name__ == "__main__":
    main()
