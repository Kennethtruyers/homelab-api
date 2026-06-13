from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

Action = Literal["include", "exclude"]
Field = Literal["group", "name"]
DefaultAction = Literal["include", "exclude"]

RULES_PATH = Path(__file__).with_name("rules.yaml")


@dataclass(frozen=True)
class Rule:
    name: str
    action: Action
    field: Field
    pattern: str


@dataclass(frozen=True)
class PlaylistConfig:
    name: str
    description: str
    normalize_groups: bool
    default: DefaultAction
    rules: tuple[Rule, ...]


@dataclass(frozen=True)
class IptvConfig:
    interested_countries: frozenset[str]
    country_aliases: dict[str, str]
    playlists: dict[str, PlaylistConfig]


def load_config(path: Path = RULES_PATH) -> IptvConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    countries = raw.get("countries", {})
    interested = frozenset(countries.get("interested", []))
    aliases = {str(k): str(v) for k, v in countries.get("aliases", {}).items()}

    playlists: dict[str, PlaylistConfig] = {}
    for name, playlist in raw.get("playlists", {}).items():
        rules = tuple(
            Rule(
                name=str(rule.get("name", f"rule-{index}")),
                action=rule["action"],
                field=rule["field"],
                pattern=rule["pattern"],
            )
            for index, rule in enumerate(playlist.get("rules", []), start=1)
        )
        playlists[name] = PlaylistConfig(
            name=name,
            description=str(playlist.get("description", "")),
            normalize_groups=bool(playlist.get("normalize_groups", False)),
            default=playlist.get("default", "exclude"),
            rules=rules,
        )

    return IptvConfig(
        interested_countries=interested,
        country_aliases=aliases,
        playlists=playlists,
    )
