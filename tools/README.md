# 工具与发布固件

`esp-flasher` 保留上游 Espressif 烧录工具、配置、使用文档和可直接烧录的发布固件：

- ESP32-S3 头部：`多功能小智固件_45coll.bin`，烧录地址 `0x0`。
- BMI270 头部变体：`bmi270/多功能小智固件_bmi270.bin`。
- ESP32-C3 底盘：`tank.bin`，烧录地址 `0x0`。

具体步骤见 `docs/upstream/sparkbot/tutorials` 和 `tools/esp-flasher/doc`。烧录日志与 `dl_temp` 临时文件不属于项目资产，已从版本库排除。
