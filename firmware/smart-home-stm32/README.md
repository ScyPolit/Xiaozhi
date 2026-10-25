# STM32 + ESP8266-01S 智能家居 LED 控制系统

本项目基于当前 STM32Cube for VSCode 工程改造，目标 MCU 为 STM32F103C8T6。浏览器前端页面运行在电脑上，通过局域网访问 ESP8266-01S 的 TCP Server；ESP8266-01S 运行 AT 固件，只负责 Wi-Fi 和 TCP 透传；STM32 通过 USART1 接收 `+IPD` HTTP 请求，解析 API 后控制 PA4、PA5、PA6、PA7、PB0 上的 5 个 LED，并通过 PA15 蜂鸣器模块模拟空调。

## 系统架构

```text
电脑浏览器前端页面
→ 局域网 Wi-Fi
→ ESP8266-01S AT 固件 TCP Server
→ USART1 PA9/PA10
→ STM32F103C8T6
→ PA4、PA5、PA6、PA7、PB0 LED + PA15 空调蜂鸣器
```

使用 AT 固件的原因：ESP8266 不运行 Arduino/PlatformIO 程序，网络配置、TCP Server、连接收发都由 STM32 发送 AT 指令完成，控制逻辑集中在 STM32，适合课程设计展示“外部 Wi-Fi 模块 + MCU 主控”的架构。

## 当前工程结构说明

当前仓库是 STM32Cube for VSCode 生成过的扁平化工程，使用根目录 `Inc/`、`Src/`，没有标准 `Core/Inc`、`Core/Src` 和完整 HAL `Drivers/` 目录。因此本项目尊重现有结构，在 `Inc/` 和 `Src/` 中新增模块。`gpio_led.c` 内提供了兼容 `HAL_GPIO_WritePin` 风格的本地写引脚函数，底层仍按当前工程方式直接操作 STM32F103 寄存器。

旧的 `smart-home-stm32-led-control/` 子目录包含 Node 后端示例，本次系统不使用它。

## 硬件准备

- STM32F103C8T6 开发板
- ESP8266-01S，已烧录 AT 固件
- 5 个 LED
- 220 欧或 330 欧限流电阻
- 独立 3.3V 稳压模块，至少 500mA，推荐 700mA 或 1A
- ST-LINK 或兼容烧录器

## STM32 GPIO 与 USART1

LED 高电平点亮，低电平熄灭：

| 功能 | STM32 引脚 |
| --- | --- |
| 客厅灯 | PA4 |
| 卧室灯 | PA5 |
| 厨房灯 | PA6 |
| 卫生间灯 | PA7 |
| 梳妆台灯 | PB0 |
| 空调蜂鸣器 | PA15 |

USART1 连接 ESP8266-01S：

| ESP8266-01S | STM32F103C8T6 |
| --- | --- |
| TXD | PA10 USART1_RX |
| RXD | PA9 USART1_TX |
| GND | GND |
| VCC | 独立 3.3V |
| EN / CH_PD | 3.3V |
| RST | 3.3V，或复位按钮到 GND |
| GPIO0 | 运行接 3.3V，烧录 AT 固件时接 GND |
| GPIO2 | 3.3V |

注意：ESP8266-01S 只能接 3.3V，不能接 5V。STM32 和 ESP8266 必须共地。不要用电流能力弱的开发板 3.3V 引脚直接给 ESP8266 供电，否则容易重启、掉线、AT 无响应。

## Wi-Fi 配置

打开 [app_config.h](Inc/app_config.h)，把下面两个占位符改成本地 Wi-Fi：

```c
#define WIFI_SSID       "YOUR_WIFI_SSID"
#define WIFI_PASSWORD   "YOUR_WIFI_PASSWORD"
```

不要把真实密码提交到公开仓库。

固件会优先设置 hostname：

```text
AT+CWHOSTNAME="smart-home-stm32"
```

如果 AT 固件支持，可以用 `http://smart-home-stm32` 或 `http://smart-home-stm32.local` 访问；如果不支持 hostname 或 mDNS，请在路由器 DHCP 客户端列表中查看 ESP8266 获得的 IP，例如 `http://192.168.1.123`。

## 前端使用方法

直接打开 [frontend/index.html](frontend/index.html)。如果浏览器对 `file://` 页面请求局域网设备有限制，可用本地静态服务器：

```powershell
cd frontend
python -m http.server 8080
```

然后访问 `http://localhost:8080`。页面中输入设备地址，例如 `http://smart-home-stm32`、`http://smart-home-stm32.local` 或 `http://192.168.1.123`，保存后点击刷新状态。

## API 接口

- `GET /api/health`
- `GET /api/leds`
- `GET /api/led?id=1&state=on`
- `GET /api/led?id=1&state=off`
- `GET /api/all?state=on`
- `GET /api/all?state=off`
- `GET /api/ac?state=on`
- `GET /api/ac?state=off`
- `OPTIONS *`

响应包含 CORS 头，便于电脑上的静态前端跨域访问 ESP8266 地址。

## 编译方法

```powershell
cmake --list-presets
cmake --preset Debug
cmake --build --preset Debug
```

如果 `arm-none-eabi-gcc` 不在 PATH，需要安装 STM32Cube for VSCode 推荐的 GNU Tools for STM32，或把现有工具链 `bin` 目录加入 PATH。

## 烧录方法

如果安装了 STM32CubeProgrammer：

```powershell
STM32_Programmer_CLI --list
STM32_Programmer_CLI -c port=SWD -w build/Debug/c8t6test.hex -v -rst
```

如果使用 OpenOCD，请根据实际 ST-LINK 配置选择 interface 和 target。没有实际开发板或烧录器连接时，不要把命令输出当作烧录成功。

## 常见问题

- ESP8266 无响应：检查 3.3V 供电能力、共地、PA9/PA10 是否交叉连接、波特率是否为 115200。
- 浏览器无法访问 hostname：在路由器中查 ESP8266 IP，改用 `http://IP地址`。
- 页面提示 CORS 或连接失败：确认 STM32 已启动 TCP Server，前端设备地址没有多余路径。
- LED 或蜂鸣器不动作：确认 PA4、PA5、PA6、PA7、PB0、PA15 接线和限流/驱动电路，当前设计为高电平有效。PA15 默认是 JTAG JTDI，固件已禁用 JTAG 并保留 SWD。
