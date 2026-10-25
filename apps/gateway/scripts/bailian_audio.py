from __future__ import annotations

import os
import sys
import wave
from pathlib import Path

import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback
from dashscope.audio.tts_v2 import AudioFormat, SpeechSynthesizer


class ResultCollector(RecognitionCallback):
    def __init__(self) -> None:
        self.sentences: dict[int, str] = {}
        self.error = ""

    def on_event(self, result) -> None:
        sentence = result.get_sentence() if hasattr(result, "get_sentence") else None
        if not sentence:
            return
        index = int(sentence.get("sentence_id", len(self.sentences)))
        text = str(sentence.get("text") or "").strip()
        if text:
            self.sentences[index] = text

    def on_error(self, result) -> None:
        self.error = str(result)


def init_key() -> None:
    key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("DASHSCOPE_API_KEY is not configured")
    dashscope.api_key = key


def transcribe(path: Path) -> str:
    callback = ResultCollector()
    recognition = Recognition(
        model=os.getenv("BAILIAN_STT_MODEL", "paraformer-realtime-v2"),
        callback=callback,
        format="wav",
        sample_rate=16000,
        language_hints=["zh", "en"],
    )
    result = recognition.call(str(path))
    if callback.error:
        raise RuntimeError(callback.error)
    if getattr(result, "status_code", 200) not in (None, 200):
        raise RuntimeError(str(result))
    return "".join(callback.sentences[index] for index in sorted(callback.sentences)).strip()


def synthesize(text: str, path: Path) -> None:
    synthesizer = SpeechSynthesizer(
        model=os.getenv("BAILIAN_TTS_MODEL", "cosyvoice-v3-flash"),
        voice=os.getenv("BAILIAN_TTS_VOICE", "longxiaochun_v3"),
        format=AudioFormat.PCM_16000HZ_MONO_16BIT,
        speech_rate=float(os.getenv("BAILIAN_TTS_RATE", "1.08")),
    )
    pcm = synthesizer.call(text)
    if not pcm:
        raise RuntimeError("Bailian TTS returned no audio")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(pcm)


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in {"stt", "tts"}:
        print("usage: bailian_audio.py stt <input.wav> | tts <text> <output.wav>", file=sys.stderr)
        return 2
    init_key()
    if sys.argv[1] == "stt":
        print(transcribe(Path(sys.argv[2])))
        return 0
    if len(sys.argv) != 4:
        return 2
    synthesize(sys.argv[2], Path(sys.argv[3]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
