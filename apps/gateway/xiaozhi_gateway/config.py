from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    access_token: str
    openclaw_base_url: str
    openclaw_api_key: str
    openclaw_model: str
    reasoning_effort: str
    max_output_tokens: int
    max_reply_chars: int
    system_prompt: str
    stt_command: str
    tts_command: str
    fallback_stt_text: str
    sample_rate: int
    channels: int
    frame_ms: int
    log_level: str
    xiaozhi_ip: str
    tool_bridge_url: str
    smart_home_url: str
    motion_pulse_ms: int


def load_config() -> Config:
    load_dotenv()
    return Config(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        access_token=os.getenv("ACCESS_TOKEN", "test-token"),
        openclaw_base_url=os.getenv("OPENCLAW_BASE_URL", "http://127.0.0.1:18789/v1").rstrip("/"),
        openclaw_api_key=os.getenv("OPENCLAW_API_KEY", "local"),
        openclaw_model=os.getenv("OPENCLAW_MODEL", "glm-5.2"),
        reasoning_effort=os.getenv("OPENCLAW_REASONING_EFFORT", "medium"),
        max_output_tokens=max(256, min(int(os.getenv("MAX_OUTPUT_TOKENS", "1024")), 4096)),
        max_reply_chars=max(80, min(int(os.getenv("MAX_REPLY_CHARS", "360")), 1000)),
        system_prompt=os.getenv(
            "SYSTEM_PROMPT",
            "你是桌面机器人小智。使用自然、简洁的中文口语回答，先说结论。"
            "默认不超过120个汉字，复杂问题不超过三点。不要输出Markdown、表格、代码块、表情或内部推理。"
            "涉及移动、跳舞、灯光等动作时，优先确认执行结果，不要虚构设备状态。",
        ),
        stt_command=os.getenv("STT_COMMAND", "").strip(),
        tts_command=os.getenv("TTS_COMMAND", "").strip(),
        fallback_stt_text=os.getenv("FALLBACK_STT_TEXT", "").strip(),
        sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
        channels=int(os.getenv("AUDIO_CHANNELS", "1")),
        frame_ms=int(os.getenv("AUDIO_FRAME_MS", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        xiaozhi_ip=os.getenv("XIAOZHI_IP", "").strip(),
        tool_bridge_url=os.getenv("TOOL_BRIDGE_URL", "http://127.0.0.1:18790").rstrip("/"),
        smart_home_url=os.getenv("SMART_HOME_URL", "http://127.0.0.1:18880").rstrip("/"),
        motion_pulse_ms=max(100, min(int(os.getenv("MOTION_PULSE_MS", "450")), 2000)),
    )
