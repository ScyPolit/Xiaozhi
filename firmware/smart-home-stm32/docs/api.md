# HTTP API

所有响应都包含：

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
Content-Type: application/json
Connection: close
```

## GET /api/health

返回设备状态：

```json
{
  "ok": true,
  "device": "STM32F103C8T6",
  "wifi": true,
  "hostname": "smart-home-stm32"
}
```

## GET /api/leds

返回 5 个 LED 当前状态：

```json
{
  "leds": [
    { "id": 1, "name": "客厅灯", "pin": "PA4", "state": false },
    { "id": 2, "name": "卧室灯", "pin": "PA5", "state": false },
    { "id": 3, "name": "厨房灯", "pin": "PA6", "state": false },
    { "id": 4, "name": "卫生间灯", "pin": "PA7", "state": false },
    { "id": 5, "name": "梳妆台灯", "pin": "PB0", "state": false },
    { "id": 6, "name": "空调", "pin": "PA15", "state": false }
  ]
}
```

## GET /api/led?id=1&state=on

打开指定 LED。`id` 范围为 1 到 5。

```json
{ "ok": true, "id": 1, "state": true }
```

## GET /api/led?id=1&state=off

关闭指定 LED。

```json
{ "ok": true, "id": 1, "state": false }
```

非法参数示例：

```json
{ "ok": false, "error": "Invalid led id" }
```

## GET /api/all?state=on

打开全部 LED。

```json
{ "ok": true, "state": true }
```

## GET /api/all?state=off

关闭全部 LED。

```json
{ "ok": true, "state": false }
```

## GET /api/ac?state=on

打开 PA15 蜂鸣器模块，用于模拟空调启动。

```json
{ "ok": true, "id": 6, "name": "空调", "pin": "PA15", "state": true }
```

## GET /api/ac?state=off

关闭 PA15 蜂鸣器模块，用于模拟空调关闭。

```json
{ "ok": true, "id": 6, "name": "空调", "pin": "PA15", "state": false }
```

## OPTIONS *

用于浏览器 CORS 预检，返回 `204 No Content`。
