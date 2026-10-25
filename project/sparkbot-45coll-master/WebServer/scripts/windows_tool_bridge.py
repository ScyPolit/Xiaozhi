from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".html",
    ".css",
    ".xml",
    ".csv",
    ".log",
}
BLOCKED_COMMANDS = re.compile(
    r"\b(del|erase|rd|rmdir|remove-item|ren|rename-item|move-item|format|diskpart|shutdown|restart-computer|reg\s+delete)\b",
    re.IGNORECASE,
)
OFFICE_SITES = {
    "search": [
        {"name": "Bing 搜索", "url": "https://www.bing.com/search?q={query}"},
        {"name": "百度搜索", "url": "https://www.baidu.com/s?wd={query}"},
    ],
    "translate": [
        {"name": "百度翻译", "url": "https://fanyi.baidu.com/"},
        {"name": "有道翻译", "url": "https://fanyi.youdao.com/"},
        {"name": "DeepL", "url": "https://www.deepl.com/translator"},
    ],
    "docs": [
        {"name": "腾讯文档", "url": "https://docs.qq.com/"},
        {"name": "金山文档", "url": "https://www.kdocs.cn/"},
        {"name": "石墨文档", "url": "https://shimo.im/"},
    ],
    "pdf": [
        {"name": "iLovePDF", "url": "https://www.ilovepdf.com/zh-cn"},
        {"name": "Smallpdf", "url": "https://smallpdf.com/cn"},
        {"name": "PDF24", "url": "https://tools.pdf24.org/zh/"},
    ],
    "ocr": [
        {"name": "百度 AI 开放平台 OCR", "url": "https://ai.baidu.com/tech/ocr"},
        {"name": "OCR Space", "url": "https://ocr.space/"},
    ],
    "image": [
        {"name": "TinyPNG 图片压缩", "url": "https://tinypng.com/"},
        {"name": "Remove.bg 抠图", "url": "https://www.remove.bg/zh"},
        {"name": "Photopea 在线修图", "url": "https://www.photopea.com/"},
    ],
    "dev": [
        {"name": "JSON Formatter", "url": "https://jsonformatter.org/"},
        {"name": "Regex101", "url": "https://regex101.com/"},
        {"name": "Can I Use", "url": "https://caniuse.com/"},
    ],
    "meeting": [
        {"name": "腾讯会议", "url": "https://meeting.tencent.com/"},
        {"name": "飞书", "url": "https://www.feishu.cn/"},
        {"name": "钉钉", "url": "https://www.dingtalk.com/"},
    ],
    "storage": [
        {"name": "百度网盘", "url": "https://pan.baidu.com/"},
        {"name": "阿里云盘", "url": "https://www.aliyundrive.com/"},
        {"name": "坚果云", "url": "https://www.jianguoyun.com/"},
    ],
}


def default_roots(project_root: str | None = None) -> dict[str, Path]:
    home = Path.home()
    roots = {
        "desktop": windows_known_folder("Desktop") or home / "Desktop",
        "documents": windows_known_folder("Personal") or home / "Documents",
        "downloads": home / "Downloads",
    }
    if project_root:
        roots["project"] = Path(project_root)
    return {name: path.resolve() for name, path in roots.items() if path.exists()}


def windows_known_folder(name: str) -> Path | None:
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        ) as key:
            value, _ = winreg.QueryValueEx(key, name)
        expanded = os.path.expandvars(value)
        return Path(expanded)
    except Exception:
        return None


class ToolBridge:
    def __init__(self, roots: dict[str, Path], allow_commands: bool):
        self.roots = roots
        self.allow_commands = allow_commands

    def tools(self) -> dict[str, Any]:
        return {
            "tools": [
                {"name": "list_roots", "description": "列出允许访问的根目录"},
                {"name": "list_files", "description": "列出目录文件", "parameters": {"root": "desktop|documents|downloads|project", "path": "相对路径"}},
                {"name": "read_file", "description": "读取文本文件内容", "parameters": {"root": "desktop|documents|downloads|project", "path": "相对路径"}},
                {"name": "search_files", "description": "按文件名或文本内容搜索", "parameters": {"root": "desktop|documents|downloads|project", "query": "关键词"}},
                {"name": "file_info", "description": "查看文件大小和修改时间", "parameters": {"root": "desktop|documents|downloads|project", "path": "相对路径"}},
                {"name": "fetch_url", "description": "读取 HTTP/HTTPS 网页或局域网接口", "parameters": {"url": "网址或 IP 地址"}},
                {"name": "web_search", "description": "使用搜索引擎查询网页", "parameters": {"query": "搜索词", "engine": "bing|baidu"}},
                {"name": "ping_host", "description": "检测主机是否可达", "parameters": {"host": "IP 或域名"}},
                {"name": "scan_port", "description": "检测 TCP 端口是否开放", "parameters": {"host": "IP 或域名", "port": "端口"}},
                {"name": "dns_lookup", "description": "解析域名 IP", "parameters": {"host": "域名"}},
                {"name": "office_sites", "description": "列出日常办公常用工具站", "parameters": {"category": "search|translate|docs|pdf|ocr|image|dev|meeting|storage"}},
                {"name": "run_powershell", "description": "执行非破坏性 PowerShell 命令", "enabled": self.allow_commands},
            ],
            "roots": {name: str(path) for name, path in self.roots.items()},
        }

    def invoke(self, name: str, args: dict[str, Any]) -> Any:
        if name == "list_roots":
            return self.tools()["roots"]
        if name == "list_files":
            return self.list_files(str(args.get("root") or "desktop"), str(args.get("path") or ""))
        if name == "read_file":
            return self.read_file(str(args.get("root") or "desktop"), str(args.get("path") or ""))
        if name == "search_files":
            return self.search_files(
                str(args.get("root") or "desktop"),
                str(args.get("query") or ""),
                int(args.get("limit") or 20),
            )
        if name == "file_info":
            return self.file_info(str(args.get("root") or "desktop"), str(args.get("path") or ""))
        if name == "fetch_url":
            return self.fetch_url(str(args.get("url") or ""))
        if name == "web_search":
            return self.web_search(str(args.get("query") or ""), str(args.get("engine") or "bing"))
        if name == "ping_host":
            return self.ping_host(str(args.get("host") or ""))
        if name == "scan_port":
            return self.scan_port(str(args.get("host") or ""), int(args.get("port") or 80))
        if name == "dns_lookup":
            return self.dns_lookup(str(args.get("host") or ""))
        if name == "office_sites":
            return self.office_sites(str(args.get("category") or "all"), str(args.get("query") or ""))
        if name == "run_powershell":
            return self.run_powershell(str(args.get("command") or ""))
        raise ValueError(f"unknown tool: {name}")

    def resolve(self, root: str, relpath: str = "") -> Path:
        base = self.roots.get(root)
        if not base:
            raise ValueError(f"root not allowed: {root}")
        target = (base / relpath).resolve()
        if target != base and base not in target.parents:
            raise ValueError("path escapes allowed root")
        return target

    def list_files(self, root: str, relpath: str) -> list[dict[str, Any]]:
        target = self.resolve(root, relpath)
        if not target.exists():
            raise FileNotFoundError(str(target))
        if not target.is_dir():
            raise NotADirectoryError(str(target))
        items = []
        for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:200]:
            stat = child.stat()
            items.append(
                {
                    "name": child.name,
                    "path": str(child.relative_to(self.roots[root])),
                    "type": "dir" if child.is_dir() else "file",
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                }
            )
        return items

    def read_file(self, root: str, relpath: str) -> dict[str, Any]:
        target = self.resolve(root, relpath)
        if not target.is_file():
            raise FileNotFoundError(str(target))
        if target.suffix.lower() not in TEXT_SUFFIXES:
            raise ValueError(f"unsupported text suffix: {target.suffix}")
        data = target.read_bytes()[:200_000]
        text = data.decode("utf-8", errors="replace")
        return {"path": str(target), "truncated": target.stat().st_size > len(data), "text": text}

    def search_files(self, root: str, query: str, limit: int) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("empty query")
        base = self.resolve(root)
        query_lower = query.lower()
        matches: list[dict[str, Any]] = []
        for path in base.rglob("*"):
            if len(matches) >= max(1, min(limit, 100)):
                break
            try:
                rel = str(path.relative_to(base))
                if query_lower in path.name.lower():
                    matches.append({"path": rel, "type": "dir" if path.is_dir() else "file", "match": "name"})
                    continue
                if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES and path.stat().st_size <= 1_000_000:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    idx = text.lower().find(query_lower)
                    if idx >= 0:
                        snippet = text[max(0, idx - 80) : idx + len(query) + 120].replace("\n", " ")
                        matches.append({"path": rel, "type": "file", "match": "content", "snippet": snippet})
            except (OSError, UnicodeError):
                continue
        return matches

    def file_info(self, root: str, relpath: str) -> dict[str, Any]:
        target = self.resolve(root, relpath)
        stat = target.stat()
        return {
            "path": str(target),
            "type": "dir" if target.is_dir() else "file",
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }

    def fetch_url(self, url: str) -> dict[str, Any]:
        url = normalize_url(url)
        request = urllib.request.Request(url, headers={"User-Agent": "XiaozhiToolBridge/1.0"})
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read(500_000)
            content_type = response.headers.get("Content-Type", "")
            charset = response.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="replace")
            text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
            text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return {
                "url": response.geturl(),
                "status": response.status,
                "content_type": content_type,
                "text": text[:12000],
                "truncated": len(raw) >= 500_000 or len(text) > 12000,
            }

    def web_search(self, query: str, engine: str) -> dict[str, Any]:
        if not query.strip():
            raise ValueError("empty query")
        engine = engine.lower()
        if engine == "baidu":
            url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
        else:
            url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
        fetched = self.fetch_url(url)
        text = fetched.get("text", "")
        snippets = []
        for part in re.split(r"\s{2,}|(?<=。)", text):
            part = part.strip()
            if len(part) >= 20 and query[:2] in part:
                snippets.append(part[:240])
            if len(snippets) >= 8:
                break
        return {"query": query, "engine": engine, "url": url, "snippets": snippets or [text[:800]]}

    def ping_host(self, host: str) -> dict[str, Any]:
        host = clean_host(host)
        proc = subprocess.run(["ping", "-n", "2", host], text=True, capture_output=True, timeout=10)
        return {"host": host, "ok": proc.returncode == 0, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-1000:]}

    def scan_port(self, host: str, port: int) -> dict[str, Any]:
        host = clean_host(host)
        port = max(1, min(int(port), 65535))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)
            ok = sock.connect_ex((host, port)) == 0
        return {"host": host, "port": port, "open": ok}

    def dns_lookup(self, host: str) -> dict[str, Any]:
        host = clean_host(host)
        return {"host": host, "addresses": sorted({item[4][0] for item in socket.getaddrinfo(host, None)})}

    def office_sites(self, category: str, query: str = "") -> dict[str, Any]:
        category = category.lower()
        if category in ("all", "全部", ""):
            sites = OFFICE_SITES
        else:
            sites = {category: OFFICE_SITES.get(category, [])}
        encoded = urllib.parse.quote(query) if query else ""
        rendered: dict[str, Any] = {}
        for key, values in sites.items():
            rendered[key] = [
                {**item, "url": item["url"].format(query=encoded)}
                for item in values
            ]
        return rendered

    def run_powershell(self, command: str) -> dict[str, Any]:
        if not self.allow_commands:
            raise PermissionError("run_powershell is disabled")
        if BLOCKED_COMMANDS.search(command):
            raise PermissionError("blocked destructive command")
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            text=True,
            capture_output=True,
            timeout=20,
        )
        return {"returncode": proc.returncode, "stdout": proc.stdout[-12000:], "stderr": proc.stderr[-4000:]}


class Handler(BaseHTTPRequestHandler):
    bridge: ToolBridge

    def do_GET(self) -> None:
        if self.path == "/health":
            self.json({"ok": True})
        elif self.path == "/tools":
            self.json(self.bridge.tools())
        else:
            self.send_error(404, "not found")

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length") or "0")
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if self.path != "/invoke":
                self.send_error(404, "not found")
                return
            result = self.bridge.invoke(str(payload.get("tool") or ""), payload.get("arguments") or {})
            self.json({"ok": True, "result": result})
        except Exception as exc:
            self.json({"ok": False, "error": str(exc)}, status=400)

    def json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), fmt % args))


def normalize_url(url: str) -> str:
    url = url.strip().strip("。？?，,")
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("only http/https URLs are allowed")
    return url


def clean_host(host: str) -> str:
    host = host.strip().strip("。？?，,")
    if "://" in host:
        host = urllib.parse.urlparse(host).hostname or host
    return host


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=18790)
    parser.add_argument("--project-root", default=os.getenv("XIAOZHI_PROJECT_ROOT"))
    parser.add_argument("--allow-commands", action="store_true", default=os.getenv("XIAOZHI_ALLOW_COMMANDS") == "1")
    args = parser.parse_args()

    Handler.bridge = ToolBridge(default_roots(args.project_root), args.allow_commands)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"windows tool bridge listening on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
