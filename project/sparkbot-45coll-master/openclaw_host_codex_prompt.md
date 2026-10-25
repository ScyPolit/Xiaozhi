# 给 OpenClaw 主机 Codex 的完整提示词

你现在在一台已经部署了 OpenClaw 的局域网主机上工作。请你实现一个“小智 ESP32 WebSocket 协议兼容网关”，让 SparkBot / 小智 ESP32 设备可以通过局域网 WebSocket 连接到这台主机，并把聊天大模型切换为本机 OpenClaw。

## 背景

ESP32 设备固件已经改成 WebSocket 通道，并支持在设备网页配置里填写服务地址：

```text
ws://<你的主机局域网IP>:<端口>/xiaozhi/v1/
```

设备端行为如下：

- WebSocket 握手请求头会带：
  - `Authorization: Bearer <token>`
  - `Protocol-Version: 1`
  - `Device-Id: <mac>`
  - `Client-Id: <uuid>`
- 连接建立后，设备先发送 JSON hello：

```json
{
  "type": "hello",
  "version": 1,
  "transport": "websocket",
  "audio_params": {
    "format": "opus",
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 60
  }
}
```

- 服务端必须在 10 秒内回复：

```json
{
  "type": "hello",
  "transport": "websocket",
  "audio_params": {
    "sample_rate": 16000
  }
}
```

- 设备会发送文本 JSON 消息：
  - `{"type":"listen","state":"detect","text":"你好小智"}`
  - `{"type":"listen","state":"start","mode":"auto|manual|realtime"}`
  - `{"type":"listen","state":"stop"}`
  - `{"type":"abort","reason":"wake_word_detected"}`
  - `{"type":"iot", ...}`
- 设备录音以 WebSocket binary frame 发送，内容是 Opus，16kHz，单声道，通常 60ms 一帧。
- 服务端需要给设备发送：
  - STT 结果：`{"type":"stt","text":"用户说的话"}`
  - LLM 表情：`{"type":"llm","emotion":"neutral|happy|sad|thinking"}`
  - TTS 开始：`{"type":"tts","state":"start"}`
  - 当前句子文本：`{"type":"tts","state":"sentence_start","text":"回复文本"}`
  - TTS 音频：WebSocket binary frame，Opus，建议 16kHz 单声道
  - TTS 结束：`{"type":"tts","state":"stop"}`

## 目标

请在本机创建或修改服务端项目，实现：

1. 启动一个 WebSocket 服务，路径为 `/xiaozhi/v1/`。
2. 完整兼容上述小智 WebSocket 协议。
3. 接收 ESP32 上传的 Opus 音频，完成语音识别。
4. 将识别文本发送给本机 OpenClaw 作为 LLM。
5. 将 OpenClaw 回复文本送入 TTS。
6. 将 TTS 音频转换/编码为 ESP32 可播放的 Opus binary frame 发回设备。
7. 支持打断：收到 `abort` 后停止当前 LLM/TTS 输出。
8. 保留日志，至少打印连接设备、STT 文本、OpenClaw 回复、TTS 开始/结束、异常栈。

## OpenClaw 接入要求

优先按 OpenAI 兼容接口接入 OpenClaw。请先探测本机可用地址，例如：

```text
http://127.0.0.1:8000/v1
http://127.0.0.1:11434/v1
http://127.0.0.1:3000/v1
```

如果 OpenClaw 的实际接口不是 OpenAI 兼容格式，请你根据本机 OpenClaw 文档或已存在服务代码写一个 adapter。不要让 ESP32 直接调用 OpenClaw。

OpenAI 兼容调用示例：

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer local

{
  "model": "openclaw",
  "messages": [
    {"role": "system", "content": "你是一个简洁、自然、适合语音对话的机器人。"},
    {"role": "user", "content": "你好"}
  ],
  "stream": true
}
```

## STT/TTS 要求

请优先复用本机已有 STT/TTS。如果没有现成服务，请实现可配置方案：

- STT 输入：Opus 音频流，需要解码为 PCM 16kHz mono 后识别。
- TTS 输出：生成 PCM/WAV 后重新编码为 Opus 16kHz mono，按帧发送给 ESP32。
- 可用工具可以是 ffmpeg、whisper/faster-whisper、SenseVoice、本地 TTS、edge-tts、piper、cosyvoice 等。

要把 STT、LLM、TTS 做成配置项，例如 `.env`：

```env
HOST=0.0.0.0
PORT=8000
ACCESS_TOKEN=test-token

OPENCLAW_BASE_URL=http://127.0.0.1:8000/v1
OPENCLAW_API_KEY=local
OPENCLAW_MODEL=openclaw

STT_PROVIDER=auto
TTS_PROVIDER=auto
VOICE=default
```

## 建议实现形态

如果没有现成框架，建议用 Python 实现：

- `fastapi` 或 `aiohttp`
- `websockets`
- `openai` SDK 或 `httpx`
- `opuslib` / `pyogg` / `ffmpeg` 处理 Opus
- 一个 `Session` 对象保存每个设备的状态、音频缓冲、当前 TTS 任务和中断标志

请提供：

1. 可运行服务代码。
2. `.env.example`。
3. `README.md`，写清楚如何启动、如何填 ESP32 设备上的 WebSocket URL。
4. 一个本地自测脚本，至少能测试：
   - WebSocket hello 握手
   - 文本模拟 STT 后调用 OpenClaw
   - TTS 输出是否能生成 Opus 帧
5. 运行后打印主机局域网 IP 和设备应填写的 URL，例如：

```text
SparkBot WebSocket URL: ws://192.168.1.23:8000/xiaozhi/v1/
Access Token: test-token
```

## 验收标准

- ESP32 连接后 10 秒内收到 hello 响应。
- 唤醒或按键开始说话后，服务端能收到 Opus binary 音频。
- 服务端能输出 STT 文本。
- OpenClaw 能返回回复。
- 设备屏幕能显示用户文本和助手文本。
- 设备能播放 TTS 回复音频。
- 收到 abort 后，正在播放的 TTS 能停止或尽快结束。

请你直接实施，不要只给方案。实现后运行服务并给出设备需要填写的 WebSocket URL和access token。
