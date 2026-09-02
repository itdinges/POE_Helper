from __future__ import annotations

from app.domain.scoring import MarketItemScore


def build_score_profile_rules(scores: list[MarketItemScore]) -> list[str]:
    grouped: dict[str, list[str]] = {
        "show": [],
        "watch": [],
        "hide": [],
    }

    for score in scores:
        grouped.setdefault(score.recommendation, []).append(score.item_name)

    lines: list[str] = [
        "# score profile",
        "",
    ]

    for section_name, label in (("show", "Show"), ("hide", "Hide")):
        lines.append(label)
        items = grouped.get(section_name, [])
        if items:
            for name in items:
                lines.append(f'    BaseType "{name}"')
        else:
            lines.append(f"    # no {label.lower()} entries")
        lines.append("")

    if grouped.get("watch"):
        lines.append("# watch entries omitted from generated filter output")
        for name in grouped["watch"]:
            lines.append(f'    # watch: "{name}"')
        lines.append("")

    return lines
