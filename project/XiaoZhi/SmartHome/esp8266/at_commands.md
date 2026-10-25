# ESP8266 AT 指令流程

STM32 启动后按以下顺序初始化 ESP8266-01S：

```text
AT
ATE0
AT+CWMODE=1
AT+CWHOSTNAME="smart-home-stm32"
AT+CWJAP="YOUR_WIFI_SSID","YOUR_WIFI_PASSWORD"
AT+CIFSR
AT+CIPMUX=1
AT+CIPSERVER=1,80
AT+MDNS=1,"smart-home-stm32","http",80
```

兼容性说明：

- `AT+CWHOSTNAME` 不是所有 AT 固件都支持。失败时固件继续运行，可改用路由器分配的 IP 访问。
- `AT+MDNS` 不是所有 AT 固件都支持。`smart-home-stm32.local` 访问失败时，改用 hostname 或 IP。
- `AT+CWJAP` 连接失败时，STM32 不会永久卡死，会定时重试。

HTTP 请求由 ESP8266 以如下格式转发给 STM32：

```text
+IPD,0,123:GET /api/leds HTTP/1.1
Host: smart-home-stm32
...
```

STM32 返回响应：

```text
AT+CIPSEND=0,<length>
<HTTP/1.1 JSON response>
AT+CIPCLOSE=0
```
