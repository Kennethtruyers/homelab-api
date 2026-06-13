from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TTL = 3600
DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_READ_TIMEOUT = 600
DEFAULT_USER_AGENT = "VLC/3.0.20 LibVLC/3.0.20"


class UpstreamFetchError(RuntimeError):
    pass


class UpstreamCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fetched_at: float = 0.0
        self._session = self._build_session()
        self._raw_path = Path(
            os.getenv("IPTV_RAW_CACHE_PATH", "/tmp/iptv-upstream.m3u")
        )

    def invalidate(self) -> None:
        with self._lock:
            self._fetched_at = 0.0
            if self._raw_path.exists():
                self._raw_path.unlink()

    def iter_lines(self, *, force_refresh: bool = False) -> Iterator[str]:
        path = self._ensure_raw_file(force_refresh=force_refresh)
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                yield line.rstrip("\n")

    def probe_upstream(self) -> dict[str, Any]:
        url = os.getenv("IPTV_UPSTREAM_URL", "").strip()
        if not url:
            return {"ok": False, "error": "IPTV_UPSTREAM_URL is not configured"}

        parsed = urlparse(url)
        try:
            path = self._ensure_raw_file(force_refresh=True)
            preview: list[str] = []
            with path.open(encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    preview.append(line.rstrip("\n"))
                    if len(preview) >= 3:
                        break
        except (UpstreamFetchError, requests.RequestException, OSError) as exc:
            logger.warning("IPTV upstream probe failed for %s: %s", parsed.netloc, exc)
            return {
                "ok": False,
                "host": parsed.netloc,
                "scheme": parsed.scheme,
                "fetch_backend": self._fetch_backend(),
                "error": str(exc),
            }

        valid = bool(preview) and preview[0].startswith("#EXTM3U")
        return {
            "ok": valid,
            "host": parsed.netloc,
            "scheme": parsed.scheme,
            "fetch_backend": self._fetch_backend(),
            "preview": preview,
            "error": None if valid else "response is not a valid M3U playlist",
        }

    def upstream_status(self) -> dict[str, Any]:
        url = os.getenv("IPTV_UPSTREAM_URL", "").strip()
        parsed = urlparse(url) if url else None
        raw_exists = self._raw_path.exists()
        return {
            "configured": bool(url),
            "host": parsed.netloc if parsed else None,
            "fetch_backend": self._fetch_backend(),
            "raw_cache_path": str(self._raw_path),
            "raw_cache_exists": raw_exists,
            "raw_cache_bytes": self._raw_path.stat().st_size if raw_exists else None,
            "cache_age_seconds": (
                int(time.time() - self._fetched_at) if self._fetched_at else None
            ),
            "user_agent": os.getenv("IPTV_USER_AGENT") or None,
        }

    def _ensure_raw_file(self, *, force_refresh: bool) -> Path:
        ttl = int(os.getenv("IPTV_CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL)))
        now = time.time()

        with self._lock:
            if (
                not force_refresh
                and self._raw_path.exists()
                and self._fetched_at
                and now - self._fetched_at < ttl
            ):
                return self._raw_path

        try:
            self._download_upstream(self._raw_path)
        except requests.RequestException as exc:
            logger.warning("IPTV upstream fetch failed: %s", exc)
            raise UpstreamFetchError(f"upstream fetch failed: {exc}") from exc

        with self._lock:
            self._fetched_at = time.time()
            return self._raw_path

    def _fetch_backend(self) -> str:
        backend = os.getenv("IPTV_FETCH_BACKEND", "curl").lower()
        if backend == "curl" and shutil.which("curl") is None:
            logger.warning("curl not found, falling back to requests fetch backend")
            return "requests"
        return backend

    def _download_upstream(self, dest: Path) -> None:
        backend = self._fetch_backend()
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")

        if backend == "curl":
            self._download_with_curl(tmp)
        else:
            self._download_with_requests(tmp)

        self._validate_m3u_header(tmp)
        tmp.replace(dest)

    def _download_with_curl(self, dest: Path) -> None:
        url = os.getenv("IPTV_UPSTREAM_URL", "").strip()
        if not url:
            raise RuntimeError("IPTV_UPSTREAM_URL is not configured")

        read_timeout = int(
            os.getenv("IPTV_READ_TIMEOUT_SECONDS", str(DEFAULT_READ_TIMEOUT))
        )
        cmd = [
            "curl",
            "-fL",
            "--max-time",
            str(read_timeout),
            "-o",
            str(dest),
        ]
        user_agent = os.getenv("IPTV_USER_AGENT", "").strip()
        if user_agent:
            cmd.extend(["-A", user_agent])
        cmd.append(url)

        logger.info("Fetching IPTV upstream with curl")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "curl failed").strip()
            raise UpstreamFetchError(detail)

    def _download_with_requests(self, dest: Path) -> None:
        url = os.getenv("IPTV_UPSTREAM_URL", "").strip()
        if not url:
            raise RuntimeError("IPTV_UPSTREAM_URL is not configured")

        connect_timeout = int(
            os.getenv("IPTV_CONNECT_TIMEOUT_SECONDS", str(DEFAULT_CONNECT_TIMEOUT))
        )
        read_timeout = int(
            os.getenv("IPTV_READ_TIMEOUT_SECONDS", str(DEFAULT_READ_TIMEOUT))
        )

        logger.info("Fetching IPTV upstream with requests")
        with self._session.get(
            url,
            stream=True,
            timeout=(connect_timeout, read_timeout),
            headers=self._request_headers(),
        ) as response:
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"
            with dest.open("w", encoding="utf-8") as handle:
                for line in response.iter_lines(decode_unicode=True):
                    if line is None:
                        continue
                    handle.write(line)
                    handle.write("\n")

    def _validate_m3u_header(self, path: Path) -> None:
        with path.open(encoding="utf-8", errors="replace") as handle:
            first = handle.readline().strip()
        if first != "#EXTM3U":
            raise UpstreamFetchError("upstream response is not a valid M3U playlist")

    def _build_session(self) -> requests.Session:
        retries = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1,
            status_forcelist=(502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        session = requests.Session()
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))
        return session

    def _request_headers(self) -> dict[str, str]:
        headers = {"Accept": "*/*"}
        user_agent = os.getenv("IPTV_USER_AGENT", "").strip()
        if user_agent:
            headers["User-Agent"] = user_agent
        return headers


upstream_cache = UpstreamCache()
