"""OpenAI-compatible client restricted to loopback and private network addresses."""

import ipaddress
import json
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

NETWORKS = tuple(map(ipaddress.ip_network, (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16",
    "fc00::/7", "fe80::/10",
)))
RESPONSE_LIMIT = 1024 * 1024


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def local_url(endpoint: str) -> str:
    url = urlsplit(endpoint)
    if (url.scheme not in {"http", "https"} or not url.hostname or "@" in url.netloc
            or url.query or url.fragment or url.path.rstrip("/") != "/v1"):
        raise ValueError("Endpoint must be a local HTTP(S) URL ending in /v1.")
    try:
        address = ipaddress.ip_address("127.0.0.1" if url.hostname == "localhost" else url.hostname)
    except ValueError:
        raise ValueError("Use localhost or a literal local IP for the endpoint.") from None
    if (getattr(address, "scope_id", None)
            or not (address.is_loopback or any(address in net for net in NETWORKS))):
        raise ValueError("Endpoint address must be loopback or on a private network.")
    host = f"[{address}]" if address.version == 6 else str(address)
    authority = host if url.port is None else f"{host}:{url.port}"
    return urlunsplit((url.scheme, authority, "/v1/chat/completions", "", ""))


class LocalModel:
    def __init__(self, endpoint: str, model: str):
        self.url = local_url(endpoint)
        self.model = model
        self.opener = build_opener(ProxyHandler({}), NoRedirects())

    def complete(self, messages: list, tools: list, max_tokens: int) -> tuple[dict, dict]:
        body = {
            "model": self.model, "messages": messages, "tools": tools, "temperature": 0.1,
            "max_tokens": max_tokens, "stream": False, "think": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        request = Request(self.url, data=json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with self.opener.open(request, timeout=180) as response:
                raw = response.read(RESPONSE_LIMIT + 1)
            if len(raw) > RESPONSE_LIMIT:
                raise ValueError("response exceeded 1 MiB")
            data = json.loads(raw)
            message = data["choices"][0]["message"]
            content = message.get("content")
            calls = message.get("tool_calls")
            if content is not None and not isinstance(content, str):
                raise ValueError("expected an assistant message")
            if calls is not None and not isinstance(calls, list):
                raise ValueError("expected a list of tool calls")
            clean = {"role": "assistant", "content": content or ""}
            for call in calls or []:
                function = call["function"]
                call_id, name, args = call["id"], function["name"], function["arguments"]
                if not all(isinstance(value, str) for value in (call_id, name, args)) or not call_id or not name:
                    raise ValueError("invalid tool call")
                clean.setdefault("tool_calls", []).append({
                    "id": call_id, "type": "function", "function": {"name": name, "arguments": args},
                })
            usage = data.get("usage")
            return clean, usage if isinstance(usage, dict) else {}
        except Exception as exc:
            raise RuntimeError(f"Local model request to {self.url} failed: {exc}") from exc
