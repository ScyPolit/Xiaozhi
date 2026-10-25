from __future__ import annotations

import asyncio
import json
import logging
import re
import signal
from dataclasses import dataclass, field
from typing import Any

import httpx
from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol, serve

from .audio import AudioBridge
from .config import Config, load_config
from .dashboard import DashboardState, send_dashboard_html
from .device_control import DeviceController, parse_local_intent
from .openclaw import OpenClawClient
from .tools import ToolClient, with_tool_context

LOGGER = logging.getLogger(__name__)

SENTENCE_ENDINGS = set("。！？!?；;")
WAKE_ACK_TEXT = "我在，请说。"
THINKING_ACK_TEXT = "我正在思考。"
LONG_THINKING_TEXTS = (
    "这个任务有点复杂，我还在处理。",
    "我没有下线，正在继续分析。",
    "我在分步骤推理，马上继续。",
)
MARKDOWN_RE = re.compile(r"[*_`#>\[\]()]")
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U00002600-\U000026FF"
    "]+",
    flags=re.UNICODE,
)


def clean_voice_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.fullmatch(r"[-|\s:]+", stripped):
            continue
        stripped = re.sub(r"^\s*[-+]\s+", "", stripped)
        stripped = stripped.replace("|", "，")
        lines.append(stripped)
    text = " ".join(lines)
    text = MARKDOWN_RE.sub("", text)
    text = EMOJI_RE.sub("", text)
    text = re.sub(r"-{2,}", "，", text)
    return re.sub(r"\s+", " ", text).strip()


def infer_emotion(text: str) -> str:
    lowered = text.lower()
    if any(token in text for token in ("开心", "太好了", "哈哈", "喜欢", "棒", "好呀")):
        return "happy"
    if any(token in text for token in ("抱歉", "难过", "遗憾", "对不起")):
        return "sad"
    if any(token in text for token in ("让我想想", "可能", "也许", "分析")) or "?" in lowered:
        return "thinking"
    return "neutral"


@dataclass
class Session:
    websocket: WebSocketServerProtocol
    config: Config
    dashboard: DashboardState
    llm: OpenClawClient
    audio: AudioBridge
    tools: ToolClient
    controller: DeviceController
    device_id: str = "unknown"
    client_id: str = "unknown"
    listening: bool = False
    opus_packets: list[bytes] = field(default_factory=list)
    response_task: asyncio.Task | None = None
    conversation: list[dict[str, str]] = field(default_factory=list)
    tts_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def close(self) -> None:
        await self.abort(send_stop=False)
        await self.llm.close()
        await self.tools.close()
        await self.controller.close()

    async def abort(self, send_stop: bool = True) -> None:
        if self.response_task and not self.response_task.done():
            self.response_task.cancel()
            try:
                await self.response_task
            except asyncio.CancelledError:
                pass
        self.response_task = None
        if send_stop:
            await self.send_json({"type": "tts", "state": "stop"})
        await self.dashboard.set_busy(False)
        await self.dashboard.set_listen_state("ready")

    async def send_json(self, payload: dict[str, Any]) -> None:
        try:
            await self.websocket.send(json.dumps(payload, ensure_ascii=False))
        except ConnectionClosed:
            LOGGER.debug("skip json send after close: %s", payload)

    async def handle_json(self, payload: dict[str, Any]) -> None:
        kind = payload.get("type")
        if kind == "hello":
            params = payload.get("audio_params", {})
            LOGGER.info("hello from %s audio=%s", self.device_id, params)
            await self.send_json(
                {
                    "type": "hello",
                    "transport": "websocket",
                    "audio_params": {"sample_rate": self.config.sample_rate},
                }
            )
            await self.dashboard.set_listen_state("ready")
            return

        if kind == "listen":
            await self._handle_listen(payload)
            return

        if kind == "abort":
            LOGGER.info("abort from %s reason=%s", self.device_id, payload.get("reason"))
            await self.dashboard.log(f"小智打断: {payload.get('reason', '')}")
            await self.abort()
            return

        if kind == "iot":
            LOGGER.info("iot message from %s: %s", self.device_id, payload)
            await self.dashboard.on_iot_message(payload)
            return

        LOGGER.info("unhandled json from %s: %s", self.device_id, payload)

    async def handle_audio(self, data: bytes) -> None:
        if self.listening:
            self.opus_packets.append(data)

    async def _handle_listen(self, payload: dict[str, Any]) -> None:
        state = payload.get("state")
        if state == "start":
            await self.abort(send_stop=False)
            self.listening = True
            self.opus_packets.clear()
            await self.dashboard.set_listen_state("listening")
            await self.dashboard.log(f"开始收音: {payload.get('mode', 'manual')}")
            return

        if state == "detect":
            text = str(payload.get("text") or "").strip()
            await self.dashboard.set_listen_state("wake")
            await self.dashboard.log(f"唤醒词: {text}")
            await self.dashboard.set_last_input(text)
            await self.send_json({"type": "stt", "text": text})
            self.response_task = asyncio.create_task(self.wake_ack())
            return

        if state == "stop":
            self.listening = False
            packets = list(self.opus_packets)
            self.opus_packets.clear()
            await self.dashboard.set_listen_state("recognizing")
            LOGGER.info("listen stop from %s packets=%d", self.device_id, len(packets))
            user_text = str(payload.get("text") or payload.get("test_text") or "").strip()
            if not user_text:
                user_text = await self.audio.recognize(packets)
            if not user_text:
                await self.send_json({"type": "stt", "text": ""})
                await self.send_json({"type": "tts", "state": "stop"})
                await self.dashboard.set_listen_state("ready")
                await self.dashboard.log("没有识别到有效语音")
                return
            await self.send_json({"type": "stt", "text": user_text})
            await self.dashboard.set_last_input(user_text)
            await self.dashboard.broadcast_chat("user", user_text)
            self.response_task = asyncio.create_task(self.respond(user_text))
            return

    async def wake_ack(self) -> None:
        LOGGER.info("wake ack for %s", self.device_id)
        await self.dashboard.set_busy(True)
        await self.dashboard.set_emotion("happy")
        await self.dashboard.set_last_output(WAKE_ACK_TEXT)
        await self.dashboard.broadcast_chat("assistant", WAKE_ACK_TEXT)
        try:
            await self.send_json({"type": "llm", "emotion": "happy"})
            await self.send_json({"type": "tts", "state": "start"})
            await self._send_sentence(WAKE_ACK_TEXT, emotion_override="happy")
        except asyncio.CancelledError:
            LOGGER.info("wake ack cancelled for %s", self.device_id)
            raise
        finally:
            await self.send_json({"type": "tts", "state": "stop"})
            await self.dashboard.set_busy(False)
            await self.dashboard.set_emotion("neutral")
            await self.dashboard.set_listen_state("ready")

    async def respond(self, user_text: str) -> None:
        LOGGER.info("STT %s: %s", self.device_id, user_text)
        await self.dashboard.set_busy(True)
        await self.dashboard.set_emotion("thinking")
        await self.send_json({"type": "llm", "emotion": "thinking"})
        await self.send_json({"type": "tts", "state": "start"})

        chunks: list[str] = []
        full_reply: list[str] = []
        first_reply_seen = asyncio.Event()
        progress_task = asyncio.create_task(self._thinking_progress(first_reply_seen))
        try:
            local_intent = parse_local_intent(user_text)
            if local_intent:
                first_reply_seen.set()
                reply = await self.controller.execute(local_intent)
                full_reply.append(reply)
                await self._send_sentence(reply)
                self._remember_turn(user_text, reply)
                await self.dashboard.set_last_output(reply)
                await self.dashboard.broadcast({"type": "openclaw_done", "text": reply})
                return
            tool_context = await self.tools.collect_context(user_text)
            if tool_context:
                await self.dashboard.log("已调用电脑工具")
            prompt_text = with_tool_context(user_text, tool_context)
            history = self.conversation or getattr(self.dashboard, "conversation", [])
            tts_tasks: list[asyncio.Task] = []
            async for chunk in self.llm.chat(prompt_text, history):
                first_reply_seen.set()
                chunks.append(chunk)
                full_reply.append(chunk)
                display_chunk = clean_voice_text(chunk)
                if display_chunk:
                    await self.send_json({"type": "llm", "text_delta": display_chunk})
                    await self.dashboard.broadcast({"type": "openclaw_delta", "text": display_chunk})
                sentence = "".join(chunks).strip()
                if sentence and (sentence[-1] in SENTENCE_ENDINGS or len(sentence) >= 20):
                    tts_tasks.append(asyncio.create_task(self._send_sentence(sentence)))
                    chunks.clear()
            rest = "".join(chunks).strip()
            if rest:
                tts_tasks.append(asyncio.create_task(self._send_sentence(rest)))
            if tts_tasks:
                await asyncio.gather(*tts_tasks)
            reply = clean_voice_text("".join(full_reply).strip())
            if reply:
                self._remember_turn(user_text, reply)
            await self.dashboard.set_last_output(reply)
            await self.dashboard.broadcast({"type": "openclaw_done", "text": reply})
            await self.dashboard.set_emotion("neutral")
            await self.send_json({"type": "llm", "emotion": "neutral"})
        except asyncio.CancelledError:
            LOGGER.info("response cancelled for %s", self.device_id)
            await self.dashboard.log("输出已打断")
            raise
        except Exception as exc:
            LOGGER.exception("response failed for %s: %s", self.device_id, exc)
            reply = "模型服务暂时不可用，但移动和灯光控制仍可正常使用。"
            await self.send_json({"type": "llm", "emotion": "sad"})
            await self._send_sentence(reply, emotion_override="sad")
            await self.dashboard.set_last_output(reply)
            await self.dashboard.broadcast({"type": "openclaw_done", "text": reply})
            await self.dashboard.log(f"OpenClaw 响应失败: {exc}")
        finally:
            first_reply_seen.set()
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
            await self.send_json({"type": "tts", "state": "stop"})
            await self.dashboard.set_busy(False)
            await self.dashboard.set_listen_state("ready")
            LOGGER.info("TTS stop for %s", self.device_id)

    async def _thinking_progress(self, first_reply_seen: asyncio.Event) -> None:
        try:
            await asyncio.wait_for(first_reply_seen.wait(), timeout=1.1)
            return
        except asyncio.TimeoutError:
            pass

        await self.dashboard.log("OpenClaw 正在思考")
        await self.dashboard.set_last_output(THINKING_ACK_TEXT)
        await self.dashboard.broadcast({"type": "openclaw_delta", "text": THINKING_ACK_TEXT})
        await self.send_json({"type": "llm", "text_delta": THINKING_ACK_TEXT})

        index = 0
        while not first_reply_seen.is_set():
            try:
                await asyncio.wait_for(first_reply_seen.wait(), timeout=7.0)
                return
            except asyncio.TimeoutError:
                text = LONG_THINKING_TEXTS[index % len(LONG_THINKING_TEXTS)]
                index += 1
                await self.dashboard.log(text)
                await self.dashboard.set_last_output(text)
                await self.dashboard.broadcast({"type": "openclaw_delta", "text": text})
                await self.send_json({"type": "llm", "text_delta": text})

    def _remember_turn(self, user_text: str, assistant_text: str) -> None:
        self.conversation.append({"role": "user", "content": user_text})
        self.conversation.append({"role": "assistant", "content": assistant_text})
        if len(self.conversation) > 12:
            self.conversation = self.conversation[-12:]
        self.dashboard.conversation = list(self.conversation)

    async def _send_sentence(self, sentence: str, emotion_override: str | None = None) -> None:
        async with self.tts_lock:
            sentence = clean_voice_text(sentence)
            if not sentence:
                return
            emotion = emotion_override or infer_emotion(sentence)
            LOGGER.info("OpenClaw reply %s: %s", self.device_id, sentence)
            await self.dashboard.set_emotion(emotion)
            await self.send_json({"type": "llm", "emotion": emotion})
            await self.send_json({"type": "tts", "state": "sentence_start", "text": sentence})
            packets = await self.audio.synthesize_opus(sentence)
            for packet in packets:
                try:
                    await self.websocket.send(packet)
                    await self.dashboard.add_audio_frame()
                except ConnectionClosed:
                    return
                await asyncio.sleep(self.config.frame_ms / 1000)


def _token_valid(protocol: WebSocketServerProtocol, config: Config) -> bool:
    if not config.access_token:
        return True
    auth = protocol.request_headers.get("Authorization", "")
    return auth == f"Bearer {config.access_token}"


async def xiaozhi_handler(websocket: WebSocketServerProtocol, path: str, config: Config, dashboard: DashboardState) -> None:
    if not _token_valid(websocket, config):
        await websocket.close(code=1008, reason="invalid token")
        return

    session = Session(
        websocket=websocket,
        config=config,
        dashboard=dashboard,
        llm=OpenClawClient(config),
        audio=AudioBridge(config),
        tools=ToolClient(config),
        controller=DeviceController(config, dashboard),
        device_id=websocket.request_headers.get("Device-Id", "unknown"),
        client_id=websocket.request_headers.get("Client-Id", "unknown"),
    )
    LOGGER.info("device connected device=%s client=%s path=%s", session.device_id, session.client_id, path)
    await dashboard.on_device_connected(session)
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                await session.handle_audio(message)
                continue
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                LOGGER.warning("bad json from %s: %s", session.device_id, message[:200])
                continue
            await session.handle_json(payload)
    except ConnectionClosed:
        pass
    finally:
        LOGGER.info("device disconnected device=%s", session.device_id)
        await dashboard.on_device_disconnected(session)
        await session.close()


async def trigger_xiaozhi_chat(config: Config, dashboard: DashboardState, action: str = "start") -> bool:
    if not config.xiaozhi_ip:
        return False
    url = f"http://{config.xiaozhi_ip}/xiaozhi_chat"
    try:
        async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
            response = await client.post(url, json={"action": action})
        ok = 200 <= response.status_code < 300
        await dashboard.log(f"已请求小智{action}会话" if ok else f"请求小智会话失败: HTTP {response.status_code}")
        return ok
    except Exception as exc:
        await dashboard.log(f"请求小智会话失败: {exc}")
        return False


async def wait_for_device_session(dashboard: DashboardState, timeout: float = 8.0) -> Any | None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if dashboard.device_session:
            return dashboard.device_session
        await asyncio.sleep(0.25)
    return dashboard.device_session


async def dashboard_chat(text: str, speak: bool, config: Config, dashboard: DashboardState) -> None:
    await dashboard.set_busy(True)
    await dashboard.set_last_input(text)
    await dashboard.broadcast_chat("user", text)
    if speak:
        session = dashboard.device_session
        if not session:
            await trigger_xiaozhi_chat(config, dashboard, "start")
            session = await wait_for_device_session(dashboard)
        if session:
            session.response_task = asyncio.create_task(session.respond(text))
            return
        await dashboard.log("小智未进入语音会话，本次改为只在大屏显示文字回复")

    client = OpenClawClient(config)
    tools = ToolClient(config)
    chunks: list[str] = []
    try:
        tool_context = await tools.collect_context(text)
        if tool_context:
            await dashboard.log("已调用电脑工具")
        prompt_text = with_tool_context(text, tool_context)
        async for chunk in client.chat(prompt_text, dashboard.conversation):
            chunks.append(chunk)
            await dashboard.broadcast({"type": "openclaw_delta", "text": clean_voice_text(chunk)})
        reply = clean_voice_text("".join(chunks).strip())
        if reply:
            dashboard.conversation.extend(
                [
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": reply},
                ]
            )
            dashboard.conversation = dashboard.conversation[-12:]
        await dashboard.set_last_output(reply)
        await dashboard.broadcast({"type": "openclaw_done", "text": reply})
    except Exception as exc:
        await dashboard.log(f"文字聊天失败: {exc}")
    finally:
        await client.close()
        await tools.close()
        await dashboard.set_busy(False)


async def dashboard_handler(websocket: WebSocketServerProtocol, config: Config, dashboard: DashboardState) -> None:
    await dashboard.add_client(websocket)
    try:
        async for message in websocket:
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                continue
            kind = payload.get("type")
            if kind == "chat":
                text = str(payload.get("text") or "").strip()
                if text:
                    asyncio.create_task(dashboard_chat(text, bool(payload.get("speak")), config, dashboard))
            elif kind == "control":
                method = str(payload.get("method") or "Stop")
                params = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
                await dashboard.send_iot_command(method, params)
            elif kind == "abort":
                await dashboard.abort_device()
    except ConnectionClosed:
        pass
    finally:
        dashboard.remove_client(websocket)


async def websocket_handler(websocket: WebSocketServerProtocol, path: str, config: Config, dashboard: DashboardState) -> None:
    route = path.split("?", 1)[0].rstrip("/")
    if route == "/xiaozhi/v1":
        await xiaozhi_handler(websocket, path, config, dashboard)
    elif route == "/dashboard/ws":
        await dashboard_handler(websocket, config, dashboard)
    else:
        await websocket.close(code=1008, reason="unsupported path")


def json_response(payload: dict[str, Any]) -> tuple[int, list[tuple[str, str]], bytes]:
    return 200, [("Content-Type", "application/json; charset=utf-8"), ("Cache-Control", "no-store")], (
        json.dumps(payload, ensure_ascii=False) + "\n"
    ).encode("utf-8")


async def process_request(
    path: str, request_headers: Any, dashboard: DashboardState
) -> tuple[int, list[tuple[str, str]], bytes] | None:
    route = path.split("?", 1)[0]
    if route == "/health":
        return json_response({"ok": True, "device_connected": dashboard.device["connected"]})
    if route == "/state":
        return json_response(dashboard.snapshot())
    if route in ("/", "/dashboard"):
        return await send_dashboard_html()
    return None


async def poll_xiaozhi_device(config: Config, dashboard: DashboardState, stop_event: asyncio.Event) -> None:
    if not config.xiaozhi_ip:
        return
    url = f"http://{config.xiaozhi_ip}/xiaozhi_config"
    async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
        last_online: bool | None = None
        while not stop_event.is_set():
            online = False
            try:
                response = await client.get(url)
                online = response.status_code == 200
            except Exception:
                online = False
            if online != last_online:
                dashboard.device["http_online"] = online
                await dashboard.log("小智 HTTP 在线" if online else "小智 HTTP 离线")
                await dashboard.broadcast_state()
                last_online = online
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass


async def async_main() -> None:
    config = load_config()
    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    dashboard = DashboardState(config.xiaozhi_ip)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            pass

    poll_task = asyncio.create_task(poll_xiaozhi_device(config, dashboard, stop_event))
    handler = lambda ws, path: websocket_handler(ws, path, config, dashboard)
    process = lambda path, headers: process_request(path, headers, dashboard)
    async with serve(handler, config.host, config.port, process_request=process, max_size=4 * 1024 * 1024):
        LOGGER.info("gateway listening on %s:%d", config.host, config.port)
        LOGGER.info("dashboard: http://<host>:%d/", config.port)
        LOGGER.info("SparkBot WebSocket URL: ws://<host>:%d/xiaozhi/v1/", config.port)
        await stop_event.wait()
    poll_task.cancel()


def main() -> None:
    asyncio.run(async_main())
