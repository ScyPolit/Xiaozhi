from __future__ import annotations

import argparse
import asyncio
import logging


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        writer.close()
        await writer.wait_closed()


async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    target_host: str,
    target_port: int,
) -> None:
    peer = client_writer.get_extra_info("peername")
    logging.info("proxy accepted %s", peer)
    try:
        target_reader, target_writer = await asyncio.open_connection(target_host, target_port)
    except Exception as exc:
        logging.error("proxy target connection failed: %s", exc)
        client_writer.close()
        await client_writer.wait_closed()
        return

    await asyncio.gather(
        pipe(client_reader, target_writer),
        pipe(target_reader, client_writer),
        return_exceptions=True,
    )
    logging.info("proxy closed %s", peer)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Small TCP proxy for Xiaozhi gateway bridging.")
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--listen-port", type=int, default=8000)
    parser.add_argument("--target-host", default="192.168.31.163")
    parser.add_argument("--target-port", type=int, default=8000)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, args.target_host, args.target_port),
        args.listen_host,
        args.listen_port,
    )
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    logging.info("proxy listening on %s -> %s:%d", addrs, args.target_host, args.target_port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
