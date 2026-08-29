from __future__ import annotations

import logging
import time
from pathlib import Path


def configure_logging(log_level: str = "INFO", log_file: str = "data/logs/poe_helper.log") -> Path:
    log_path = Path(log_file).expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(_parse_level(log_level))

    # Reset handlers so repeated CLI calls do not duplicate log lines.
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.getLogger(__name__).debug("Logging configured", extra={"log_path": str(log_path)})
    return log_path


def tail_log_file(log_file: str, lines: int = 40, follow: bool = False, poll_seconds: float = 0.5) -> None:
    path = Path(log_file).expanduser().resolve()
    if not path.exists():
        print(f"Log file not found: {path}")
        return

    with path.open("r", encoding="utf-8") as handle:
        all_lines = handle.readlines()
        for line in all_lines[-max(1, lines):]:
            print(line.rstrip("\n"))

        if not follow:
            return

        while True:
            line = handle.readline()
            if line:
                print(line.rstrip("\n"))
            else:
                time.sleep(max(0.1, poll_seconds))


def _parse_level(log_level: str) -> int:
    value = (log_level or "INFO").strip().upper()
    if value in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        return getattr(logging, value)
    return logging.INFO
