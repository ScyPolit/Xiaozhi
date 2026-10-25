from __future__ import annotations

import asyncio
import logging
import math
import shlex
import struct
import tempfile
import wave
from fractions import Fraction
from pathlib import Path

from .config import Config

LOGGER = logging.getLogger(__name__)


class AudioBridge:
    def __init__(self, config: Config):
        self._config = config
        self._tts_cache: dict[str, list[bytes]] = {}

    async def recognize(self, opus_packets: list[bytes]) -> str:
        if not opus_packets:
            return self._config.fallback_stt_text

        with tempfile.TemporaryDirectory(prefix="xiaozhi-stt-") as tmpdir:
            wav_path = Path(tmpdir) / "input.wav"
            decoded = await self._decode_opus_to_wav(opus_packets, wav_path)
            if decoded and self._config.stt_command:
                try:
                    text = await self._run_command(self._config.stt_command, [str(wav_path)])
                    return text.strip() or self._config.fallback_stt_text
                except Exception as exc:
                    LOGGER.warning("STT command failed: %s", exc)
        return self._config.fallback_stt_text

    async def synthesize_opus(self, text: str) -> list[bytes]:
        if not text:
            return []
        if text in self._tts_cache:
            return list(self._tts_cache[text])

        with tempfile.TemporaryDirectory(prefix="xiaozhi-tts-") as tmpdir:
            wav_path = Path(tmpdir) / "reply.wav"
            if self._config.tts_command:
                await self._run_command(self._config.tts_command, [text, str(wav_path)])
            else:
                self._write_fallback_wav(wav_path, text)
            if not wav_path.exists():
                LOGGER.warning("TTS did not produce wav: %s", wav_path)
                return []
            packets = await self._encode_wav_to_opus(wav_path)
            if packets and len(text) <= 32:
                if len(self._tts_cache) >= 64:
                    self._tts_cache.pop(next(iter(self._tts_cache)))
                self._tts_cache[text] = packets
            return packets

    async def _decode_opus_to_wav(self, packets: list[bytes], wav_path: Path) -> bool:
        try:
            import opuslib
        except Exception as exc:
            LOGGER.info("opuslib unavailable, decoding with PyAV: %s", exc)
            return self._decode_opus_with_av(packets, wav_path)

        decoder = opuslib.Decoder(self._config.sample_rate, self._config.channels)
        pcm = bytearray()
        frame_size = int(self._config.sample_rate * self._config.frame_ms / 1000)
        for packet in packets:
            try:
                pcm.extend(decoder.decode(packet, frame_size, decode_fec=False))
            except Exception as exc:
                LOGGER.debug("skipping undecodable opus packet: %s", exc)

        if not pcm:
            return False
        self._write_pcm_wav(wav_path, bytes(pcm), self._config.sample_rate, self._config.channels)
        return True

    def _decode_opus_with_av(self, packets: list[bytes], wav_path: Path) -> bool:
        try:
            import av
        except Exception as exc:
            LOGGER.warning("PyAV unavailable, cannot decode STT audio: %s", exc)
            return False
        codec = av.CodecContext.create("opus", "r")
        codec.sample_rate = self._config.sample_rate
        codec.layout = "mono"
        pcm = bytearray()
        try:
            for data in packets:
                for frame in codec.decode(av.Packet(data)):
                    array = frame.to_ndarray()
                    pcm.extend(array.astype("<i2", copy=False).tobytes())
        except Exception as exc:
            LOGGER.warning("PyAV Opus decode failed: %s", exc)
            return False
        if not pcm:
            return False
        self._write_pcm_wav(wav_path, bytes(pcm), self._config.sample_rate, self._config.channels)
        return True

    async def _encode_wav_to_opus(self, wav_path: Path) -> list[bytes]:
        try:
            import opuslib
        except Exception as exc:
            LOGGER.info("opuslib unavailable, encoding with PyAV: %s", exc)
            return self._encode_wav_with_av(wav_path)

        pcm, sample_rate, channels = self._read_wav_as_pcm16(wav_path)
        if sample_rate != self._config.sample_rate or channels != self._config.channels:
            converted = wav_path.with_name("reply-16k-mono.wav")
            ok = await self._ffmpeg_resample(wav_path, converted)
            if not ok:
                LOGGER.warning("cannot resample wav to 16 kHz mono")
                return []
            pcm, sample_rate, channels = self._read_wav_as_pcm16(converted)

        encoder = opuslib.Encoder(sample_rate, channels, opuslib.APPLICATION_VOIP)
        frame_samples = int(sample_rate * self._config.frame_ms / 1000)
        frame_bytes = frame_samples * channels * 2
        packets: list[bytes] = []
        for offset in range(0, len(pcm), frame_bytes):
            frame = pcm[offset : offset + frame_bytes]
            if len(frame) < frame_bytes:
                frame += b"\x00" * (frame_bytes - len(frame))
            try:
                packets.append(encoder.encode(frame, frame_samples))
            except Exception as exc:
                LOGGER.debug("failed to encode opus frame: %s", exc)
        return packets

    def _encode_wav_with_av(self, wav_path: Path) -> list[bytes]:
        try:
            import av
        except Exception as exc:
            LOGGER.warning("PyAV unavailable, cannot encode TTS audio: %s", exc)
            return []
        pcm, sample_rate, channels = self._read_wav_as_pcm16(wav_path)
        if sample_rate != self._config.sample_rate or channels != self._config.channels:
            LOGGER.warning("PyAV fallback expects 16 kHz mono WAV, got %d Hz/%d channels", sample_rate, channels)
            return []
        codec = av.CodecContext.create("libopus", "w")
        codec.sample_rate = sample_rate
        codec.layout = "mono"
        codec.format = "s16"
        codec.time_base = Fraction(1, sample_rate)
        codec.bit_rate = 32000
        codec.open()
        frame_samples = int(sample_rate * self._config.frame_ms / 1000)
        frame_bytes = frame_samples * 2
        packets: list[bytes] = []
        pts = 0
        for offset in range(0, len(pcm), frame_bytes):
            data = pcm[offset : offset + frame_bytes]
            if len(data) < frame_bytes:
                data += b"\x00" * (frame_bytes - len(data))
            frame = av.AudioFrame(format="s16", layout="mono", samples=frame_samples)
            frame.sample_rate = sample_rate
            frame.pts = pts
            frame.time_base = Fraction(1, sample_rate)
            frame.planes[0].update(data)
            pts += frame_samples
            packets.extend(bytes(packet) for packet in codec.encode(frame))
        packets.extend(bytes(packet) for packet in codec.encode(None))
        return packets

    async def _ffmpeg_resample(self, src: Path, dst: Path) -> bool:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-ac",
            str(self._config.channels),
            "-ar",
            str(self._config.sample_rate),
            "-sample_fmt",
            "s16",
            str(dst),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            LOGGER.warning("ffmpeg resample failed: %s", stderr.decode(errors="ignore"))
            return False
        return True

    async def _run_command(self, command: str, args: list[str]) -> str:
        parts = shlex.split(command)
        process = await asyncio.create_subprocess_exec(
            *parts,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await process.communicate()
        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            raise
        if process.returncode != 0:
            raise RuntimeError(stderr.decode(errors="ignore").strip() or f"command failed: {command}")
        return stdout.decode(errors="ignore")

    @staticmethod
    def _read_wav_as_pcm16(path: Path) -> tuple[bytes, int, int]:
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
            sample_width = wav.getsampwidth()
            frames = wav.readframes(wav.getnframes())
        if sample_width != 2:
            raise ValueError(f"expected 16-bit wav, got sample width {sample_width}")
        return frames, sample_rate, channels

    @staticmethod
    def _write_pcm_wav(path: Path, pcm: bytes, sample_rate: int, channels: int) -> None:
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm)

    def _write_fallback_wav(self, path: Path, text: str) -> None:
        duration = max(0.35, min(1.2, len(text) * 0.035))
        total = int(self._config.sample_rate * duration)
        amplitude = 2200
        pcm = bytearray()
        for index in range(total):
            value = int(amplitude * math.sin(2.0 * math.pi * 660.0 * index / self._config.sample_rate))
            pcm.extend(struct.pack("<h", value))
        self._write_pcm_wav(path, bytes(pcm), self._config.sample_rate, self._config.channels)
