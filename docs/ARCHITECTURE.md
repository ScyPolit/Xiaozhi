# 系统架构

## 1. 设计目标

智核不是把三个独立演示放在同一个仓库，而是通过网关把“对话大脑、移动机器人、智能家居与桌面助手”收敛到一条可替换、可验证的本地链路。硬件变化被限制在设备层，模型或语音服务变化被限制在网关配置层。

## 2. 运行组件

### OpenClaw

`openclaw/workspace` 保存角色设定、记忆和三个领域技能：机器人控制、智能家居、桌面助手。OpenClaw 只负责理解与编排，不直接暴露给 ESP32，也不直接操作 GPIO。

### 智核网关

`apps/gateway` 是集成边界，提供：

- `/xiaozhi/v1/`：小智 WebSocket 握手、Opus 音频和中断协议。
- `/`、`/dashboard/ws`：统一控制台和文本控制通道。
- STT -> OpenClaw -> TTS 流程。
- 本地高优先级意图，包括急停、短脉冲运动、灯光与空调控制。
- 受限 Windows 工具桥，只允许在白名单根目录和非破坏性命令范围内工作。

### SparkBot

`firmware/sparkbot/head` 面向 ESP32-S3 头部设备，负责屏幕、麦克风、扬声器和联网；`firmware/sparkbot/chassis` 面向 ESP32-C3 底盘，负责运动、灯效和传感器。网关使用带自动停止的短脉冲控制，急停意图优先于模型回复。

### 智能家居

两种执行端实现相同用途：

- `apps/smart-home-rpi`：树莓派 GPIO 服务，适合快速部署和本机模拟。
- `firmware/smart-home-stm32`：STM32F103 + ESP8266 AT 固件，适合嵌入式实机展示。

网关通过 `SMART_HOME_URL` 选择执行端，调用 `/api/health`、`/api/led`、`/api/all` 和 `/api/ac`，因此切换硬件不影响上层技能。

## 3. 端口与协议

| 默认端口 | 组件 | 协议 |
| --- | --- | --- |
| `8000` | 智核网关 | HTTP + WebSocket |
| `18789` | OpenClaw Gateway | OpenAI 兼容 API |
| `18790` | Windows 工具桥 | 本机 HTTP |
| `18880` | 智能家居模拟器/树莓派服务 | HTTP |

端口与设备地址均可在 `apps/gateway/.env` 中覆盖。

## 4. 关键流程

1. ESP32 连接网关并完成小智 `hello` 握手。
2. 设备上传 16 kHz 单声道 Opus 帧，网关完成 STT。
3. 本地控制意图先经过安全解析；能直接执行的运动或家居命令不依赖模型猜测。
4. 普通对话和工具上下文发送给 OpenClaw。
5. 回复经 TTS 生成音频并编码成设备可播放的 Opus 帧。
6. 收到 `abort` 或急停时，网关取消当前输出并发送停止命令。

## 5. 保留的历史内容

`third_party/sparkbot-legacy-baidu` 是已失效百度 API 协议对应的旧版代码；`third_party/smart-home-node-demo` 是早期 Node.js 串口方案。它们不属于当前默认运行链路，但被保留用于追溯和对照，不应作为新功能入口。
