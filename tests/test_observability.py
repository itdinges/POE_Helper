from __future__ import annotations

import logging
from pathlib import Path

from app.observability import configure_logging, tail_log_file


def test_configure_logging_creates_log_file_and_writes_message(tmp_path: Path) -> None:
    log_file = tmp_path / "logs" / "poe_helper.log"

    path = configure_logging(log_level="DEBUG", log_file=str(log_file))
    logger = logging.getLogger("test.observability")
    logger.info("hello observability")

    for handler in logging.getLogger().handlers:
        handler.flush()

    assert path == log_file.resolve()
    assert path.exists()
    contents = path.read_text(encoding="utf-8")
    assert "hello observability" in contents


def test_configure_logging_defaults_to_info_on_invalid_level(tmp_path: Path) -> None:
    log_file = tmp_path / "logs" / "invalid_level.log"

    configure_logging(log_level="not-a-level", log_file=str(log_file))

    assert logging.getLogger().level == logging.INFO


def test_tail_log_file_prints_last_lines(capsys, tmp_path: Path) -> None:
    log_file = tmp_path / "tail.log"
    log_file.write_text("line1\nline2\nline3\n", encoding="utf-8")

    tail_log_file(str(log_file), lines=2, follow=False)

    output = capsys.readouterr().out
    assert "line2" in output
    assert "line3" in output
    assert "line1" not in output


def test_tail_log_file_missing_file_message(capsys, tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.log"

    tail_log_file(str(missing), lines=5, follow=False)

    output = capsys.readouterr().out
    assert "Log file not found" in output
