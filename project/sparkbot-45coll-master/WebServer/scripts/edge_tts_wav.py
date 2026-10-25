from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts


async def main() -> int:
    if len(sys.argv) != 3:
        print("usage: edge_tts_wav.py <text> <output.wav>", file=sys.stderr)
        return 2

    text = sys.argv[1]
    output = Path(sys.argv[2])
    voice = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    with tempfile.TemporaryDirectory(prefix="edge-tts-") as tmpdir:
        mp3 = Path(tmpdir) / "tts.mp3"
        await edge_tts.Communicate(text, voice).save(str(mp3))
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(mp3),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-sample_fmt",
                "s16",
                str(output),
            ],
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

