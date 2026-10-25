# ESP8266-01S 排查

## AT 无响应

- 检查 VCC 是否为稳定 3.3V，不能是 5V。
- 检查电源电流能力，建议独立 3.3V 稳压模块。
- 检查 STM32 GND 和 ESP8266 GND 是否共地。
- 检查 TX/RX 是否交叉：ESP TXD 到 PA10，ESP RXD 到 PA9。
- 检查 AT 固件波特率是否为 115200。

## 经常重启或掉线

- 优先怀疑供电不足。
- 缩短杜邦线，给 ESP8266 电源附近加 100uF 或更大电容。
- 确认 EN/CH_PD、GPIO0、GPIO2 均为稳定高电平。

## hostname 访问失败

- 某些路由器不会解析 `smart-home-stm32`。
- 某些 AT 固件不支持 `AT+CWHOSTNAME` 或 `AT+MDNS`。
- 在路由器 DHCP 客户端列表中查看 ESP8266 IP，使用 `http://192.168.x.x`。

## 浏览器连接失败

- 确认 STM32 已成功执行 `AT+CIPSERVER=1,80`。
- 确认电脑和 ESP8266 在同一个局域网。
- 先访问 `GET /api/health`，再测试 LED 控制接口。
