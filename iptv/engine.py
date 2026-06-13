from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator

from iptv.config import IptvConfig, PlaylistConfig, Rule, load_config

GROUP_TITLE_RE = re.compile(r'group-title="([^"]*)"')
TVG_NAME_RE = re.compile(r'tvg-name="([^"]*)"')
EXTINF_DURATION_RE = re.compile(r"^#EXTINF:([^ ,]+)")
EXTINF_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
EU_PREFIX_RE = re.compile(r"^EU[\s-]*([A-Z]{2})\s*(.*)$", re.DOTALL)
VIP_US_PREFIX_RE = re.compile(r"^VIP US-\s*(.*)$", re.IGNORECASE | re.DOTALL)
DAY24_PREFIX_RE = re.compile(r"^24/7\|\s*([A-Z]{2})\s*(.*)$", re.DOTALL)
COUNTRY_PIPE_RE = re.compile(r"^([A-Z]{2,3})\s*\|\s*(.*)$", re.DOTALL)
NAME_COUNTRY_PIPE_RE = re.compile(
    r"^(BE|NL|ES|EN|UK|US)\s*(?:\||-)\s*(.*)$", re.IGNORECASE | re.DOTALL
)
NAME_COUNTRY_PREFIX_RE = re.compile(
    r"^(BE|NL|ES|EN|UK|US)\s+(.*)$", re.IGNORECASE | re.DOTALL
)
QUALITY_PREFIX_RE = re.compile(
    r"^(?:(\d+[kK](?:\s*UHD)?)|(FHD|HD|SD|UHD))[\s\-]+",
    re.IGNORECASE,
)
QUALITY_SUFFIX_RE = re.compile(
    r"\s+(4K|FHD|HD|SD|UHD)\b(?=\s*\(|\s*$)",
    re.IGNORECASE,
)
FIFA_GROUP_PREFIX_RE = re.compile(r"^FIFA\s+(.+)$", re.IGNORECASE)
FIFA_NAME_PREFIX_RE = re.compile(r"^FIFA\s+(?:WK26-\s*)?", re.IGNORECASE)
NAME_COUNTRY_SUFFIX_RE = re.compile(
    r"\s*\(([A-Z]{2,3}|Arg)\)\s*$", re.IGNORECASE
)
COUNTRY_SUFFIX_ALIASES = {"ARG": "AR"}


@dataclass(frozen=True)
class FilterStats:
    entries_in: int
    entries_out: int
    excluded: int


@dataclass(frozen=True)
class _ScannedEntry:
    url: str
    included: bool
    output_lines: tuple[str, ...] = ()


def _resolve_country_code(code: str, aliases: dict[str, str]) -> str:
    return aliases.get(code.upper(), code.upper())


def _parse_country_prefix(
    text: str, aliases: dict[str, str]
) -> tuple[str | None, str]:
    """Extract country from EU-, CC|, CC-, or CC-prefix forms."""
    stripped = text.strip()
    if not stripped:
        return None, stripped

    eu_match = EU_PREFIX_RE.match(stripped)
    if eu_match:
        return (
            _resolve_country_code(eu_match.group(1), aliases),
            eu_match.group(2).strip(),
        )

    vip_us_match = VIP_US_PREFIX_RE.match(stripped)
    if vip_us_match:
        return ("US", vip_us_match.group(1).strip())

    pipe_match = NAME_COUNTRY_PIPE_RE.match(stripped)
    if pipe_match:
        return (
            _resolve_country_code(pipe_match.group(1), aliases),
            pipe_match.group(2).strip(),
        )

    prefix_match = NAME_COUNTRY_PREFIX_RE.match(stripped)
    if prefix_match:
        return (
            _resolve_country_code(prefix_match.group(1), aliases),
            prefix_match.group(2).strip(),
        )

    return None, stripped


def extract_country(group_title: str, aliases: dict[str, str]) -> str | None:
    country, _ = _parse_country_prefix(group_title.strip(), aliases)
    if country:
        return country

    gt = group_title.strip()
    match = re.match(r"^24/7\|\s*([A-Z]{2})\b", gt, re.IGNORECASE)
    if match:
        return _resolve_country_code(match.group(1), aliases)
    return None


def normalize_group_title_with_aliases(
    group_title: str, country: str, aliases: dict[str, str]
) -> str:
    gt = group_title.strip()
    parsed_country, rest = _parse_country_prefix(gt, aliases)

    if parsed_country:
        country = parsed_country
    else:
        match = DAY24_PREFIX_RE.match(gt)
        if match:
            code = match.group(1).upper()
            country = _resolve_country_code(code, aliases)
            rest = match.group(2).strip()
            rest = f"24/7 {rest}".strip() if rest else "24/7"
        else:
            match = COUNTRY_PIPE_RE.match(gt)
            if match:
                country = _resolve_country_code(match.group(1), aliases)
                rest = match.group(2).strip()
            else:
                rest = gt

    rest = re.sub(r"\s+", " ", rest)
    return f"{country} | {rest}" if rest else country


def _country_codes_match(
    left: str, right: str, aliases: dict[str, str]
) -> bool:
    left_norm = aliases.get(left.upper(), left.upper())
    right_norm = aliases.get(right.upper(), right.upper())
    return left_norm == right_norm


def _normalize_quality_token(raw: str) -> str:
    token = raw.upper().replace(" ", "")
    if re.fullmatch(r"\d+K(?:UHD)?", token):
        return f"{token[0]}K"
    return token


def _parse_quality_prefix(rest: str) -> tuple[str | None, str]:
    match = QUALITY_PREFIX_RE.match(rest)
    if not match:
        return None, rest
    raw = match.group(1) or match.group(2) or ""
    return _normalize_quality_token(raw), rest[match.end() :].strip()


def _parse_quality_suffix(rest: str) -> tuple[str, str | None]:
    match = QUALITY_SUFFIX_RE.search(rest)
    if not match:
        return rest, None
    name = f"{rest[: match.start()]} {rest[match.end() :]}".strip()
    return name, match.group(1).upper()


def _format_channel_name(country: str | None, name: str, quality: str | None) -> str:
    parts = [part for part in (country, name, quality) if part]
    return " - ".join(parts)


def normalize_channel_name(
    name: str, country: str | None, aliases: dict[str, str]
) -> str:
    text = re.sub(r"\s+", " ", name.strip())
    if not text:
        return text

    name_country, rest = _parse_country_prefix(text, aliases)

    if name_country and country and not _country_codes_match(
        name_country, country, aliases
    ):
        return text

    output_country: str | None = None
    if name_country:
        output_country = name_country
    elif country:
        output_country = country

    quality_prefix, rest = _parse_quality_prefix(rest)
    rest, quality_suffix = _parse_quality_suffix(rest)
    quality = quality_prefix or quality_suffix
    name_part = re.sub(r"\s+", " ", rest).strip()

    if not any((output_country, name_part, quality)):
        return text

    formatted = _format_channel_name(output_country, name_part, quality)
    return formatted or text


def _parse_name_country_suffix(name: str) -> tuple[str | None, str]:
    match = NAME_COUNTRY_SUFFIX_RE.search(name)
    if not match:
        return None, name
    raw = match.group(1).upper()
    country = COUNTRY_SUFFIX_ALIASES.get(raw, raw)
    return country, name[: match.start()].strip()


def normalize_fifa_group_title(
    group_title: str, aliases: dict[str, str]
) -> str:
    country = extract_country(group_title, aliases)
    if country:
        return normalize_group_title_with_aliases(group_title, country, aliases)

    gt = group_title.strip()
    fifa_match = FIFA_GROUP_PREFIX_RE.match(gt)
    if fifa_match:
        rest = re.sub(r"\s+", " ", fifa_match.group(1)).strip()
        return f"FIFA | {rest}" if rest else "FIFA"
    return gt


def normalize_fifa_channel_name(
    name: str, group_title: str, aliases: dict[str, str]
) -> str:
    text = re.sub(r"\s+", " ", name.strip())
    if not text:
        return text

    group_country = extract_country(group_title, aliases)
    text = FIFA_NAME_PREFIX_RE.sub("", text).strip()
    name_country, text = _parse_name_country_suffix(text)

    country = name_country or group_country or "FIFA"
    if group_country and name_country and not _country_codes_match(
        group_country, name_country, aliases
    ):
        country = name_country

    quality_prefix, text = _parse_quality_prefix(text)
    text, quality_suffix = _parse_quality_suffix(text)
    quality = quality_prefix or quality_suffix
    name_part = re.sub(r"\s+", " ", text).strip()

    if not any((country, name_part, quality)):
        return name

    formatted = _format_channel_name(country, name_part, quality)
    return formatted or name


def parse_extinf_fields(extinf: str) -> tuple[str, str, str]:
    comma = extinf.find(",")
    display = extinf[comma + 1 :].strip() if comma != -1 else ""

    group_match = GROUP_TITLE_RE.search(extinf)
    name_match = TVG_NAME_RE.search(extinf)
    group_title = group_match.group(1) if group_match else ""
    stream_name = name_match.group(1) if name_match else display
    return group_title, stream_name, display


def format_m3u_entry(
    extinf: str, group_title: str, channel_name: str | None = None
) -> tuple[str, ...]:
    """Emit group-title first and add #EXTGRP for Dispatcharr-compatible parsing."""
    comma = extinf.find(",")
    if comma == -1:
        head, display = extinf, ""
    else:
        head, display = extinf[:comma], extinf[comma + 1 :].lstrip()

    if channel_name is not None:
        display = channel_name

    duration = "-1"
    duration_match = EXTINF_DURATION_RE.match(head)
    if duration_match:
        duration = duration_match.group(1)

    attrs: list[tuple[str, str]] = []
    has_tvg_name = False
    for key, value in EXTINF_ATTR_RE.findall(head):
        if key.lower() == "group-title":
            continue
        if key.lower() == "tvg-name":
            if channel_name is not None:
                value = channel_name
            has_tvg_name = True
        attrs.append((key, value))
    if channel_name is not None and not has_tvg_name:
        attrs.insert(0, ("tvg-name", channel_name))

    parts = [f"#EXTINF:{duration}", f'group-title="{group_title}"']
    parts.extend(f'{key}="{value}"' for key, value in attrs)
    extinf_line = " ".join(parts)
    if display:
        extinf_line += f",{display}"
    return (extinf_line, f"#EXTGRP:{group_title}")


class RuleEngine:
    def __init__(self, config: IptvConfig | None = None) -> None:
        self.config = config or load_config()
        self._compiled: dict[str, list[tuple[Rule, re.Pattern[str]]]] = {}
        for name, playlist in self.config.playlists.items():
            self._compiled[name] = [
                (rule, re.compile(rule.pattern)) for rule in playlist.rules
            ]

    def evaluate(
        self,
        playlist_name: str,
        group_title: str,
        stream_name: str,
        stream_url: str = "",
    ) -> bool:
        playlist = self.config.playlists[playlist_name]
        target_by_field = {
            "group": group_title or "",
            "name": stream_name or "",
            "url": stream_url or "",
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

            group_title, stream_name, display_name = parse_extinf_fields(extinf)
            included = self.evaluate(
                playlist_name, group_title, stream_name, stream_url=line
            )
            country = (
                extract_country(group_title, self.config.country_aliases)
                if included
                else None
            )
            final_group = group_title
            if included and playlist.normalize_groups:
                if playlist_name == "fifa":
                    final_group = normalize_fifa_group_title(
                        group_title, self.config.country_aliases
                    )
                elif country in self.config.interested_countries:
                    final_group = normalize_group_title_with_aliases(
                        group_title,
                        country,
                        self.config.country_aliases,
                    )

            final_name = display_name or stream_name
            if included and playlist.normalize_names:
                source_name = stream_name or display_name
                if playlist_name == "fifa":
                    final_name = normalize_fifa_channel_name(
                        source_name,
                        group_title,
                        self.config.country_aliases,
                    )
                elif country in self.config.interested_countries:
                    final_name = normalize_channel_name(
                        source_name, country, self.config.country_aliases
                    )

            output_lines: tuple[str, ...] = ()
            if included:
                if final_group:
                    output_lines = format_m3u_entry(
                        extinf, final_group, channel_name=final_name
                    )
                else:
                    output_lines = (extinf,)

            yield _ScannedEntry(
                url=line, included=included, output_lines=output_lines
            )
            extinf = None

    def iter_filtered_lines(
        self, lines: Iterator[str], playlist_name: str
    ) -> Iterator[str]:
        yield "#EXTM3U"
        for entry in self._scan_playlist(lines, playlist_name):
            if entry.included:
                yield from entry.output_lines
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
