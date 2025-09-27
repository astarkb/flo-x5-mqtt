"""Thin HTTP transport wrapper used by protocol adapters.

Keeps request details centralized and makes adapter code easier to test.
"""

from __future__ import annotations

import requests
from typing import Any


class Transport:
    def __init__(self, headers_provider: callable) -> None:
        self._headers_provider = headers_provider

    def get_json(self, url: str) -> Any:
        resp = requests.get(url, headers=self._headers_provider())
        if resp.status_code != 200:
            raise Exception(f"GET {url} failed", resp.status_code, resp.text)
        return resp.json()

