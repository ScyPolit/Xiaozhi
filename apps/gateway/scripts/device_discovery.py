from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import socket
import urllib.request

import psutil


TOKEN = "test-token"
PORT = 8000
INTERVAL_SECONDS = 30
LOGGER = logging.getLogger("zhihe-device-discovery")


def local_ipv4_networks() -> list[tuple[str, ipaddress.IPv4Network]]:
    networks: list[tuple[str, ipaddress.IPv4Network]] = []
    for addresses in psutil.net_if_addrs().values():
        for item in addresses:
            if item.family != socket.AF_INET or not item.netmask:
                continue
            address = ipaddress.ip_address(item.address)
            if address.is_private and not address.is_loopback and not address.is_link_local:
                network = ipaddress.ip_network(f"{item.address}/{item.netmask}", strict=False)
                if network.num_addresses <= 1024:
                    networks.append((item.address, network))
    # Windows Mobile Hotspot normally uses this network even before a client joins.
    networks.append(("192.168.137.1", ipaddress.ip_network("192.168.137.0/24")))
    return list(dict.fromkeys(networks))


def get_json(url: str, timeout: float = 0.35) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read(4096).decode("utf-8"))
    except Exception:
        return None


def configure_xiaozhi(ip: str, gateway_ip: str, current: dict) -> None:
    expected_url = f"ws://{gateway_ip}:{PORT}/xiaozhi/v1/"
    if current.get("websocket_url") == expected_url and current.get("websocket_token") == TOKEN:
        return
    request = urllib.request.Request(
        f"http://{ip}/xiaozhi_config",
        data=json.dumps({"websocket_url": expected_url, "websocket_token": TOKEN}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        response.read()
    LOGGER.info("configured Xiaozhi %s -> %s", ip, expected_url)


async def probe(ip: str, gateway_ip: str) -> None:
    current = await asyncio.to_thread(get_json, f"http://{ip}/xiaozhi_config")
    if current and "websocket_url" in current:
        try:
            await asyncio.to_thread(configure_xiaozhi, ip, gateway_ip, current)
        except Exception as exc:
            LOGGER.warning("cannot configure Xiaozhi %s: %s", ip, exc)
        return
    health = await asyncio.to_thread(get_json, f"http://{ip}/api/health")
    if health and health.get("device") == "STM32F103C8T6":
        LOGGER.info("smart-home STM32 online at %s", ip)


async def scan_once() -> None:
    for gateway_ip, network in local_ipv4_networks():
        tasks = [probe(str(ip), gateway_ip) for ip in network.hosts() if str(ip) != gateway_ip]
        await asyncio.gather(*tasks)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    while True:
        await scan_once()
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
