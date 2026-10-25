# 固件工程

本目录只放当前系统使用的嵌入式工程，每个子目录都保持自身构建系统和依赖结构。

| 目录 | 芯片 | 作用 | 构建环境 |
| --- | --- | --- | --- |
| `sparkbot/head` | ESP32-S3 | 屏幕、音频、摄像头、联网与小智协议终端 | ESP-IDF 5.3+ |
| `sparkbot/chassis` | ESP32-C3 | 电机、灯效、红外与电源管理 | ESP-IDF |
| `smart-home-stm32` | STM32F103C8T6 | ESP8266 AT 网络、HTTP API、灯光与空调模拟 | CMake + GNU Arm Toolchain |

不要在目录之间共享构建输出。ESP-IDF 的 `build/`、STM32 的 `build/` 和本机 SDK 配置均由忽略规则排除。

可直接烧录的发布固件位于 `tools/esp-flasher`，源码构建产物不需要提交到仓库。
