# 串口协议说明

本项目采用简单文本协议，便于使用串口调试助手、Node.js 后端和 STM32 固件进行联调。

## 基本规则

- 通信方式：UART 串口
- 波特率：`115200`
- 数据位：`8`
- 停止位：`1`
- 校验位：`None`
- 每条命令以换行符 `\n` 结尾
- 建议 STM32 返回使用 `\r\n`

## 命令列表

### 1. 设置单个灯

命令格式：

```text
SET <id> ON
SET <id> OFF
```

示例：

```text
SET 1 ON
SET 3 OFF
```

说明：

- `id` 取值范围：`1` 到 `5`
- `ON` 表示点亮
- `OFF` 表示熄灭

### 2. 设置全部灯

命令格式：

```text
ALL ON
ALL OFF
```

示例：

```text
ALL ON
```

### 3. 查询状态

命令格式：

```text
STATUS
```

## 响应格式

### 成功响应

对于 [`SET`](../firmware/Core/Src/usart_protocol.c:173) 和 [`ALL`](../firmware/Core/Src/usart_protocol.c:205) 命令，STM32 返回：

```text
OK
```

### 失败响应

当命令非法、参数错误或解析失败时，STM32 返回：

```text
ERR
```

### 状态响应

对于 [`STATUS`](../firmware/Core/Src/usart_protocol.c:121) 命令，STM32 返回：

```text
STATUS 1:ON 2:OFF 3:ON 4:OFF 5:OFF
```

## LED ID 映射

| LED ID | 灯名称 | 引脚 |
|---:|---|---|
| 1 | 客厅灯 | PA4 |
| 2 | 卧室灯 | PA5 |
| 3 | 厨房灯 | PA6 |
| 4 | 卫生间灯 | PA7 |
| 5 | 梳妆台灯 | PB0 |

## 完整交互示例

### 示例 1：打开客厅灯

主机发送：

```text
SET 1 ON
```

STM32 返回：

```text
OK
```

### 示例 2：关闭全部灯

主机发送：

```text
ALL OFF
```

STM32 返回：

```text
OK
```

### 示例 3：查询全部状态

主机发送：

```text
STATUS
```

STM32 返回：

```text
STATUS 1:ON 2:OFF 3:OFF 4:ON 5:OFF
```

## 非法命令示例

以下命令应返回：

```text
ERR
```

示例：

```text
SET 0 ON
SET 6 OFF
SET 1 HELLO
ALL MAYBE
PING
```

## 后端解析说明

后端在 [`backend/serial.js`](../backend/serial.js) 中负责：

- 发送命令
- 等待 STM32 响应
- 解析 [`STATUS`](../backend/serial.js) 返回内容
- 将结果转换为 JSON 返回给前端

## 调试建议

如果协议联调失败，请按以下顺序检查：

1. 使用串口助手手动发送 [`STATUS`](../backend/server.js)
2. 确认 STM32 能返回完整状态字符串
3. 确认每条命令都带换行符
4. 确认串口波特率为 `115200`
5. 确认没有其他调试日志混入协议串口
