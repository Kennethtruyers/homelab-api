from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

from iptv.config import IptvConfig, PlaylistConfig, Rule, load_config

GROUP_TITLE_RE = re.compile(r'group-title="([^"]*)"')
TVG_NAME_RE = re.compile(r'tvg-name="([^"]*)"')
EU_PREFIX_RE = re.compile(r"^EU[\s-]*([A-Z]{2})\s*(.*)$", re.DOTALL)
DAY24_PREFIX_RE = re.compile(r"^24/7\|\s*([A-Z]{2})\s*(.*)$", re.DOTALL)
COUNTRY_PIPE_RE = re.compile(r"^([A-Z]{2,3})\|\s*(.*)$", re.DOTALL)


@dataclass(frozen=True)
class FilterStats:
    entries_in: int
    entries_out: int
    excluded: int


@dataclass(frozen=True)
class _ScannedEntry:
    extinf: str
    url: str
    included: bool


def extract_country(group_title: str, aliases: dict[str, str]) -> str | None:
    gt = group_title.strip()
    match = COUNTRY_PIPE_RE.match(gt)
    if match:
        return match.group(1)
    match = re.match(r"^EU[\s-]*([A-Z]{2})\b", gt, re.IGNORECASE)
    if match:
        code = match.group(1).upper()
        return aliases.get(code, code)
    match = re.match(r"^24/7\|\s*([A-Z]{2})\b", gt, re.IGNORECASE)
    if match:
        code = match.group(1).upper()
        return aliases.get(code, code)
    return None


def normalize_group_title_with_aliases(
    group_title: str, country: str, aliases: dict[str, str]
) -> str:
    gt = group_title.strip()
    rest = ""

    match = EU_PREFIX_RE.match(gt)
    if match:
        code = match.group(1).upper()
        country = aliases.get(code, code)
        rest = match.group(2).strip()
    else:
        match = DAY24_PREFIX_RE.match(gt)
        if match:
            code = match.group(1).upper()
            country = aliases.get(code, code)
            rest = match.group(2).strip()
            rest = f"24/7 {rest}".strip() if rest else "24/7"
        else:
            match = COUNTRY_PIPE_RE.match(gt)
            if match:
                rest = match.group(2).strip()
            else:
                rest = gt

    rest = re.sub(r"\s+", " ", rest)
    return f"{country} | {rest}" if rest else country


def parse_extinf_fields(extinf: str) -> tuple[str, str]:
    group_match = GROUP_TITLE_RE.search(extinf)
    name_match = TVG_NAME_RE.search(extinf)
    group_title = group_match.group(1) if group_match else ""
    stream_name = name_match.group(1) if name_match else extinf
    return group_title, stream_name


def set_group_title(extinf: str, group_title: str) -> str:
    if GROUP_TITLE_RE.search(extinf):
        return GROUP_TITLE_RE.sub(f'group-title="{group_title}"', extinf, count=1)
    return extinf.replace("#EXTINF:", f'#EXTINF: group-title="{group_title}"', 1)


class RuleEngine:
    def __init__(self, config: IptvConfig | None = None) -> None:
        self.config = config or load_config()
        self._compiled: dict[str, list[tuple[Rule, re.Pattern[str]]]] = {}
        for name, playlist in self.config.playlists.items():
            self._compiled[name] = [
                (rule, re.compile(rule.pattern)) for rule in playlist.rules
            ]

    def evaluate(
        self, playlist_name: str, group_title: str, stream_name: str
    ) -> bool:
        playlist = self.config.playlists[playlist_name]
        target_by_field = {
            "group": group_title or "",
            "name": stream_name or "",
        }

        for rule, pattern in self._compiled[playlist_name]:
            target = target_by_field[rule.field]
            if pattern.search(target):
                return rule.action == "include"

        return playlist.default == "include"

    def _scan_playlist(
        self, lines: Iterator[str], playlist_name: str
    ) -> Iterator[_ScannedEntry]:
        if playlist_name not in self.config.playlists:
            raise KeyError(f"Unknown playlist: {playlist_name}")

        playlist = self.config.playlists[playlist_name]
        extinf: str | None = None

        for raw_line in lines:
            line = raw_line.rstrip("\n")
            if line.startswith("#EXTM3U"):
                continue
            if line.startswith("#EXTINF"):
                extinf = line
                continue
            if extinf is None or not line or line.startswith("#"):
                continue

            group_title, stream_name = parse_extinf_fields(extinf)
            included = self.evaluate(playlist_name, group_title, stream_name)
            if included and playlist.normalize_groups:
                country = extract_country(group_title, self.config.country_aliases)
                if country in self.config.interested_countries:
                    extinf = set_group_title(
                        extinf,
                        normalize_group_title_with_aliases(
                            group_title,
                            country,
                            self.config.country_aliases,
                        ),
                    )

            yield _ScannedEntry(extinf=extinf, url=line, included=included)
            extinf = None

    def iter_filtered_lines(
        self, lines: Iterator[str], playlist_name: str
    ) -> Iterator[str]:
        yield "#EXTM3U"
        for entry in self._scan_playlist(lines, playlist_name):
            if entry.included:
                yield entry.extinf
                yield entry.url

    def compute_stats(
        self, lines: Iterator[str], playlist_name: str
    ) -> FilterStats:
        entries_in = 0
        entries_out = 0
        for entry in self._scan_playlist(lines, playlist_name):
            entries_in += 1
            if entry.included:
                entries_out += 1
        return FilterStats(
            entries_in=entries_in,
            entries_out=entries_out,
            excluded=entries_in - entries_out,
        )
