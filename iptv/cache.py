from __future__ import annotations

import os
import threading
import time
from typing import Iterator

import requests

DEFAULT_CACHE_TTL = 3600
DEFAULT_FETCH_TIMEOUT = 300


class UpstreamCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._lines: list[str] | None = None
        self._fetched_at: float = 0.0

    def invalidate(self) -> None:
        with self._lock:
            self._lines = None
            self._fetched_at = 0.0

    def iter_lines(self, *, force_refresh: bool = False) -> Iterator[str]:
        lines = self._get_lines(force_refresh=force_refresh)
        yield from lines

    def _get_lines(self, *, force_refresh: bool) -> list[str]:
        ttl = int(os.getenv("IPTV_CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL)))
        now = time.time()

        with self._lock:
            if (
                not force_refresh
                and self._lines is not None
                and now - self._fetched_at < ttl
            ):
                return self._lines

        fetched = self._fetch_upstream()
        with self._lock:
            self._lines = fetched
            self._fetched_at = time.time()
            return self._lines

    def _fetch_upstream(self) -> list[str]:
        url = os.getenv("IPTV_UPSTREAM_URL", "").strip()
        if not url:
            raise RuntimeError("IPTV_UPSTREAM_URL is not configured")

        timeout = int(os.getenv("IPTV_FETCH_TIMEOUT_SECONDS", str(DEFAULT_FETCH_TIMEOUT)))
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"

        lines: list[str] = []
        for line in response.iter_lines(decode_unicode=True):
            if line is None:
                continue
            lines.append(line)
        return lines


upstream_cache = UpstreamCache()
