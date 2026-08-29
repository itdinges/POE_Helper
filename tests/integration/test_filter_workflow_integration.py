from __future__ import annotations

from pathlib import Path

from app.application.services import build_filter, initialize_filter_manager, list_filters


def test_filter_workflow_end_to_end_replaces_managed_block(tmp_path: Path) -> None:
    source_name = "base_filter"
    managed_name = "base_filter_managed"
    source_file = tmp_path / source_name
    source_file.write_text(
        "\n".join(
            [
                "#Online Item Filter",
                "#name:Bow_Leveling",
                "Show",
                '    Class "Currency"',
            ]
        ),
        encoding="utf-8",
    )

    init_result, manager = initialize_filter_manager(str(tmp_path))
    assert init_result.ok is True
    assert manager is not None

    first_build = build_filter(manager, source_name, managed_name, "mapping")
    assert first_build.ok is True

    second_build = build_filter(manager, managed_name, managed_name, "crafting")
    assert second_build.ok is True

    list_result = list_filters(manager)
    assert list_result.ok is True
    assert source_name in list_result.filters
    assert managed_name in list_result.filters

    managed_text = (tmp_path / managed_name).read_text(encoding="utf-8")

    assert managed_text.count("# ==== POE Helper managed section start ====") == 1
    assert managed_text.count("# ==== POE Helper managed section end ====") == 1
    assert managed_text.count("#name:Bow_Leveling_managed") == 1
    assert "# profile: crafting" in managed_text
    assert "# profile: mapping" not in managed_text
