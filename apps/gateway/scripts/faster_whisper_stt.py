from __future__ import annotations

import os
import sys
import wave
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

CONTROL_HOTWORDS = "停止移动 停下 急停 前进 后退 左转 右转 打开灯光 关闭灯光 客厅 卧室 厨房 卫生间 梳妆台 空调"
SAFE_CORRECTIONS = {
    "品質移動": "停止移动",
    "品质移动": "停止移动",
    "停止一動": "停止移动",
    "停止一动": "停止移动",
}


def read_pcm16_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    if sample_width != 2 or sample_rate != 16000:
        raise ValueError("STT input must be 16-bit 16 kHz WAV")
    audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: faster_whisper_stt.py <input.wav>", file=sys.stderr)
        return 2

    wav_path = Path(sys.argv[1])
    model_name = os.getenv("WHISPER_MODEL", "tiny")
    language = os.getenv("WHISPER_LANGUAGE", "zh") or None
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        read_pcm16_wav(wav_path),
        language=language,
        vad_filter=True,
        beam_size=5,
        hotwords=CONTROL_HOTWORDS,
        initial_prompt="这是中文机器人控制语音，可能包含移动、停止和智能家居命令。",
    )
    text = "".join(segment.text for segment in segments).strip()
    for source, target in SAFE_CORRECTIONS.items():
        text = text.replace(source, target)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

