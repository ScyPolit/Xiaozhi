# 智核语音与设备网关

本服务通过小智 WebSocket 协议连接 SparkBot ESP32 与局域网 OpenClaw，并统一转发机器人运动、智能家居和受限桌面工具调用。它是智核系统的运行中枢，不是独立的上游 SparkBot 组件。

## Run

```bash
cd apps/gateway
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m xiaozhi_gateway
```

The ESP32 should use:

```text
WebSocket URL: ws://<OpenClaw host LAN IP>:8000/xiaozhi/v1/
Access Token: test-token
```

## Configuration

Edit `.env`:

```env
HOST=0.0.0.0
PORT=8000
ACCESS_TOKEN=test-token
XIAOZHI_IP=192.168.31.219

OPENCLAW_BASE_URL=http://127.0.0.1:8000/v1
OPENCLAW_API_KEY=local
OPENCLAW_MODEL=openclaw

STT_COMMAND=./.venv/bin/python ./scripts/faster_whisper_stt.py
TTS_COMMAND=./.venv/bin/python ./scripts/edge_tts_wav.py
FALLBACK_STT_TEXT=
WHISPER_MODEL=tiny
WHISPER_LANGUAGE=zh
HF_ENDPOINT=https://hf-mirror.com
EDGE_TTS_VOICE=zh-CN-XiaoxiaoNeural
```

`STT_COMMAND` receives the decoded WAV path as the first argument and must print recognized text to stdout.

`TTS_COMMAND` receives text as the first argument and an output WAV path as the second argument.

The default STT command uses `faster-whisper` with the `tiny` model. The first recognition downloads the model and can be slow. The default TTS command uses `edge-tts` and converts the generated audio to 16 kHz mono WAV before Opus encoding.

If no STT/TTS command is configured, the gateway still completes protocol handshakes and forwards text-mode tests to OpenClaw, but real voice recognition and voice playback depend on local providers.

## Protocol Notes

The gateway accepts:

- `GET /health`
- `GET /state`
- `GET /` digital dashboard
- WebSocket `/dashboard/ws`
- WebSocket `/xiaozhi/v1/`

It handles:

- Xiaozhi hello handshake
- `listen start/stop/detect`
- `abort`
- raw Opus binary frames from ESP32
- STT text messages
- LLM text through OpenClaw OpenAI-compatible API
- TTS start, sentence text, optional Opus binary audio, and stop
- Dashboard text chat, abort, and Chassis control commands

## Local Test

```bash
python scripts/test_gateway.py ws://127.0.0.1:8000/xiaozhi/v1/ test-token
```
