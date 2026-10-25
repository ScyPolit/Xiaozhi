# 系统架构

```mermaid
flowchart LR
    Browser[电脑浏览器前端页面] -->|HTTP API / Wi-Fi LAN| ESP[ESP8266-01S\nAT 固件 TCP Server]
    ESP -->|+IPD HTTP 请求\nUSART1 115200 8N1| STM32[STM32F103C8T6\nHTTP 解析 + LED 控制]
    STM32 -->|AT+CIPSEND HTTP 响应| ESP
    STM32 --> PA4[PA4 客厅灯]
    STM32 --> PA5[PA5 卧室灯]
    STM32 --> PA6[PA6 厨房灯]
    STM32 --> PA7[PA7 卫生间灯]
    STM32 --> PB0[PB0 梳妆台灯]
    STM32 --> PA15[PA15 空调蜂鸣器]
```

ESP8266-01S 只承担 Wi-Fi 接入和 TCP Server 功能。STM32 发送 AT 指令完成初始化，浏览器请求进入 ESP8266 后以 `+IPD,<id>,<len>:` 形式经 UART 转发给 STM32。STM32 解析 HTTP method、path 和 query string 后控制 LED，再通过 `AT+CIPSEND=<id>,<length>` 返回 JSON 响应，并关闭连接。

启动流程：

1. STM32 初始化 SysTick、LED GPIO 和 USART1。
2. STM32 发送 `AT`、`ATE0`、`AT+CWMODE=1`。
3. 尝试 `AT+CWHOSTNAME="smart-home-stm32"`。
4. 通过 `AT+CWJAP` 连接 Wi-Fi。
5. 发送 `AT+CIFSR` 查询 IP。
6. 发送 `AT+CIPMUX=1`。
7. 发送 `AT+CIPSERVER=1,80`。
8. 主循环持续处理 ESP8266 UART 接收缓冲区中的 `+IPD` 请求。
