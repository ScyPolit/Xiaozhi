# 固件说明

本目录提供 STM32 端核心业务代码，用于实现 5 路 LED 控制和 UART 文本协议解析。

## 文件说明

- [`Core/Inc/main.h`](Core/Inc/main.h)：主头文件，包含 HAL 头文件和错误处理声明。
- [`Core/Inc/gpio_led.h`](Core/Inc/gpio_led.h)：LED 控制模块头文件，定义 LED 数量、ID、状态和 API。
- [`Core/Src/main.c`](Core/Src/main.c)：主程序入口，完成 HAL 初始化、时钟初始化、UART 初始化和协议轮询。
- [`Core/Src/gpio_led.c`](Core/Src/gpio_led.c)：LED GPIO 初始化与控制实现。
- [`Core/Src/usart_protocol.c`](Core/Src/usart_protocol.c)：串口中断接收、命令解析、响应发送。
- [`stm32cube_notes.md`](stm32cube_notes.md)：如何在 STM32CubeMX 中配置工程。

## 支持的 LED 引脚

| LED ID | 名称 | 引脚 |
|---:|---|---|
| 1 | 客厅灯 | PA4 |
| 2 | 卧室灯 | PA5 |
| 3 | 厨房灯 | PA6 |
| 4 | 卫生间灯 | PA7 |
| 5 | 梳妆台灯 | PB0 |

## LED 控制接口

在 [`gpio_led.h`](Core/Inc/gpio_led.h) 中提供以下接口：

```c
void LED_Init(void);
void LED_Set(uint8_t led_id, uint8_t state);
void LED_SetAll(uint8_t state);
uint8_t LED_Get(uint8_t led_id);
void LED_Toggle(uint8_t led_id);
```

默认高电平点亮：

```c
#define LED_ACTIVE_HIGH 1
```

如果你的硬件是低电平点亮，可改为：

```c
#define LED_ACTIVE_HIGH 0
```

## 串口协议

波特率默认 `115200`，格式 `8N1`。

支持命令：

```text
SET 1 ON
SET 1 OFF
ALL ON
ALL OFF
STATUS
```

返回：

```text
OK
ERR
STATUS 1:ON 2:OFF 3:ON 4:OFF 5:OFF
```

## 集成方式

推荐流程：

1. 使用 STM32CubeMX 生成一个基础 HAL 工程。
2. 打开生成后的 [`Core/Inc/main.h`](Core/Inc/main.h) 和 [`Core/Src/main.c`](Core/Src/main.c)。
3. 将本目录中的 LED 模块和协议模块复制到对应目录。
4. 根据你的芯片型号调整 HAL 头文件，例如：
   - [`stm32f1xx_hal.h`](Core/Inc/main.h)
   - [`stm32f4xx_hal.h`](Core/Inc/main.h)
5. 确认 UART 实例与你的板子一致，例如 [`USART1`](Core/Src/main.c)。
6. 编译并烧录。

## 注意事项

- [`SystemClock_Config()`](Core/Src/main.c) 中给的是最小示例，建议直接使用 CubeMX 自动生成版本。
- 如果使用的不是 [`USART1`](Core/Src/main.c)，请同步修改 GPIO 和 UART 初始化代码。
- 如果串口同时输出调试日志，可能影响协议解析，建议协议串口专用。
- 如果使用 USB 转串口模块，请确保：
  - STM32 TX → USB 转串口 RX
  - STM32 RX → USB 转串口 TX
  - GND 共地

## 编译与烧录

可使用以下任一方式：

- STM32CubeIDE
- Keil MDK
- IAR
- CMake + arm-none-eabi-gcc

烧录工具可使用：

- ST-Link Utility
- STM32CubeProgrammer
- 开发板自带下载器

详细配置步骤见 [`stm32cube_notes.md`](stm32cube_notes.md)。
