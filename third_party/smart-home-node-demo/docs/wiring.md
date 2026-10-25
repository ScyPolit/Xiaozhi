# 接线说明

本文说明如何将 5 个 LED 连接到 STM32 开发板，用于智能家居灯光控制演示。

## 引脚映射

| 灯名称 | LED ID | STM32 引脚 |
|---|---:|---|
| 客厅灯 | 1 | PA4 |
| 卧室灯 | 2 | PA5 |
| 厨房灯 | 3 | PA6 |
| 卫生间灯 | 4 | PA7 |
| 梳妆台灯 | 5 | PB0 |

## 基本接法

推荐默认接法如下：

- `PA4` 接 LED1 正极
- `PA5` 接 LED2 正极
- `PA6` 接 LED3 正极
- `PA7` 接 LED4 正极
- `PB0` 接 LED5 正极
- 每个 LED 负极串联一个限流电阻后接 `GND`

即：

```text
GPIO ----> LED 正极 ----> LED 负极 ----> 电阻 ----> GND
```

## 限流电阻建议

每个 LED 必须串联限流电阻，推荐：

- `220Ω`
- `330Ω`

不要直接把 LED 裸接到 GPIO 和 GND 之间，否则可能损坏 LED 或 IO 口。

## 电平说明

开发板 IO 电平通常为：

- `3.3V`

本项目默认逻辑为：

- GPIO 输出高电平：LED 点亮
- GPIO 输出低电平：LED 熄灭

对应固件宏定义位于 [`firmware/Core/Inc/gpio_led.h`](../firmware/Core/Inc/gpio_led.h)：

```c
#define LED_ACTIVE_HIGH 1
```

如果你的实际电路是低电平点亮，请改为：

```c
#define LED_ACTIVE_HIGH 0
```

## 串口连接说明

如果开发板没有自带 USB 虚拟串口，可使用 USB 转串口模块。

连接方式：

- STM32 TX → USB 转串口 RX
- STM32 RX → USB 转串口 TX
- STM32 GND → USB 转串口 GND

注意：

- 必须共地
- 不要把 TX 接 TX、RX 接 RX
- 串口电平应为 `3.3V` 兼容

## 接线检查清单

上电前请确认：

- 5 个 LED 都串联了限流电阻
- LED 极性没有接反
- GPIO 引脚与文档一致
- 串口 TX/RX 没有接反
- USB 转串口模块支持 3.3V 电平

## 推荐演示顺序

1. 先只接一个 LED 到 `PA4`
2. 烧录固件并测试 `SET 1 ON`
3. 确认单灯正常后，再接剩余 4 个 LED
4. 最后启动后端和前端进行整体演示
