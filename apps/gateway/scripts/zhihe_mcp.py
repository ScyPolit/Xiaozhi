from __future__ import annotations

import os
import shutil
import socket
import subprocess
import webbrowser
from pathlib import Path

import psutil
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("zhihe-windows")
HOME = Path.home()
ROOTS = {
    "desktop": HOME / "Desktop",
    "documents": HOME / "Documents",
    "downloads": HOME / "Downloads",
    "project": Path(os.getenv("XIAOZHI_PROJECT_ROOT", Path.cwd())).resolve(),
}
APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "settings": "ms-settings:",
    "terminal": "wt.exe",
    "paint": "mspaint.exe",
}


def safe_path(root: str, relative: str = "") -> Path:
    base = ROOTS.get(root)
    if not base:
        raise ValueError("root must be desktop, documents, downloads, or project")
    base = base.resolve()
    target = (base / relative).resolve()
    if target != base and base not in target.parents:
        raise ValueError("path leaves the allowed root")
    return target


@mcp.tool()
def system_status() -> dict:
    """Return current CPU, memory, battery, host name, and LAN addresses."""
    battery = psutil.sensors_battery()
    addresses = sorted({item.address for items in psutil.net_if_addrs().values() for item in items if item.family == socket.AF_INET})
    return {
        "host": socket.gethostname(),
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "memory_percent": psutil.virtual_memory().percent,
        "battery_percent": battery.percent if battery else None,
        "charging": battery.power_plugged if battery else None,
        "ipv4": addresses,
    }


@mcp.tool()
def launch_app(name: str) -> str:
    """Launch an approved Windows application: notepad, calculator, explorer, settings, terminal, or paint."""
    command = APPS.get(name.lower())
    if not command:
        raise ValueError(f"unsupported app; choose one of: {', '.join(APPS)}")
    if command.endswith(":"):
        os.startfile(command)
    else:
        executable = shutil.which(command) or command
        subprocess.Popen([executable], creationflags=subprocess.CREATE_NO_WINDOW)
    return f"launched {name}"


@mcp.tool()
def open_webpage(url: str) -> str:
    """Open an HTTP or HTTPS URL in the default browser."""
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("only http and https URLs are allowed")
    webbrowser.open(url)
    return f"opened {url}"


@mcp.tool()
def list_files(root: str = "desktop", relative: str = "") -> list[dict]:
    """List files under an approved user or project directory."""
    target = safe_path(root, relative)
    return [{"name": item.name, "type": "dir" if item.is_dir() else "file", "size": item.stat().st_size} for item in sorted(target.iterdir())[:100]]


@mcp.tool()
def search_files(query: str, root: str = "desktop", limit: int = 20) -> list[str]:
    """Search approved directories by file name."""
    if not query.strip():
        raise ValueError("query is required")
    base = safe_path(root)
    result = []
    for path in base.rglob("*"):
        if query.lower() in path.name.lower():
            result.append(str(path.relative_to(base)))
        if len(result) >= min(max(limit, 1), 50):
            break
    return result


@mcp.tool()
def clipboard_text() -> str:
    """Read current plain text from the Windows clipboard."""
    script = "Get-Clipboard -Raw -Format Text"
    result = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=5)
    return result.stdout[:10000]


@mcp.tool()
def take_screenshot(output_name: str = "zhihe-screenshot.png") -> str:
    """Capture all displays to a PNG in the Desktop folder."""
    if Path(output_name).name != output_name or not output_name.lower().endswith(".png"):
        raise ValueError("output_name must be a simple .png filename")
    target = (ROOTS["desktop"] / output_name).resolve()
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; "
        "$b=[System.Windows.Forms.SystemInformation]::VirtualScreen; "
        "$i=New-Object Drawing.Bitmap $b.Width,$b.Height; $g=[Drawing.Graphics]::FromImage($i); "
        "$g.CopyFromScreen($b.Left,$b.Top,0,0,$i.Size); "
        f"$i.Save('{str(target).replace("'", "''")}',[Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $i.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, timeout=15)
    return str(target)


if __name__ == "__main__":
    mcp.run(transport="stdio")
