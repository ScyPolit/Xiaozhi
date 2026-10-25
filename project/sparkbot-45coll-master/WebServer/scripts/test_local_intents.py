import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from xiaozhi_gateway.device_control import LocalIntent, parse_local_intent


CASES = {
    "请前进一点": LocalIntent("motion", "GoForward"),
    "向后退": LocalIntent("motion", "GoBack"),
    "马上停下": LocalIntent("motion", "Stop"),
    "打开客厅灯": LocalIntent("light", "on", 1),
    "关闭梳妆台的灯": LocalIntent("light", "off", 5),
    "把所有灯打开": LocalIntent("all_lights", "on"),
    "关闭空调": LocalIntent("ac", "off"),
}


for text, expected in CASES.items():
    actual = parse_local_intent(text)
    assert actual == expected, (text, actual, expected)

assert parse_local_intent("今天天气如何") is None
print(f"local intent tests passed: {len(CASES) + 1}")
