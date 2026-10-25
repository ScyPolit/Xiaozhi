# 智核小智本地交付说明

## 一键启动

```powershell
cd WebServer
powershell -ExecutionPolicy Bypass -File .\start_zhihe.ps1
```

脚本会启动 2.4 GHz 移动热点 `scypolit`、OpenClaw、机器人网关、Windows 工具桥和智能家居模拟器。

- 中控页面：`http://127.0.0.1:8000/`
- 小智 WebSocket：`ws://192.168.137.1:8000/xiaozhi/v1/`
- Access Token：`test-token`
- OpenClaw Gateway：`127.0.0.1:18789`
- 树莓派模拟 API：`http://127.0.0.1:18880`

停止服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\stop_zhihe.ps1
```

## 已配置链路

- 对话模型：`glm-5.2`，中度思考，流式正文限制 360 字。
- STT：百炼 `paraformer-realtime-v2`。
- TTS：百炼 `cosyvoice-v3-flash`，16 kHz 单声道，经 PyAV 编码为机器人 Opus 帧。
- OpenClaw Skills：`robot-control`、`smart-home`、`desktop-assistant`。
- MCP：`zhihe-windows`，提供 7 个受限 Windows 工具。
- 实机地址：`192.168.137.141`，MAC `9c:13:9e:af:35:78`。

## 树莓派接入

项目位于 `project/XiaoZhi/RaspberryPiSmartHome`。在树莓派安装并启动 systemd 服务后，把 `WebServer/.env` 的 `SMART_HOME_URL` 改成树莓派地址，例如 `http://192.168.137.20:18880`，重启网关即可。

## 验证命令

```powershell
.venv\Scripts\python.exe scripts\test_local_intents.py
.venv\Scripts\python.exe scripts\test_gateway.py
.venv\Scripts\python.exe scripts\test_safe_motion.py
.venv\Scripts\python.exe scripts\test_controls.py
openclaw health --json
openclaw mcp probe zhihe-windows
```
