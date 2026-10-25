# Smart Home Device Interface: LED + AC Simulator

This document describes the LAN API exposed by the STM32F103C8T6 + ESP8266-01S AT firmware for integration into a smart-home main system or an agent runtime.

## Device

- Device name: `smart-home-stm32`
- Current verified LAN address: `http://192.168.31.196/`
- Transport: HTTP over LAN Wi-Fi
- Wi-Fi module: ESP8266-01S running AT firmware
- MCU: STM32F103C8T6
- TCP server port: `80`
- Response format: JSON
- CORS: enabled
- Private Network Access preflight: enabled with `Access-Control-Allow-Private-Network: true`

Hostname and mDNS are best-effort only. If `http://smart-home-stm32` or `http://smart-home-stm32.local` does not resolve, use the router-assigned IP.

## Hardware Mapping

| Device ID | Name | GPIO | Active Level | Notes |
| --- | --- | --- | --- | --- |
| 1 | Living room light | PA4 | High | LED |
| 2 | Bedroom light | PA5 | High | LED |
| 3 | Kitchen light | PA6 | High | LED |
| 4 | Bathroom light | PA7 | High | LED |
| 5 | Dressing table light | PB0 | High | LED |
| 6 | AC simulator | PA15 | High pulse | Buzzer module |

PA15 is JTDI by default on STM32F103. The firmware disables JTAG and keeps SWD enabled so PA15 can be used as a GPIO while ST-LINK SWD programming still works.

AC buzzer behavior:

- AC on: PA15 buzzer sounds once for 1.0 second, then the pin returns low while the logical AC state remains on.
- AC off: PA15 buzzer sounds twice. Each sound lasts 0.2 seconds, with a 0.4 second silent gap between them.
- The buzzer pattern is non-blocking; HTTP requests can still be processed while the sound pattern is running.

## Request Rules

- Send requests sequentially. Do not issue concurrent commands.
- Add a delay of 300 to 800 ms between commands when possible.
- Treat the ESP8266 AT bridge as a small single-connection edge device, even though `CIPMUX=1` is enabled.
- For UI systems, update local UI state after a control command is accepted or after the user action is sent, then reconcile with `GET /api/leds`.
- Timeout recommendation: 8 to 15 seconds.

## Headers

Firmware responses include:

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
Access-Control-Allow-Private-Network: true
Content-Type: application/json; charset=utf-8
Connection: close
```

Browsers served from `http://localhost` may send a Private Network Access preflight. The firmware returns HTTP `200` and `{}` for OPTIONS requests.

## Endpoints

### Health

```http
GET /api/health
```

Response:

```json
{
  "ok": true,
  "device": "STM32F103C8T6",
  "wifi": true,
  "hostname": "smart-home-stm32"
}
```

### Read All Device States

```http
GET /api/leds
```

Response:

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

The historical field name is `leds`; integration code should treat it as the device list for this controller.

### Set One Device

Turn on:

```http
GET /api/led?id=6&state=on
```

Turn off:

```http
GET /api/led?id=6&state=off
```

Response:

```json
{
  "ok": true,
  "id": 6,
  "state": true
}
```

### Set AC Simulator

Turn AC simulator on:

```http
GET /api/ac?state=on
```

Turn AC simulator off:

```http
GET /api/ac?state=off
```

Response:

```json
{
  "ok": true,
  "id": 6,
  "name": "空调",
  "pin": "PA15",
  "state": true
}
```

### Set All Devices

Turn all on:

```http
GET /api/all?state=on
```

Turn all off:

```http
GET /api/all?state=off
```

Response:

```json
{
  "ok": true,
  "state": true
}
```

## Agent Integration Contract

Suggested tool/action schemas:

```json
{
  "name": "set_device",
  "description": "Control one output device on the STM32 smart-home controller.",
  "parameters": {
    "id": "number, 1..6",
    "state": "boolean"
  }
}
```

```json
{
  "name": "set_ac",
  "description": "Control the PA15 buzzer used as an air-conditioner simulator.",
  "parameters": {
    "state": "boolean"
  }
}
```

```json
{
  "name": "set_all_devices",
  "description": "Turn all lights and the AC simulator on or off.",
  "parameters": {
    "state": "boolean"
  }
}
```

```json
{
  "name": "get_devices",
  "description": "Read all output states from the controller.",
  "parameters": {}
}
```

Recommended command flow:

1. Call `GET /api/health`.
2. Call `GET /api/leds` to build the current state.
3. For user commands, call `GET /api/led?id=<id>&state=on|off`, `GET /api/ac?state=on|off`, or `GET /api/all?state=on|off`.
4. Update local state immediately after command success.
5. Re-read `GET /api/leds` after 500 to 1000 ms for reconciliation.

## JavaScript Example

```js
const baseUrl = "http://192.168.31.196/";

async function request(path) {
  const response = await fetch(`${baseUrl}${path}`, { cache: "no-store" });
  const data = await response.json();
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

export async function getDevices() {
  return request("/api/leds");
}

export async function setDevice(id, state) {
  return request(`/api/led?id=${id}&state=${state ? "on" : "off"}`);
}

export async function setAc(state) {
  return request(`/api/ac?state=${state ? "on" : "off"}`);
}

export async function setAllDevices(state) {
  return request(`/api/all?state=${state ? "on" : "off"}`);
}
```

## Operational Notes

- If a command changes physical outputs but the client reports `Failed to fetch`, re-check browser Private Network Access preflight and use `GET /api/leds` to reconcile.
- If no endpoint responds, verify ESP8266 GPIO0 is high during boot, ESP8266 power is stable 3.3V, and STM32 USART1 wiring is PA9 TX to ESP RXD, PA10 RX to ESP TXD.
- If PA15 does not drive the buzzer, confirm the firmware has been rebuilt and flashed after adding the AC simulator, and confirm the buzzer module supports 3.3V input.
