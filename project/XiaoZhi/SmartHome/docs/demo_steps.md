# 演示步骤

1. 连接 5 个 LED：PA4 客厅灯、PA5 卧室灯、PA6 厨房灯、PA7 卫生间灯、PB0 梳妆台灯。
2. 在 PA15 连接蜂鸣器模块，用于模拟空调。蜂鸣器模块建议使用有源蜂鸣器模块或三极管/驱动模块，高电平触发。
2. 每个 LED 使用 220 欧或 330 欧限流电阻，按高电平点亮方式接线。
3. 连接 ESP8266-01S：TXD 到 PA10，RXD 到 PA9，GND 共地，VCC 使用独立 3.3V。
4. 确认 EN/CH_PD、GPIO0、GPIO2 在正常运行时接 3.3V。
5. 确认 ESP8266-01S 已烧录 AT 固件，默认 UART 波特率为 115200。
6. 在 [app_config.h](../Inc/app_config.h) 修改 Wi-Fi SSID 和密码。
7. 使用 STM32Cube for VSCode 打开当前项目根目录。
8. 确认 PA4、PA5、PA6、PA7、PB0、PA15 为 GPIO 输出。本工程当前在 `LED_Init()` 中用寄存器配置，PA15 会禁用 JTAG 并保留 SWD。
9. 确认 USART1 使用 PA9 TX、PA10 RX，115200 8N1。本工程当前在 `ESP8266_Init()` 中配置。
10. 编译 STM32 固件：`cmake --preset Debug`，然后 `cmake --build --preset Debug`。
11. 使用 ST-LINK 或兼容工具烧录 `build/Debug/c8t6test.hex`。
12. 复位开发板，等待 ESP8266 连接 Wi-Fi 并启动 TCP Server。
13. 在路由器客户端列表中查看 `smart-home-stm32` 或 ESP8266 的 IP。
14. 打开 [frontend/index.html](../frontend/index.html)。
15. 输入设备地址，例如 `http://smart-home-stm32`、`http://smart-home-stm32.local` 或 `http://192.168.1.123`。
16. 点击刷新状态。
17. 点击单灯开关，观察对应 LED。
18. 点击全开。
19. 点击全关。
