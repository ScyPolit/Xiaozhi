# 第三方项目与来源

本仓库包含项目自研集成代码、上游硬件/固件代码以及第三方依赖。目录归属如下。

## SparkBot 45coll

- 位置：`firmware/sparkbot`、`hardware/enclosures`、`tools/esp-flasher`、`docs/upstream/sparkbot`。
- 上游说明：https://gitee.com/coll45/sparkbot-45coll
- 硬件基础：https://oshwhub.com/esp-college/esp-sparkbot
- 用途：机器人头部、底盘、结构件和固件烧录基础。
- 本项目融合：增加 OpenClaw 局域网网关、统一语音链路、机器人安全控制、智能家居和桌面技能编排。

上游原说明、图片、物料清单和教程集中保存在 `docs/upstream/sparkbot`。其中提到的销售、群聊或旧链接仅作为历史资料，不代表本项目维护入口。

## 小智 ESP32 及 ESP-IDF 组件

`firmware/sparkbot/head` 和 `firmware/sparkbot/chassis` 内包含 ESP-IDF managed components、LVGL、音频、摄像头、传感器等依赖。对应许可证文件保留在各组件目录中；这些组件的著作权和许可证归各自上游所有。

## 历史参考实现

- `third_party/sparkbot-legacy-baidu`：旧百度 API 协议源码，当前协议已失效，不参与默认构建。
- `third_party/smart-home-node-demo`：早期 Node.js + 串口智能家居样例，不参与当前 STM32 + ESP8266 HTTP 链路。

## 本项目自研部分

- `apps/gateway`：小智协议网关、OpenClaw 适配、语音链路、控制台、设备控制和工具桥。
- `apps/smart-home-rpi`：与网关 API 对齐的树莓派 GPIO 服务。
- `firmware/smart-home-stm32` 中针对智核场景的 STM32/ESP8266 控制逻辑和前端。
- `openclaw/workspace/skills`：机器人、智能家居和桌面助手技能。

没有根级统一许可证时，不应推断整个仓库使用单一许可证。复用代码前需查看目标目录和依赖内的许可证文件。
