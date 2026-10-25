---
name: smart-home
description: Control the Raspberry Pi or STM32 smart-home LED demo through the compatible local HTTP API.
---

# Smart Home

The controller API is selected through `SMART_HOME_URL`; the local demo defaults to `http://127.0.0.1:18880`.

- Health: `GET /api/health`
- State: `GET /api/leds`
- One light: `GET /api/led?id=1&state=on|off`
- All lights: `GET /api/all?state=on|off`
- Air-conditioner simulation: `GET /api/ac?state=on|off`

Room IDs are: 1 living room, 2 bedroom, 3 kitchen, 4 bathroom, 5 dressing table. Report offline status honestly.
