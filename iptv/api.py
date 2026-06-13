from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from iptv.cache import UpstreamFetchError, upstream_cache
from iptv.config import RULES_PATH, load_config
from iptv.engine import RuleEngine

router = APIRouter()


def get_engine() -> RuleEngine:
    rules_path = Path(os.getenv("IPTV_RULES_PATH", str(RULES_PATH)))
    return RuleEngine(config=load_config(rules_path))


@router.get("/playlists")
async def list_playlists():
    config = get_engine().config
    return {
        name: {
            "description": playlist.description,
            "rules": len(playlist.rules),
            "normalize_groups": playlist.normalize_groups,
            "default": playlist.default,
            "endpoint": f"/iptv/{name}.m3u",
        }
        for name, playlist in config.playlists.items()
    }


@router.post("/cache/invalidate")
async def invalidate_cache():
    upstream_cache.invalidate()
    return {"status": "ok"}


@router.get("/upstream/status")
async def upstream_status():
    return upstream_cache.upstream_status()


@router.get("/upstream/probe")
async def upstream_probe():
    result = upstream_cache.probe_upstream()
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result)
    return result


@router.get("/{playlist_name}.m3u")
async def get_playlist(
    playlist_name: str,
    refresh: bool = Query(False, description="Bypass upstream cache"),
    include_stats: bool = Query(False, description="Add X-IPTV-* response headers"),
):
    if playlist_name not in get_engine().config.playlists:
        raise HTTPException(status_code=404, detail=f"Unknown playlist: {playlist_name}")

    if not os.getenv("IPTV_UPSTREAM_URL", "").strip():
        raise HTTPException(
            status_code=503,
            detail="IPTV_UPSTREAM_URL is not configured",
        )

    engine = get_engine()
    try:
        if include_stats:
            stats = engine.compute_stats(
                upstream_cache.iter_lines(force_refresh=refresh),
                playlist_name,
            )
            lines = upstream_cache.iter_lines(force_refresh=False)
        else:
            stats = None
            lines = upstream_cache.iter_lines(force_refresh=refresh)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UpstreamFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    headers: dict[str, str] = {}
    if stats is not None:
        headers = {
            "X-IPTV-Entries-In": str(stats.entries_in),
            "X-IPTV-Entries-Out": str(stats.entries_out),
            "X-IPTV-Entries-Excluded": str(stats.excluded),
        }

    def stream_playlist():
        for line in engine.iter_filtered_lines(lines, playlist_name):
            yield f"{line}\n"

    return StreamingResponse(
        stream_playlist(),
        media_type="audio/x-mpegurl",
        headers=headers,
    )
