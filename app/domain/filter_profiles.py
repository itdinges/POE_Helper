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
        "Show",
    ]
    if grouped["show"]:
        for name in grouped["show"]:
            lines.append(f"    Class \"{name}\"")
    else:
        lines.append("    # no high-confidence entries")

    lines.extend(["", "Watch", ""])
    if grouped["watch"]:
        for name in grouped["watch"]:
            lines.append(f"    Class \"{name}\"")
    else:
        lines.append("    # no watch entries")

    lines.extend(["", "Hide", ""])
    if grouped["hide"]:
        for name in grouped["hide"]:
            lines.append(f"    Class \"{name}\"")
    else:
        lines.append("    # no hide entries")

    return lines
