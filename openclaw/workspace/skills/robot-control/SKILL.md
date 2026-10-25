---
name: robot-control
description: Control the connected Xiaozhi SparkBot chassis for movement, stopping, dancing, and light effects.
---

# Robot Control

Use the local Xiaozhi gateway at `http://127.0.0.1:8000`.

- Treat stop and emergency-stop requests as highest priority.
- Movement commands must be short pulses and must end with `Stop`.
- Supported methods: `GoForward`, `GoBack`, `TurnLeft`, `TurnRight`, `Stop`, `Dance`, `SwitchLightMode`.
- Confirm only after the gateway reports that the command was sent.
- Never claim physical movement when the device is offline.
