# Xiaozhi

Xiaozhi 是一个基于 OpenClaw 的桌面三合一机器人系统，整合自然语音交互、可移动机器人控制、智能家居与桌面工具调用。OpenClaw 负责推理和技能编排，智核网关负责协议转换与安全执行，ESP32、STM32 或树莓派负责真实设备动作。

## 系统组成

| 层级 | 主要目录 | 责任 |
| --- | --- | --- |
| 智能层 | `openclaw/workspace` | OpenClaw 人格、记忆与技能 |
| 网关层 | `apps/gateway` | 小智协议、STT/LLM/TTS、设备意图、控制台与工具桥 |
| 设备层 | `firmware/sparkbot` | ESP32-S3 机器人头部与 ESP32-C3 底盘固件 |
| 家居层 | `apps/smart-home-rpi`、`firmware/smart-home-stm32` | 两种可替换的智能家居执行端 |
| 硬件与交付 | `hardware`、`tools`、`docs` | 结构件、烧录工具、演示与项目材料 |

## 核心链路

```text
语音 / 网页控制台
        |
SparkBot ESP32 <--WebSocket/Opus--> 智核网关 <--OpenAI 兼容 API--> OpenClaw
                                      |                     |
                                      |                     +--> 桌面工具桥
                                      +--> 机器人底盘命令
                                      +--> 智能家居 HTTP API
                                             |-- 树莓派 GPIO
                                             `-- STM32 + ESP8266
```

网关对上屏蔽模型和语音服务差异，对下统一设备控制。树莓派和 STM32 是同一智能家居 API 的两种实现，可以按演示环境切换，不需要修改 OpenClaw 技能。

## 快速运行

Windows 一键启动：

```powershell
py -m venv apps\gateway\.venv
apps\gateway\.venv\Scripts\pip.exe install -r apps\gateway\requirements.txt
Copy-Item apps\gateway\.env.example apps\gateway\.env
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

启动后访问 `http://127.0.0.1:8000/`。停止全部本地服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\stop.ps1
```

设备连接、语音服务和实机交付参数见 [网关说明](apps/gateway/README.md) 与 [交付说明](apps/gateway/DELIVERY.md)。系统边界与协议见 [架构文档](docs/ARCHITECTURE.md)。

## 目录说明

- `apps/gateway`：本项目自研核心，建议从这里开始阅读。
- `apps/smart-home-rpi`：可部署在树莓派上的 GPIO HTTP 服务，也支持本机模拟。
- `firmware/sparkbot/head`：机器人头部 ESP32-S3 固件工程。
- `firmware/sparkbot/chassis`：机器人底盘 ESP32-C3 固件工程。
- `firmware/smart-home-stm32`：STM32F103 + ESP8266 智能家居固件及网页前端。
- `openclaw/workspace`：`robot-control`、`smart-home`、`desktop-assistant` 技能。
- `hardware/enclosures`：3D 打印结构件。
- `tools/esp-flasher`：离线固件、烧录工具和配置。
- `third_party`：未参与主运行链路的上游旧代码与历史示例。
- `docs/project`：项目报告、答辩演示、视频与截图。
- `docs/upstream`：上游 SparkBot 原说明与素材，保留用于溯源。

## 开源边界

项目基于 SparkBot、小智 ESP32 生态及其依赖组件继续开发。上游代码没有被包装成自研成果；来源、用途和本项目新增部分记录在 [第三方与来源清单](THIRD_PARTY.md)。各子项目原许可证继续适用于对应目录。

## 安全配置

真实 `.env`、Wi-Fi 密码、API 密钥、虚拟环境、日志与运行状态不会进入 Git。首次运行前请从 `.env.example` 创建本地配置，并将 `firmware/smart-home-stm32/Inc/app_config.h` 中的占位网络参数替换为本地值。
