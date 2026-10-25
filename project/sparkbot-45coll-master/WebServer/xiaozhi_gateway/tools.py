from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from .config import Config

LOGGER = logging.getLogger(__name__)
ROOT_ALIASES = {"桌面": "desktop", "文档": "documents", "下载": "downloads", "项目": "project", "工程": "project"}


class ToolClient:
    def __init__(self, config: Config):
        self._config = config
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=2.0), trust_env=False)

    async def close(self) -> None:
        await self._client.aclose()

    async def invoke(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self._config.tool_bridge_url:
            return {"ok": False, "error": "tool bridge disabled"}
        response = await self._client.post(f"{self._config.tool_bridge_url}/invoke", json={"tool": tool, "arguments": arguments})
        response.raise_for_status()
        return response.json()

    async def collect_context(self, user_text: str) -> str:
        calls = plan_tool_calls(user_text)
        blocks = []
        for tool, arguments in calls:
            try:
                data = await self.invoke(tool, arguments)
                blocks.append(format_tool_result(tool, arguments, data))
            except Exception as exc:
                LOGGER.warning("tool %s failed: %s", tool, exc)
                blocks.append(f"工具 {tool} 调用失败: {exc}")
        return "\n\n".join(blocks)


def plan_tool_calls(text: str) -> list[tuple[str, dict[str, Any]]]:
    root = next((value for key, value in ROOT_ALIASES.items() if key in text), "desktop")
    host_port = re.search(r"((?:\d{1,3}\.){3}\d{1,3}|[\w.-]+\.[A-Za-z]{2,})[:：](\d{1,5})", text)
    if host_port and any(word in text for word in ("端口", "开放", "能不能连", "通不通")):
        return [("scan_port", {"host": host_port.group(1), "port": int(host_port.group(2))})]
    url = extract_url(text)
    if url and any(word in text for word in ("访问", "读取", "网页", "接口", "内容", "返回", "状态", "health")):
        return [("fetch_url", {"url": url})]
    if any(word in text.lower() for word in ("ping", "连通", "是否在线", "在线吗")):
        host = extract_host(text)
        return [("ping_host", {"host": host})] if host else []
    if any(word in text.lower() for word in ("解析域名", "域名解析", "dns")):
        host = extract_host(text)
        return [("dns_lookup", {"host": host})] if host else []
    if any(word in text for word in ("有哪些文件", "有什么文件", "列出文件", "文件列表", "目录里")):
        return [("list_files", {"root": root, "path": ""})]
    query = after_keyword(text, ("搜索文件", "查找文件", "找文件", "搜索", "查找"))
    if query:
        return [("search_files", {"root": root, "query": cleanup(query), "limit": 20})]
    if any(word in text for word in ("读取", "看看", "文件内容", "总结文件")):
        path = extract_path(text)
        return [("read_file", {"root": root, "path": path})] if path else []
    return []


def after_keyword(text: str, words: tuple[str, ...]) -> str:
    for word in words:
        if word in text:
            return text.split(word, 1)[1].strip(" ，。！？?")
    return ""


def extract_url(text: str) -> str:
    match = re.search(r"https?://[^\s，。！？?]+", text, re.I)
    if match:
        return match.group(0)
    match = re.search(r"((?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?(?:/[^\s，。！？?]*)?)", text)
    return match.group(1) if match else ""


def extract_host(text: str) -> str:
    url = extract_url(text)
    return re.sub(r"^https?://", "", url, flags=re.I).split("/")[0].split(":")[0] if url else ""


def extract_path(text: str) -> str:
    match = re.search(r"([\w\u4e00-\u9fff ._\\/-]+\.(?:txt|md|py|js|json|yml|c|cpp|h|html|css|csv|log))", text, re.I)
    return match.group(1).strip() if match else ""


def cleanup(text: str) -> str:
    for word in ("桌面", "文档", "下载", "项目", "工程", "里面", "文件", "帮我", "请"):
        text = text.replace(word, " ")
    return re.sub(r"\s+", " ", text).strip()


def format_tool_result(tool: str, arguments: dict[str, Any], data: dict[str, Any]) -> str:
    if not data.get("ok"):
        return f"工具 {tool} 返回错误: {data.get('error', 'unknown error')}"
    result = json.dumps(data.get("result"), ensure_ascii=False, indent=2)[:8000]
    return f"工具结果: {tool}({json.dumps(arguments, ensure_ascii=False)})\n{result}"


def with_tool_context(user_text: str, context: str) -> str:
    if not context:
        return user_text
    return (
        "以下是电脑工具读取到的真实信息。请根据结果用简短中文口语回答，不使用 Markdown、表格或代码块。"
        "先说结论，最多列出八个关键结果；内容很多时提示用户继续追问。\n\n"
        f"{context}\n\n用户问题: {user_text}"
    )
