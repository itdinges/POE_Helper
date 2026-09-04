from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


EXCHANGE_OVERVIEW_URL = "https://poe.ninja/poe2/api/economy/exchange/current/overview"
STASH_ITEM_OVERVIEW_URL = "https://poe.ninja/poe2/api/economy/stash/current/item/overview"


@dataclass(frozen=True)
class MarketTypeDefinition:
    display: str
    fetch: str
    fetch_url: str = EXCHANGE_OVERVIEW_URL


@dataclass(frozen=True)
class MarketTypeEntry:
    category: str
    name: str
    fetch_name: str
    fetch_url: str
    enabled: bool = True


@dataclass(frozen=True)
class MarketTypeConfig:
    items: list[MarketTypeDefinition]
    progression_types: list[MarketTypeDefinition]
    disabled_types: list[str]

    @classmethod
    def from_dict(cls, payload: dict) -> "MarketTypeConfig":
        def parse_definitions(items: list[object]) -> list[MarketTypeDefinition]:
            parsed: list[MarketTypeDefinition] = []
            for item in items:
                if isinstance(item, str):
                    value = item.strip()
                    if not value:
                        continue
                    parsed.append(
                        MarketTypeDefinition(
                            display=value,
                            fetch=value,
                            fetch_url=EXCHANGE_OVERVIEW_URL,
                        )
                    )
                    continue

                if isinstance(item, dict):
                    display_value = str(item.get("display", "")).strip()
                    fetch_value = str(item.get("fetch", "")).strip()
                    fetch_url = str(item.get("fetch_url", EXCHANGE_OVERVIEW_URL)).strip()
                    if not display_value or not fetch_value or not fetch_url:
                        continue
                    parsed.append(
                        MarketTypeDefinition(
                            display=display_value,
                            fetch=fetch_value,
                            fetch_url=fetch_url,
                        )
                    )
            return parsed

        return cls(
            items=parse_definitions(payload.get("items", payload.get("default_types", []))),
            progression_types=parse_definitions(payload.get("progression_types", [])),
            disabled_types=[str(item) for item in payload.get("disabled_types", [])],
        )

    @property
    def all_types(self) -> list[str]:
        all_types = list(self.items) + list(self.progression_types)
        seen: set[str] = set()
        ordered: list[str] = []
        for item in all_types:
            if item.display not in seen:
                ordered.append(item.display)
                seen.add(item.display)
        return ordered

    def entries(self) -> list[MarketTypeEntry]:
        entries: list[MarketTypeEntry] = []
        for category, names in (
            ("items", self.items),
            ("progression", self.progression_types),
        ):
            for name in names:
                entries.append(
                    MarketTypeEntry(
                        category=category,
                        name=name.display,
                        fetch_name=name.fetch,
                        fetch_url=name.fetch_url,
                        enabled=name.display not in self.disabled_types,
                    )
                )
        return entries

    def find_entry(self, value: str) -> MarketTypeEntry | None:
        needle = value.strip().lower()
        if not needle:
            return None

        for entry in self.entries():
            if entry.name.lower() == needle or entry.fetch_name.lower() == needle:
                return entry
        return None


def load_market_type_config(config_path: str | Path | None = None) -> MarketTypeConfig:
    file_path = Path(config_path) if config_path is not None else Path(__file__).resolve().parents[2] / "config" / "market_types.json"
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    return MarketTypeConfig.from_dict(raw)


def get_default_market_types(config_path: str | Path | None = None) -> list[str]:
    config = load_market_type_config(config_path)
    return [item.display for item in config.items if item.display not in config.disabled_types]


def get_optional_market_types(config_path: str | Path | None = None) -> list[str]:
    return []


def get_progression_market_types(config_path: str | Path | None = None) -> list[str]:
    config = load_market_type_config(config_path)
    return [item.display for item in config.progression_types if item.display not in config.disabled_types]


def get_market_types_for_category(config: MarketTypeConfig, category: str) -> list[str]:
    category_map = {
        "items": config.items,
        "default": config.items,
        "progression": config.progression_types,
    }
    names = category_map.get(category, [])
    return [item.display for item in names if item.display not in config.disabled_types]
