from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from pathlib import Path
from typing import Any

import httpx
from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol


DASHBOARD_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Xiaozhi OpenClaw Console</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101214;
      --panel: #181c20;
      --panel-2: #20262b;
      --line: #303840;
      --text: #f0f4f7;
      --muted: #9eabb4;
      --green: #4cc38a;
      --red: #ef6f6c;
      --yellow: #e2b84b;
      --blue: #58a6ff;
      --cyan: #47c7d8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, "Segoe UI", "Microsoft YaHei", sans-serif;
      letter-spacing: 0;
    }
    main { min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: #14181b;
    }
    h1 { margin: 0; font-size: 18px; font-weight: 700; }
    .status-pill {
      min-width: 108px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      color: var(--muted);
      text-align: center;
      font-size: 13px;
    }
    .status-pill.ok { color: var(--green); border-color: #31684d; }
    .grid {
      display: grid;
      grid-template-columns: minmax(300px, 420px) 1fr minmax(300px, 380px);
      gap: 12px;
      padding: 12px;
      min-height: 0;
    }
    section {
      min-height: 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    section > h2 {
      margin: 0;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      font-size: 14px;
      color: #d9e2e8;
    }
    .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 12px; }
    .metric { background: var(--panel-2); border: 1px solid var(--line); border-radius: 6px; padding: 10px; min-height: 72px; }
    .metric label { display: block; color: var(--muted); font-size: 12px; margin-bottom: 8px; }
    .metric strong { display: block; font-size: 20px; overflow-wrap: anywhere; }
    .metric.wide { grid-column: 1 / -1; }
    .green { color: var(--green); } .red { color: var(--red); } .yellow { color: var(--yellow); } .blue { color: var(--blue); }
    .log, .chat { flex: 1; overflow: auto; padding: 12px; min-height: 0; }
    .event { border-bottom: 1px solid #293139; padding: 8px 0; color: #d5dde3; font-size: 13px; }
    .event time { color: var(--muted); margin-right: 8px; font-size: 12px; }
    .bubble { max-width: 86%; margin: 8px 0; padding: 9px 11px; border-radius: 8px; line-height: 1.45; white-space: pre-wrap; }
    .bubble.user { margin-left: auto; background: #1f3d5a; border: 1px solid #2d5d8c; }
    .bubble.assistant { background: #24332b; border: 1px solid #386046; }
    .bubble.system { background: #2b2f35; border: 1px solid #3c454d; color: var(--muted); }
    .composer { display: grid; grid-template-columns: 1fr auto; gap: 8px; padding: 10px; border-top: 1px solid var(--line); }
    textarea, input {
      width: 100%;
      background: #111518;
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px;
      font: inherit;
      min-height: 42px;
    }
    button {
      background: #26313a;
      color: var(--text);
      border: 1px solid #3a4650;
      border-radius: 6px;
      min-height: 42px;
      padding: 0 14px;
      font: inherit;
      cursor: pointer;
    }
    button:hover { border-color: var(--blue); }
    button.primary { background: #1f4a74; border-color: #3679b6; }
    button.danger { background: #68302e; border-color: #9d4641; }
    .controls { padding: 12px; display: grid; gap: 10px; }
    .pad { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .pad button { aspect-ratio: 1.45; }
    .pad .empty { visibility: hidden; }
    .inline { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 13px; }
    pre { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; color: #cdd6dd; font-size: 12px; }
    @media (max-width: 1100px) { .grid { grid-template-columns: 1fr; } section { min-height: 360px; } }
  </style>
</head>
<body>
<main>
  <header>
    <h1>Xiaozhi OpenClaw Console</h1>
    <div id="dashState" class="status-pill">连接中</div>
  </header>
  <div class="grid">
    <section>
      <h2>小智状态</h2>
      <div class="metrics">
        <div class="metric"><label>设备连接</label><strong id="deviceConnected" class="red">离线</strong></div>
        <div class="metric"><label>运动状态</label><strong id="motionState">unknown</strong></div>
        <div class="metric"><label>会话状态</label><strong id="listenState">idle</strong></div>
        <div class="metric"><label>情感</label><strong id="emotionState">neutral</strong></div>
        <div class="metric wide"><label>设备</label><strong id="deviceInfo">等待连接</strong></div>
        <div class="metric wide"><label>最后输入</label><pre id="lastInput"></pre></div>
        <div class="metric wide"><label>最后输出</label><pre id="lastOutput"></pre></div>
      </div>
    </section>
    <section>
      <h2>对话</h2>
      <div id="chat" class="chat"></div>
      <div class="composer">
        <textarea id="chatInput" rows="2" placeholder="输入文字发送给 OpenClaw"></textarea>
        <div style="display:grid;gap:8px;">
          <button id="sendBtn" class="primary">发送</button>
          <label class="inline"><input id="speakOnDevice" type="checkbox"> 小智播报</label>
        </div>
      </div>
    </section>
    <section>
      <h2>OpenClaw 与控制</h2>
      <div class="metrics">
        <div class="metric"><label>OpenClaw</label><strong id="openclawState" class="yellow">待机</strong></div>
        <div class="metric"><label>音频帧</label><strong id="audioFrames">0</strong></div>
      </div>
      <div class="controls">
        <div class="pad">
          <button class="empty"></button>
          <button data-move="GoForward">前进</button>
          <button class="empty"></button>
          <button data-move="TurnLeft">左转</button>
          <button class="danger" data-command="Stop">停止</button>
          <button data-move="TurnRight">右转</button>
          <button class="empty"></button>
          <button data-move="GoBack">后退</button>
          <button class="empty"></button>
        </div>
        <button id="wakeBtn" class="primary">唤醒会话</button>
        <button data-command="Dance">跳舞</button>
        <button id="abortBtn" class="danger">打断输出</button>
      </div>
      <h2>事件</h2>
      <div id="events" class="log"></div>
    </section>
  </div>
</main>
<script>
const state = { ws: null, assistantDraft: "" };
const $ = (id) => document.getElementById(id);
function addBubble(role, text) {
  const el = document.createElement("div");
  el.className = `bubble ${role}`;
  el.textContent = text;
  $("chat").appendChild(el);
  $("chat").scrollTop = $("chat").scrollHeight;
  return el;
}
function addEvent(e) {
  const row = document.createElement("div");
  row.className = "event";
  const t = new Date((e.ts || Date.now()/1000) * 1000).toLocaleTimeString();
  row.innerHTML = `<time>${t}</time>${escapeHtml(e.message || JSON.stringify(e))}`;
  $("events").prepend(row);
  while ($("events").children.length > 80) $("events").lastChild.remove();
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function send(payload) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) state.ws.send(JSON.stringify(payload));
}
function directRocker(method) {
  const table = {
    GoForward: {x: 0, y: 100},
    GoBack: {x: 0, y: -100},
    TurnLeft: {x: -100, y: 0},
    TurnRight: {x: 100, y: 0},
    Stop: {x: 0, y: 0}
  };
  const body = table[method];
  if (!body) return;
  fetch(`http://${$("deviceInfo").textContent.split(" / ")[1] || "192.168.31.219"}/rocker_data`, {
    method: "POST",
    headers: {"Content-Type": "text/plain"},
    body: JSON.stringify(body)
  }).catch(() => {});
}
async function directChatAction(action) {
  try {
    const host = $("deviceInfo").textContent.split(" / ")[1] || "192.168.31.219";
    const r = await fetch(`http://${host}/xiaozhi_chat`, {
      method: "POST",
      headers: {"Content-Type": "text/plain"},
      body: JSON.stringify({action})
    });
    addEvent({message: r.ok ? `已请求小智${action}会话` : `小智会话请求失败 ${r.status}`});
    return r.ok;
  } catch (e) {
    addEvent({message: `小智会话请求失败: ${e.message || e}`});
    return false;
  }
}
function directHealth() {
  fetch("http://192.168.31.219/xiaozhi_config", {cache: "no-store"})
    .then(r => {
      $("deviceConnected").dataset.browserOnline = r.ok ? "true" : "false";
      if (!$("deviceConnected").textContent.includes("session")) {
        setText("deviceConnected", r.ok ? "standby" : "offline");
        $("deviceConnected").className = r.ok ? "green" : "red";
      }
    })
    .catch(() => {
      $("deviceConnected").dataset.browserOnline = "false";
    });
}
function setText(id, text) { $(id).textContent = text ?? ""; }
function applySnapshot(s) {
  $("dashState").className = "status-pill ok";
  setText("dashState", "connected");
  const browserOnline = $("deviceConnected").dataset.browserOnline === "true";
  const deviceLabel = s.device.connected ? "session" : ((s.device.http_online || browserOnline) ? "standby" : "offline");
  setText("deviceConnected", deviceLabel);
  $("deviceConnected").className = (s.device.connected || s.device.http_online || browserOnline) ? "green" : "red";
  setText("motionState", s.device.motion_state || "unknown");
  setText("listenState", s.device.listen_state || "idle");
  setText("emotionState", s.openclaw.emotion || "neutral");
  setText("deviceInfo", `${s.device.device_id || "unknown"} / ${s.device.ip || ""}`);
  setText("lastInput", s.openclaw.last_input || "");
  setText("lastOutput", s.openclaw.last_output || "");
  setText("openclawState", s.openclaw.busy ? "busy" : "idle");
  $("openclawState").className = s.openclaw.busy ? "green" : "yellow";
  setText("audioFrames", s.openclaw.audio_frames || 0);
}
function handleMessage(msg) {
  if (msg.type === "snapshot") {
    applySnapshot(msg);
    (msg.events || []).forEach(addEvent);
  } else if (msg.type === "state") {
    applySnapshot(msg.snapshot);
  } else if (msg.type === "event") {
    addEvent(msg.event);
  } else if (msg.type === "chat") {
    addBubble(msg.role || "system", msg.text || "");
  } else if (msg.type === "openclaw_delta") {
    state.assistantDraft += msg.text || "";
    setText("lastOutput", state.assistantDraft);
  } else if (msg.type === "openclaw_done") {
    if (msg.text) addBubble("assistant", msg.text);
    state.assistantDraft = "";
  }
}
function connect() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  state.ws = new WebSocket(`${proto}//${location.host}/dashboard/ws`);
  state.ws.onopen = () => { $("dashState").className = "status-pill ok"; setText("dashState", "connected"); };
  state.ws.onmessage = (ev) => handleMessage(JSON.parse(ev.data));
  state.ws.onclose = () => {
    $("dashState").className = "status-pill";
    setText("dashState", "reconnecting");
    setTimeout(connect, 1000);
  };
}
$("sendBtn").onclick = async () => {
  const text = $("chatInput").value.trim();
  if (!text) return;
  addBubble("user", text);
  $("chatInput").value = "";
  if ($("speakOnDevice").checked && $("deviceConnected").textContent !== "session") {
    await directChatAction("start");
  }
  send({type: "chat", text, speak: $("speakOnDevice").checked});
};
$("wakeBtn").onclick = () => directChatAction("start");
$("abortBtn").onclick = () => send({type: "abort"});
document.querySelectorAll("[data-command]").forEach(btn => {
  btn.onclick = () => {
    send({type: "control", method: btn.dataset.command});
    directRocker(btn.dataset.command);
  };
});
document.querySelectorAll("[data-move]").forEach(btn => {
  let timer = null;
  const start = (event) => {
    event.preventDefault();
    if (timer) return;
    send({type: "control", method: btn.dataset.move, parameters: {speed: 70, duration_ms: 120}});
    timer = setTimeout(stop, 150);
  };
  const stop = () => {
    if (timer) clearTimeout(timer);
    timer = null;
    send({type: "control", method: "Stop"});
  };
  btn.addEventListener("pointerdown", start);
  btn.addEventListener("pointerup", stop);
  btn.addEventListener("pointerleave", stop);
  btn.addEventListener("pointercancel", stop);
});
connect();
directHealth();
setInterval(directHealth, 5000);
</script>
</body>
</html>
"""


class DashboardState:
    def __init__(self, xiaozhi_ip: str):
        self.xiaozhi_ip = xiaozhi_ip
        self.device_session: Any | None = None
        self.clients: set[WebSocketServerProtocol] = set()
        self.events: deque[dict[str, Any]] = deque(maxlen=100)
        self.conversation: list[dict[str, str]] = []
        self.descriptors: list[dict[str, Any]] = []
        self.states: list[dict[str, Any]] = []
        self.device: dict[str, Any] = {
            "connected": False,
            "http_online": False,
            "device_id": "",
            "client_id": "",
            "ip": xiaozhi_ip,
            "listen_state": "idle",
            "motion_state": "unknown",
        }
        self.openclaw: dict[str, Any] = {
            "busy": False,
            "emotion": "neutral",
            "last_input": "",
            "last_output": "",
            "audio_frames": 0,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "type": "snapshot",
            "device": self.device,
            "openclaw": self.openclaw,
            "descriptors": self.descriptors,
            "states": self.states,
            "events": list(self.events)[-40:],
        }

    async def add_client(self, websocket: WebSocketServerProtocol) -> None:
        self.clients.add(websocket)
        await websocket.send(json.dumps(self.snapshot(), ensure_ascii=False))

    def remove_client(self, websocket: WebSocketServerProtocol) -> None:
        self.clients.discard(websocket)

    async def log(self, message: str, **extra: Any) -> None:
        event = {"ts": time.time(), "message": message, **extra}
        self.events.append(event)
        await self.broadcast({"type": "event", "event": event})

    async def broadcast_state(self) -> None:
        await self.broadcast({"type": "state", "snapshot": self.snapshot()})

    async def broadcast_chat(self, role: str, text: str) -> None:
        await self.broadcast({"type": "chat", "role": role, "text": text})

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self.clients:
            return
        data = json.dumps(payload, ensure_ascii=False)
        stale: list[WebSocketServerProtocol] = []
        for client in self.clients:
            try:
                await client.send(data)
            except ConnectionClosed:
                stale.append(client)
        for client in stale:
            self.remove_client(client)

    async def on_device_connected(self, session: Any) -> None:
        self.device_session = session
        remote = session.websocket.remote_address
        remote_ip = remote[0] if isinstance(remote, tuple) and remote else self.xiaozhi_ip
        self.device.update(
            {
                "connected": True,
                "device_id": session.device_id,
                "client_id": session.client_id,
                "ip": remote_ip,
                "listen_state": "connected",
            }
        )
        await self.log(f"小智已连接: {session.device_id}")
        await self.broadcast_state()

    async def on_device_disconnected(self, session: Any) -> None:
        if self.device_session is session:
            self.device_session = None
            self.device["connected"] = False
            self.device["listen_state"] = "offline"
        await self.log("小智已断开")
        await self.broadcast_state()

    async def set_listen_state(self, value: str) -> None:
        self.device["listen_state"] = value
        await self.broadcast_state()

    async def set_emotion(self, value: str) -> None:
        self.openclaw["emotion"] = value
        await self.broadcast_state()

    async def set_busy(self, value: bool) -> None:
        self.openclaw["busy"] = value
        await self.broadcast_state()

    async def set_last_input(self, text: str) -> None:
        self.openclaw["last_input"] = text
        await self.broadcast_state()

    async def set_last_output(self, text: str) -> None:
        self.openclaw["last_output"] = text
        await self.broadcast_state()

    async def add_audio_frame(self) -> None:
        self.openclaw["audio_frames"] = int(self.openclaw.get("audio_frames") or 0) + 1
        if self.openclaw["audio_frames"] % 10 == 0:
            await self.broadcast_state()

    async def on_iot_message(self, payload: dict[str, Any]) -> None:
        if "descriptors" in payload:
            for descriptor in payload.get("descriptors") or []:
                name = descriptor.get("name")
                self.descriptors = [item for item in self.descriptors if item.get("name") != name]
                self.descriptors.append(descriptor)
            await self.log("收到 IOT 能力描述")
        if "states" in payload:
            for state in payload.get("states") or []:
                name = state.get("name")
                self.states = [item for item in self.states if item.get("name") != name]
                self.states.append(state)
                if name == "Chassis":
                    data = state.get("state") or {}
                    self.device["motion_state"] = data.get("motion_state", self.device["motion_state"])
            await self.log("收到 IOT 状态更新")
        await self.broadcast_state()

    async def send_iot_command(self, method: str, parameters: dict[str, Any] | None = None) -> bool:
        if not self.device_session:
            await self.log("控制失败: 小智未连接")
            return False

        parameters = parameters or {}
        rocker = {
            "GoForward": (0, 1),
            "GoBack": (0, -1),
            "TurnLeft": (-1, 0),
            "TurnRight": (1, 0),
            "Stop": (0, 0),
        }
        if method in rocker:
            speed = max(20, min(int(parameters.get("speed", 70)), 75))
            direction_x, direction_y = rocker[method]
            if method == "Stop":
                ok = await self._send_rocker(0, 0)
            else:
                duration_ms = max(80, min(int(parameters.get("duration_ms", 120)), 180))
                ok = await self._send_rocker(direction_x * speed, direction_y * speed)
                if ok:
                    asyncio.create_task(
                        self._pulse_rocker(
                            direction_x * speed,
                            direction_y * speed,
                            duration_ms / 1000,
                        )
                    )
            if not ok:
                await self.log(f"小车 HTTP 控制失败: {method}")
                return False
        else:
            await self.device_session.send_json(
                {
                    "type": "iot",
                    "commands": [
                        {
                            "name": "Chassis",
                            "method": method,
                            "parameters": parameters,
                        }
                    ],
                }
            )
        self.device["motion_state"] = "stopped" if method == "Stop" else method
        await self.log(f"发送小车控制: {method}")
        await self.broadcast_state()
        return True

    async def _send_rocker(self, x: int, y: int) -> bool:
        device_ip = self.device.get("ip") or self.xiaozhi_ip
        try:
            async with httpx.AsyncClient(timeout=2.0, trust_env=False) as client:
                response = await client.post(
                    f"http://{device_ip}/rocker_data",
                    json={"x": x, "y": y},
                )
            return 200 <= response.status_code < 300
        except Exception:
            return False

    async def _pulse_rocker(self, x: int, y: int, duration: float) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + duration
        while loop.time() + 0.04 < deadline:
            await asyncio.sleep(0.04)
            await self._send_rocker(x, y)
        await self._send_rocker(0, 0)
        await asyncio.sleep(0.03)
        await self._send_rocker(0, 0)
        self.device["motion_state"] = "stopped"
        await self.broadcast_state()

    async def abort_device(self) -> None:
        if self.device_session:
            await self.device_session.abort()
            await self.log("已请求打断小智输出")


async def send_dashboard_html() -> tuple[int, list[tuple[str, str]], bytes]:
    static_path = Path(__file__).with_name("dashboard.html")
    if static_path.exists():
        return (
            200,
            [("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-store")],
            static_path.read_bytes(),
        )
    return (
        200,
        [("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-store")],
        DASHBOARD_HTML.encode("utf-8"),
    )
