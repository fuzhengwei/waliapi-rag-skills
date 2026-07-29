#!/usr/bin/env python3
"""
WaLiAPI MCP Client — 通过 MCP JSON-RPC 协议调用 WaLiAPI 知识库工具。

用法:
    python3 mcp_call.py <tool_name> '<json_arguments>'
    python3 mcp_call.py list_knowledge_bases '{}'
    python3 mcp_call.py search_knowledge_base '{"query": "如何配置渠道"}'
    python3 mcp_call.py ask_knowledge_base '{"question": "WaLiAPI支持哪些协议？"}'

环境变量:
    WALIAPI_MCP_URL — MCP 服务地址（覆盖配置文件）
"""

import json
import sys
import os
import time
import urllib.request
import urllib.error
import threading
import queue

# ── Config ───────────────────────────────────────────────────────

CONFIG_PATH = os.path.expanduser("~/.qclaw/skills/waliapi-rag/config.json")
DEFAULT_MCP_URL = "http://127.0.0.1:8777/mcp"
SSE_TIMEOUT = 30  # seconds
REQUEST_TIMEOUT = 30  # seconds for POST


def get_mcp_url():
    """Get MCP server URL from env var, config file, or default."""
    # 1. Environment variable
    url = os.environ.get("WALIAPI_MCP_URL")
    if url:
        return url

    # 2. Config file
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
                url = config.get("mcp_url")
                if url:
                    return url
        except (json.JSONDecodeError, IOError):
            pass

    # 3. Default (will likely fail, but try)
    return DEFAULT_MCP_URL


# ── MCP SSE Client ───────────────────────────────────────────────

class McpSseClient:
    """
    MCP SSE transport client.
    
    Flow:
    1. Open SSE connection to GET /mcp/sse (or /mcp GET)
    2. Receive endpoint event with session_id
    3. POST JSON-RPC request to the endpoint
    4. Read response from SSE stream
    """

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        # Normalize: if URL ends with /mcp, derive SSE URL
        if self.base_url.endswith("/mcp"):
            self.sse_url = self.base_url + "/sse"
        elif self.base_url.endswith("/mcp/"):
            self.sse_url = self.base_url + "sse"
        else:
            self.sse_url = self.base_url
        self.session_id = None
        self.post_url = None
        self.response_queue = queue.Queue()
        self._sse_thread = None
        self._stop_event = threading.Event()

    def _read_sse_stream(self):
        """Background thread to read SSE events."""
        try:
            req = urllib.request.Request(self.sse_url, method="GET")
            req.add_header("Accept", "text/event-stream")
            req.add_header("Cache-Control", "no-cache")

            with urllib.request.urlopen(req, timeout=SSE_TIMEOUT) as resp:
                buffer = b""
                while not self._stop_event.is_set():
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\n\n" in buffer:
                        event_data, buffer = buffer.split(b"\n\n", 1)
                        self._parse_sse_event(event_data.decode("utf-8", errors="replace"))
        except Exception as e:
            if not self._stop_event.is_set():
                self.response_queue.put(("error", str(e)))

    def _parse_sse_event(self, raw):
        """Parse a single SSE event."""
        event_type = None
        data_lines = []

        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
            elif line.startswith(":"):
                pass  # comment/keepalive

        data = "\n".join(data_lines) if data_lines else ""

        if event_type == "endpoint":
            # endpoint event: data is the POST URL (relative)
            self.post_url = self._resolve_url(data)
            self.response_queue.put(("endpoint", self.post_url))
        elif data:
            # JSON-RPC response
            try:
                resp = json.loads(data)
                self.response_queue.put(("response", resp))
            except json.JSONDecodeError:
                pass  # ignore non-JSON SSE data

    def _resolve_url(self, path):
        """Resolve relative URL against base URL."""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        # Parse base URL
        from urllib.parse import urlparse
        parsed = urlparse(self.base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if path.startswith("/"):
            return base + path
        return base + "/" + path

    def connect(self):
        """Open SSE connection and wait for endpoint event."""
        self._sse_thread = threading.Thread(target=self._read_sse_stream, daemon=True)
        self._sse_thread.start()

        # Wait for endpoint event
        try:
            event_type, data = self.response_queue.get(timeout=SSE_TIMEOUT)
            if event_type == "endpoint":
                self.post_url = data
                return True
            elif event_type == "error":
                raise ConnectionError(f"SSE connection failed: {data}")
        except queue.Empty:
            raise TimeoutError("Timeout waiting for SSE endpoint event")
        return False

    def call_tool(self, tool_name, arguments):
        """Send tools/call JSON-RPC request and return result."""
        if not self.post_url:
            raise RuntimeError("Not connected: call connect() first")

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        body = json.dumps(request).encode("utf-8")
        req = urllib.request.Request(self.post_url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                status = resp.status
                # For SSE transport, response comes through SSE stream
                if status == 202:
                    # Wait for response on SSE stream
                    try:
                        event_type, data = self.response_queue.get(timeout=REQUEST_TIMEOUT)
                        if event_type == "response":
                            return data
                        elif event_type == "error":
                            raise ConnectionError(f"SSE error: {data}")
                    except queue.Empty:
                        raise TimeoutError("Timeout waiting for MCP response")
                else:
                    # Direct JSON response (non-SSE mode)
                    body = resp.read().decode("utf-8")
                    return json.loads(body)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise ConnectionError(f"HTTP {e.code}: {body}")

    def call_tool_direct(self, tool_name, arguments):
        """Call tool via direct POST (no SSE, simpler for single requests)."""
        url = self.base_url

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        body = json.dumps(request).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise ConnectionError(f"HTTP {e.code}: {body}")

    def close(self):
        """Close SSE connection."""
        self._stop_event.set()
        # Thread will exit on next read timeout


# ── Main ─────────────────────────────────────────────────────────

def format_result(result):
    """Format MCP response for display."""
    if not isinstance(result, dict):
        return str(result)

    # Check for error
    if "error" in result:
        err = result["error"]
        return f"❌ Error {err.get('code', '?')}: {err.get('message', 'Unknown error')}"

    # Extract content
    r = result.get("result", result)
    if not isinstance(r, dict):
        return json.dumps(r, ensure_ascii=False, indent=2)

    content = r.get("content", [])
    is_error = r.get("isError", False)

    if is_error:
        prefix = "⚠️ "
    else:
        prefix = ""

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item["text"])
            elif isinstance(item, dict):
                parts.append(json.dumps(item, ensure_ascii=False))
            else:
                parts.append(str(item))
        return prefix + "\n\n".join(parts)
    elif isinstance(content, str):
        return prefix + content
    else:
        return prefix + json.dumps(r, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mcp_call.py <tool_name> '<json_arguments>'")
        print("")
        print("Examples:")
        print("  python3 mcp_call.py list_knowledge_bases '{}'")
        print("  python3 mcp_call.py search_knowledge_base '{\"query\": \"如何配置渠道\"}'")
        print("  python3 mcp_call.py ask_knowledge_base '{\"question\": \"WaLiAPI支持哪些协议？\"}'")
        print("")
        print("Environment:")
        print("  WALIAPI_MCP_URL — Override MCP server URL")
        sys.exit(1)

    tool_name = sys.argv[1]
    args_str = sys.argv[2] if len(sys.argv) > 2 else "{}"

    # Parse arguments
    try:
        arguments = json.loads(args_str)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON arguments: {e}", file=sys.stderr)
        sys.exit(1)

    # Get MCP URL
    mcp_url = get_mcp_url()

    # Try direct POST first (simpler, works for WaLiAPI's /mcp endpoint)
    client = McpSseClient(mcp_url)

    try:
        result = client.call_tool_direct(tool_name, arguments)
        print(format_result(result))
    except Exception as e:
        # If direct POST fails, try SSE transport
        error_msg = str(e)
        if "202" in error_msg or "Accepted" in error_msg or "timeout" in error_msg.lower():
            # SSE transport needed
            try:
                client2 = McpSseClient(mcp_url)
                client2.connect()
                result = client2.call_tool(tool_name, arguments)
                print(format_result(result))
                client2.close()
            except Exception as e2:
                print(f"❌ MCP call failed (SSE): {e2}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"❌ MCP call failed: {error_msg}", file=sys.stderr)
            print(f"   MCP URL: {mcp_url}", file=sys.stderr)
            print(f"   Tool: {tool_name}", file=sys.stderr)
            print(f"   Args: {args_str}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
