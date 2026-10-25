# ESP8266-01S 接线

| ESP8266-01S | STM32F103C8T6 |
| --- | --- |
| TXD | PA10 USART1_RX |
| RXD | PA9 USART1_TX |
| GND | GND |
| VCC | 独立 3.3V 稳压电源 |
| EN / CH_PD | 3.3V |
| RST | 3.3V，或接复位按钮到 GND |
| GPIO0 | 正常运行接 3.3V，烧录 AT 固件时接 GND |
| GPIO2 | 3.3V |

电源注意事项：

- ESP8266-01S 只能使用 3.3V，不能接 5V。
- 峰值电流较大，至少准备 500mA，推荐 700mA 或 1A。
- STM32 和 ESP8266 必须共地。
- STM32F103C8T6 是 3.3V IO，可直接连接 ESP8266 串口。
- 不建议直接使用部分 STM32 开发板自带的弱 3.3V 引脚给 ESP8266 供电。
