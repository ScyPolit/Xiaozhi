# 后端说明

后端使用 [`Node.js`](server.js) + [`Express`](server.js) + [`serialport`](serial.js) 实现，负责在浏览器和 STM32 串口之间做桥接。

## 目录说明

- [`package.json`](package.json)：依赖与启动脚本。
- [`config.js`](config.js)：端口和串口配置。
- [`serial.js`](serial.js)：串口通信、协议发送、状态解析、错误处理。
- [`server.js`](server.js)：HTTP API 服务入口。

## 安装依赖

```bash
npm install
```

## 启动方式

```bash
npm start
```

默认监听地址：

- `http://localhost:3000`

## 串口配置

默认配置位于 [`config.js`](config.js)：

```js
module.exports = {
  port: 3000,
  serialPort: process.env.SERIAL_PORT || "COM3",
  baudRate: 115200
};
```

### 平台示例

- Windows：`COM3`
- macOS：`/dev/tty.usbserial-xxxx`
- Linux：`/dev/ttyUSB0`

### 使用环境变量覆盖

#### Windows CMD

```cmd
set SERIAL_PORT=COM5 && npm start
```

#### PowerShell

```powershell
$env:SERIAL_PORT="COM5"; npm start
```

#### macOS / Linux

```bash
SERIAL_PORT=/dev/ttyUSB0 npm start
```

## API 列表

### [`GET /api/health`](server.js)

返回后端和串口健康状态。

示例响应：

```json
{
  "success": true,
  "message": "后端服务运行正常",
  "data": {
    "backendOnline": true,
    "stm32Online": true,
    "serialConnected": true,
    "serialPort": "COM3",
    "baudRate": 115200,
    "lastError": null
  }
}
```

### [`GET /api/leds`](server.js)

返回当前缓存的 LED 状态。

### [`GET /api/leds/status`](server.js)

主动向 STM32 发送 `STATUS` 命令，并返回实时状态。

### [`POST /api/leds/:id`](server.js)

设置单个 LED。

请求体：

```json
{
  "state": true
}
```

### [`POST /api/leds/all`](server.js)

设置全部 LED。

请求体：

```json
{
  "state": false
}
```

## 错误处理

后端已处理以下情况：

- 串口未连接
- 串口打开失败
- STM32 未响应
- STM32 返回 `ERR`
- 非法 LED ID
- 非法 `state` 参数
- 串口忙

所有错误均返回 JSON，例如：

```json
{
  "success": false,
  "message": "串口不可用，请检查设备连接与配置。当前串口：COM3"
}
```

## 调试建议

1. 先烧录 STM32 固件。
2. 用串口助手手动发送 `STATUS`，确认固件协议正常。
3. 再启动后端。
4. 浏览器访问前端页面进行联调。

## 注意事项

- 如果串口被占用，后端仍可启动，但调用控制接口会返回错误 JSON。
- 如果 STM32 固件没有正确响应换行结尾命令，后端会在超时后返回 `504` 错误。
- 如果你修改了协议格式，需要同步修改 [`serial.js`](serial.js) 中的解析逻辑。
