# STM32CubeMX 配置说明

本文说明如何基于 STM32CubeMX / STM32CubeIDE 生成一个 HAL 工程，并集成本项目的 LED 控制与串口协议代码。

## 1. 适用芯片

本项目不强绑定某一个具体型号，但推荐以下两类板子作为示例：

- [`STM32F103C8T6`](README.md)
- [`STM32F401RE`](README.md)

如果你使用其他 STM32 型号，也可以参考相同思路，只需调整：

- HAL 头文件
- UART 实例
- GPIO 复用配置
- 时钟配置

## 2. 新建 CubeMX 工程

在 STM32CubeMX 中：

1. 选择你的芯片或开发板。
2. 新建工程。
3. 在 Pinout 页面配置 GPIO 和 USART。
4. 在 Clock Configuration 页面配置系统时钟。
5. 在 Project Manager 中选择生成工具链，例如 STM32CubeIDE。
6. 生成代码。

## 3. GPIO 配置

将以下引脚配置为 [`GPIO_Output`](README.md)：

- `PA4`
- `PA5`
- `PA6`
- `PA7`
- `PB0`

推荐参数：

- Output Level：Low
- Mode：Output Push Pull
- Pull-up/Pull-down：No pull-up and no pull-down
- Maximum output speed：Low 或 Medium

说明：

- 如果 LED 为高电平点亮，则默认输出 Low 表示上电熄灭。
- 如果你的板子外接电路是低电平点亮，可在 [`Core/Inc/gpio_led.h`](Core/Inc/gpio_led.h) 中把 [`LED_ACTIVE_HIGH`](Core/Inc/gpio_led.h) 改为 `0`。

## 4. USART 配置

推荐使用 [`USART1`](Core/Src/main.c) 作为协议串口。

### 对于 STM32F103C8T6 常见配置

- `PA9` -> USART1_TX
- `PA10` -> USART1_RX

### 参数设置

- Mode：Asynchronous
- Baud Rate：`115200`
- Word Length：`8 Bits`
- Parity：`None`
- Stop Bits：`1`
- Hardware Flow Control：`None`
- Oversampling：`16`

### 中断配置

在 NVIC Settings 中启用 USART 全局中断。

建议启用：

- USART1 global interrupt

因为本项目的 [`Core/Src/usart_protocol.c`](Core/Src/usart_protocol.c) 使用 [`HAL_UART_Receive_IT()`](Core/Src/usart_protocol.c:84) 进行中断接收。

## 5. 时钟配置基本要求

### STM32F103C8T6 示例

可选方案：

- 使用 HSI + PLL
- 或使用外部晶振 HSE + PLL

常见目标系统时钟：

- `72MHz`

### STM32F401RE 示例

常见目标系统时钟：

- `84MHz`

要求：

- UART 时钟稳定
- HAL Tick 正常工作
- [`HAL_Delay()`](Core/Src/main.c:96) 可正常使用

建议：

- 直接使用 CubeMX 自动生成的 [`SystemClock_Config()`](Core/Src/main.c:24)
- 不要手工修改复杂时钟树，除非你非常熟悉芯片时钟系统

## 6. 生成 HAL 工程后，需要复制哪些文件

在 CubeMX 生成基础工程后，将本项目中的以下文件复制到生成工程对应位置：

### 复制到 `Core/Inc/`

- [`Core/Inc/gpio_led.h`](Core/Inc/gpio_led.h)

### 复制到 `Core/Src/`

- [`Core/Src/gpio_led.c`](Core/Src/gpio_led.c)
- [`Core/Src/usart_protocol.c`](Core/Src/usart_protocol.c)

### 参考并合并到生成工程中的文件

- [`Core/Inc/main.h`](Core/Inc/main.h)
- [`Core/Src/main.c`](Core/Src/main.c)

注意：

- 不建议直接粗暴覆盖 CubeMX 生成的 [`main.c`](Core/Src/main.c)，更推荐把本项目中的业务逻辑合并进去。
- 你需要保留 CubeMX 自动生成的：
  - 时钟初始化
  - GPIO 初始化框架
  - UART 初始化框架
  - 中断向量和 MSP 初始化

## 7. 推荐集成步骤

### 步骤 1：先用 CubeMX 生成基础工程

确保生成后工程可以正常编译。

### 步骤 2：加入 LED 模块

把以下文件加入工程：

- [`gpio_led.h`](Core/Inc/gpio_led.h)
- [`gpio_led.c`](Core/Src/gpio_led.c)

然后在 [`main.c`](Core/Src/main.c) 中调用：

```c
LED_Init();
```

### 步骤 3：加入串口协议模块

把以下文件加入工程：

- [`usart_protocol.c`](Core/Src/usart_protocol.c)

并在 [`main.c`](Core/Src/main.c) 中声明：

```c
void USART_Protocol_Init(UART_HandleTypeDef *huart);
void USART_Protocol_Process(void);
```

初始化后调用：

```c
USART_Protocol_Init(&huart1);
```

主循环中调用：

```c
USART_Protocol_Process();
```

### 步骤 4：确认中断回调可用

本项目在 [`usart_protocol.c`](Core/Src/usart_protocol.c) 中实现了：

- [`HAL_UART_RxCpltCallback()`](Core/Src/usart_protocol.c:46)
- [`HAL_UART_ErrorCallback()`](Core/Src/usart_protocol.c:77)

如果你的工程其他文件中也实现了这些回调，需要合并逻辑，避免重复定义。

## 8. 编译

### 使用 STM32CubeIDE

1. 导入或打开工程。
2. 点击 Build。
3. 确认无编译错误。

### 常见编译问题

#### 找不到 HAL 头文件

检查 [`main.h`](Core/Inc/main.h) 中包含的头文件是否与你芯片系列一致，例如：

- `stm32f1xx_hal.h`
- `stm32f4xx_hal.h`

#### UART 句柄名称不一致

如果 CubeMX 生成的是 [`huart2`](README.md) 而不是 [`huart1`](Core/Src/main.c)，请同步修改：

- [`main.c`](Core/Src/main.c)
- UART 初始化函数
- 协议初始化调用

## 9. 烧录

可使用以下工具烧录：

- STM32CubeProgrammer
- ST-Link Utility
- STM32CubeIDE 内置下载功能

### 基本步骤

1. 连接 ST-Link 或开发板下载接口。
2. 选择目标芯片。
3. 下载编译生成的 `.elf` 或 `.bin` 文件。
4. 复位运行。

## 10. 串口联调验证

烧录完成后，可先使用串口调试助手测试协议。

串口参数：

- 波特率：`115200`
- 数据位：`8`
- 停止位：`1`
- 校验位：`None`
- 发送结尾：`
`

测试命令：

```text
STATUS
SET 1 ON
SET 1 OFF
ALL ON
ALL OFF
```

预期响应：

```text
STATUS 1:OFF 2:OFF 3:OFF 4:OFF 5:OFF
OK
OK
OK
OK
```

## 11. 与后端联动前的最终检查

在启动 [`backend/server.js`](../backend/server.js) 前，请确认：

- 固件已烧录成功
- 串口号已识别
- 串口助手已关闭，避免占用
- STM32 能正确响应 [`STATUS`](../docs/protocol.md)

完成以上步骤后，即可通过 Web 页面控制 5 个 LED。
