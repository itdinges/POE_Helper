from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MarketTypeEntry:
    category: str
    name: str
    enabled: bool = True


@dataclass(frozen=True)
class MarketTypeConfig:
    default_types: list[str]
    optional_types: list[str]
    progression_types: list[str]
    equipment_types: list[str]
    disabled_types: list[str]

    @classmethod
    def from_dict(cls, payload: dict) -> "MarketTypeConfig":
        return cls(
            default_types=[str(item) for item in payload.get("default_types", [])],
            optional_types=[str(item) for item in payload.get("optional_types", [])],
            progression_types=[str(item) for item in payload.get("progression_types", [])],
            equipment_types=[str(item) for item in payload.get("equipment_types", [])],
            disabled_types=[str(item) for item in payload.get("disabled_types", [])],
        )

    @property
    def all_types(self) -> list[str]:
        all_types = list(self.default_types) + list(self.optional_types) + list(self.progression_types) + list(self.equipment_types)
        seen: set[str] = set()
        ordered: list[str] = []
        for item in all_types:
            if item not in seen:
                ordered.append(item)
                seen.add(item)
        return ordered

    def entries(self) -> list[MarketTypeEntry]:
        entries: list[MarketTypeEntry] = []
        for category, names in (
            ("default", self.default_types),
            ("optional", self.optional_types),
            ("progression", self.progression_types),
            ("equipment", self.equipment_types),
        ):
            for name in names:
                entries.append(MarketTypeEntry(category=category, name=name, enabled=name not in self.disabled_types))
        return entries


def load_market_type_config(config_path: str | Path | None = None) -> MarketTypeConfig:
    file_path = Path(config_path) if config_path is not None else Path(__file__).resolve().parents[2] / "config" / "market_types.json"
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    return MarketTypeConfig.from_dict(raw)


def get_default_market_types(config_path: str | Path | None = None) -> list[str]:
    config = load_market_type_config(config_path)
    return [item for item in config.default_types if item not in config.disabled_types]


def get_optional_market_types(config_path: str | Path | None = None) -> list[str]:
    config = load_market_type_config(config_path)
    return [item for item in config.optional_types if item not in config.disabled_types]


def get_progression_market_types(config_path: str | Path | None = None) -> list[str]:
    config = load_market_type_config(config_path)
    return [item for item in config.progression_types if item not in config.disabled_types]


def get_market_types_for_category(config: MarketTypeConfig, category: str) -> list[str]:
    category_map = {
        "default": config.default_types,
        "optional": config.optional_types,
        "progression": config.progression_types,
        "equipment": config.equipment_types,
    }
    names = category_map.get(category, [])
    return [item for item in names if item not in config.disabled_types]
