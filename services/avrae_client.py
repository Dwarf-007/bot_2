"""services/avrae_client.py

Minimal Avrae HTTP client wrapper for a local Avrae runtime.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AvraeClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = str(base_url or "http://localhost:5000").rstrip("/")

    def ping(self) -> bool:
        if not self.base_url:
            return False
        try:
            req = Request(f"{self.base_url}/health", method="GET")
            with urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except (HTTPError, URLError, ValueError):
            return False

    def call(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("Avrae base URL is not configured.")
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        body = json.dumps(payload).encode("utf-8")
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except HTTPError as exc:
            raise RuntimeError(f"Avrae HTTP error: {exc.code} {exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"Avrae request failed: {exc.reason}") from exc

    def batch_commands(self, commands: list[str]) -> Dict[str, Any]:
        return self.call("commands/batch", {"commands": commands})
