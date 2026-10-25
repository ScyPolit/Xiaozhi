import os
import sys
import ctypes
import xml.etree.ElementTree as ET
from ctypes import wintypes


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def main() -> None:
    # sanity round-trip
    test = b"ping"
    tbuf = ctypes.create_string_buffer(test, len(test))
    tbi = DATA_BLOB(len(test), ctypes.cast(tbuf, ctypes.POINTER(ctypes.c_char)))
    tbo = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(tbi), None, None, None, None, 0, ctypes.byref(tbo)
    )
    if not ok:
        print("PROTECT failed", ctypes.GetLastError())
        sys.exit(1)
    t2 = ctypes.create_string_buffer(ctypes.string_at(tbo.pbData, tbo.cbData))
    tbi2 = DATA_BLOB(tbo.cbData, ctypes.cast(t2, ctypes.POINTER(ctypes.c_char)))
    tbo2 = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(tbi2), None, None, None, None, 0, ctypes.byref(tbo2)
    )
    if not ok or ctypes.string_at(tbo2.pbData, tbo2.cbData) != test:
        print("DPAPI round-trip FAILED err", ctypes.GetLastError())
        sys.exit(1)
    print("DPAPI round-trip OK")
    path = os.path.join(
        os.environ.get("TEMP", os.environ.get("TMP", "")),
        "wifiprof",
        "WLAN-momotang.xml",
    )
    root = ET.parse(path).getroot()
    vals = {}
    for el in root.iter():
        tag = el.tag.split("}")[-1].lower()
        if tag in ("keymaterial", "ssid", "name", "authentication", "encryption"):
            text = (el.text or "").strip()
            if text:
                vals.setdefault(tag, text)
    print("tags found:", sorted(vals.keys()))
    key = vals.get("keymaterial")
    if not key:
        print("NO keyMaterial")
        sys.exit(1)
    raw = bytes.fromhex(key)
    buf = ctypes.create_string_buffer(raw, len(raw))
    bi = DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    bo = DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(bi), None, None, None, None, 0, ctypes.byref(bo)
    )
    if not ok:
        print("CryptUnprotectData failed", ctypes.GetLastError())
        sys.exit(1)
    print("auth:", vals.get("authentication"), "enc:", vals.get("encryption"))
    print("SSID:", vals.get("ssid") or vals.get("name"))
    pwd = ctypes.string_at(bo.pbData, bo.cbData).decode("utf-8", errors="replace")
    print("PASSWORD:", pwd)


if __name__ == "__main__":
    main()
