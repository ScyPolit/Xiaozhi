from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

import httpx

from .config import Config

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LocalIntent:
    kind: str
    action: str
    target: int | None = None


ROOMS = {"客厅": 1, "卧室": 2, "厨房": 3, "卫生间": 4, "梳妆台": 5}


def parse_local_intent(text: str) -> LocalIntent | None:
    normalized = re.sub(r"[，。！？,.!?\s]", "", text.lower())
    if any(word in normalized for word in ("急停", "立即停", "马上停", "停止移动", "停车", "停下", "别动")):
        return LocalIntent("motion", "Stop")
    if any(word in normalized for word in ("跳舞", "舞蹈", "来一段", "扭一扭")):
        return LocalIntent("motion", "Dance")
    for words, method in (
        (("前进", "向前", "往前"), "GoForward"),
        (("后退", "向后", "往后", "倒车"), "GoBack"),
        (("左转", "向左", "往左"), "TurnLeft"),
        (("右转", "向右", "往右"), "TurnRight"),
    ):
        if any(word in normalized for word in words):
            return LocalIntent("motion", method)
    match = re.search(r"灯效(?:模式)?([1-6一二三四五六])", normalized)
    if match:
        values = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}
        target = values.get(match.group(1)) or int(match.group(1))
        return LocalIntent("motion", "SwitchLightMode", target)
    is_on = any(word in normalized for word in ("打开", "开启", "开灯", "启动"))
    is_off = any(word in normalized for word in ("关闭", "关掉", "关灯", "熄灭"))
    if not (is_on or is_off):
        return None
    action = "on" if is_on else "off"
    if "空调" in normalized:
        return LocalIntent("ac", action)
    if any(word in normalized for word in ("所有灯", "全部灯", "全灯")):
        return LocalIntent("all_lights", action)
    for room, led_id in ROOMS.items():
        if room in normalized:
            return LocalIntent("light", action, led_id)
    return None


class DeviceController:
    def __init__(self, config: Config, dashboard: object):
        self.config = config
        self.dashboard = dashboard
        self.client = httpx.AsyncClient(timeout=2.0, trust_env=False)
        self._stop_task: asyncio.Task | None = None

    async def close(self) -> None:
        if self._stop_task and not self._stop_task.done():
            self._stop_task.cancel()
        await self.client.aclose()

    async def execute(self, intent: LocalIntent) -> str:
        if intent.kind == "motion":
            return await self._motion(intent)
        return await self._smart_home(intent)

    async def emergency_stop(self) -> None:
        if self._stop_task and not self._stop_task.done():
            self._stop_task.cancel()
        self._stop_task = None
        await self.dashboard.send_iot_command("Stop")

    async def _motion(self, intent: LocalIntent) -> str:
        method = intent.action
        if method == "Stop":
            await self.emergency_stop()
            return "已停止移动。"
        params = {"speed": 68, "duration_ms": self.config.motion_pulse_ms}
        if method == "SwitchLightMode":
            params = {"lightmode": intent.target or 1}
        ok = await self.dashboard.send_iot_command(method, params)
        if not ok:
            return "底盘当前未连接，动作没有执行。"
        if method in {"GoForward", "GoBack", "TurnLeft", "TurnRight"}:
            if self._stop_task and not self._stop_task.done():
                self._stop_task.cancel()
            self._stop_task = asyncio.create_task(self._stop_after_pulse())
        labels = {"GoForward": "前进", "GoBack": "后退", "TurnLeft": "左转", "TurnRight": "右转", "Dance": "跳舞", "SwitchLightMode": "切换灯效"}
        return f"好的，正在{labels[method]}。"

    async def _stop_after_pulse(self) -> None:
        try:
            await asyncio.sleep(self.config.motion_pulse_ms / 1000)
            await self.dashboard.send_iot_command("Stop")
        except asyncio.CancelledError:
            pass

    async def _smart_home(self, intent: LocalIntent) -> str:
        if intent.kind == "light":
            path = f"/api/led?id={intent.target}&state={intent.action}"
        elif intent.kind == "all_lights":
            path = f"/api/all?state={intent.action}"
        else:
            path = f"/api/ac?state={intent.action}"
        try:
            response = await self.client.get(self.config.smart_home_url + path)
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok", payload.get("success", False)):
                raise RuntimeError(payload.get("error", "device rejected command"))
        except Exception as exc:
            LOGGER.warning("smart-home command failed: %s", exc)
            return "智能家居控制器未连接，指令没有执行。"
        state = "打开" if intent.action == "on" else "关闭"
        if intent.kind == "ac":
            return f"已{state}空调。"
        if intent.kind == "all_lights":
            return f"已{state}全部灯光。"
        room = next((name for name, value in ROOMS.items() if value == intent.target), "指定")
        return f"已{state}{room}灯。"
