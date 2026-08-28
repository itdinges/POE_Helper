from __future__ import annotations

import re
from pathlib import Path


PROFILE_RULES: dict[str, list[str]] = {
    "mapping": [
        "# Mapping profile",
        "Show",
        "    Class \"Waystones\" \"Currency\"",
        "    SetBorderColor 255 200 60",
        "    SetTextColor 255 255 255",
        "    SetFontSize 45",
        "",
        "Show",
        "    Class \"Maps\"",
        "    SetBorderColor 120 180 255",
        "    SetFontSize 42",
    ],
    "crafting": [
        "# Crafting profile",
        "Show",
        "    Rarity Rare",
        "    Class \"Equipment\"",
        "    SetBorderColor 255 140 40",
        "    SetFontSize 42",
        "",
        "Show",
        "    Class \"Currency\"",
        "    SetTextColor 120 255 120",
        "    SetFontSize 45",
    ],
    "league_start": [
        "# League start profile",
        "Show",
        "    Rarity >= Magic",
        "    SetBorderColor 180 180 255",
        "    SetFontSize 40",
        "",
        "Show",
        "    Class \"Currency\"",
        "    SetBorderColor 255 255 255",
        "    SetFontSize 45",
    ],
}

MANAGED_START = "# ==== POE Helper managed section start ===="
MANAGED_END = "# ==== POE Helper managed section end ===="
MANAGED_NAME_SUFFIX = "_managed"
MANAGED_BLOCK_PATTERN = re.compile(
    rf"\n?{re.escape(MANAGED_START)}.*?{re.escape(MANAGED_END)}\n?",
    re.DOTALL,
)
FILTER_NAME_PATTERN = re.compile(r"^#name:(.+)$", re.MULTILINE)


def _online_filters_path(root: Path) -> Path:
    return root / "My Games" / "Path of Exile 2" / "OnlineFilters"


def _default_directory_candidates() -> list[Path]:
    home = Path.home()
    roots = [
        home / "Documents",
        home / "Documenten",
        home / "OneDrive" / "Documents",
        home / "OneDrive" / "Documenten",
    ]
    return [_online_filters_path(root) for root in roots]


def _resolve_default_filter_directory() -> Path:
    candidates = [path for path in _default_directory_candidates() if path.exists() and path.is_dir()]
    if not candidates:
        return _default_directory_candidates()[0]

    def score(path: Path) -> tuple[int, int]:
        try:
            file_count = sum(1 for p in path.iterdir() if p.is_file())
        except OSError:
            file_count = 0
        has_files = 1 if file_count > 0 else 0
        return (has_files, file_count)

    return max(candidates, key=score)


def _append_managed_suffix(filter_text: str) -> str:
    def add_suffix(match: re.Match[str]) -> str:
        current_name = match.group(1).strip()
        if current_name.endswith(MANAGED_NAME_SUFFIX):
            return f"#name:{current_name}"
        return f"#name:{current_name}{MANAGED_NAME_SUFFIX}"

    return FILTER_NAME_PATTERN.sub(add_suffix, filter_text, count=1)


class FilterManager:
    """Manage local Path of Exile 2 filter files and rule profiles."""

    def __init__(
        self,
        filter_directory: str | None = None,
        documents_root: str | None = None,
        create_if_missing: bool = True,
    ) -> None:
        if filter_directory:
            self.filter_directory = Path(filter_directory).expanduser().resolve()
        else:
            if documents_root:
                self.filter_directory = _online_filters_path(Path(documents_root))
            else:
                self.filter_directory = _resolve_default_filter_directory()
        if self.filter_directory.exists() and not self.filter_directory.is_dir():
            raise NotADirectoryError(f"Filter path exists but is not a directory: {self.filter_directory}")
        if not self.filter_directory.exists():
            if create_if_missing:
                self.filter_directory.mkdir(parents=True, exist_ok=True)
            else:
                raise FileNotFoundError(f"Filter directory not found: {self.filter_directory}")

    def list_filters(self) -> list[str]:
        return sorted(p.name for p in self.filter_directory.iterdir() if p.is_file())

    def read_filter(self, filename: str) -> str:
        file_path = self.filter_directory / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Filter not found: {file_path}")
        return file_path.read_text(encoding="utf-8")

    def write_filter(self, filename: str, content: str) -> Path:
        file_path = self.filter_directory / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def build_default_rules(self) -> list[str]:
        return [
            "# Default rules placeholder",
            "# Add league-specific or build-specific logic here",
        ]

    def build_profile_rules(self, profile: str) -> list[str]:
        return PROFILE_RULES.get(profile, self.build_default_rules())

    def merge_filter_with_rules(self, base_filter_text: str, rules: list[str], profile: str) -> str:
        cleaned_text = MANAGED_BLOCK_PATTERN.sub("\n", base_filter_text).rstrip()
        section = [
            "",
            MANAGED_START,
            f"# profile: {profile}",
            *rules,
            MANAGED_END,
            "",
        ]
        return cleaned_text + "\n" + "\n".join(section)

    def create_managed_filter(self, source_filename: str, output_filename: str, profile: str) -> Path:
        base_text = self.read_filter(source_filename)
        base_text = _append_managed_suffix(base_text)
        rules = self.build_profile_rules(profile)
        merged_text = self.merge_filter_with_rules(base_text, rules, profile)
        return self.write_filter(output_filename, merged_text)
