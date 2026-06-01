"""Common helpers for data cleaning and SQL API import scripts."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, TypeVar

import requests
from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
TOOL_DIR = SCRIPT_DIR.parent
RAW_DATA_DIR = TOOL_DIR / "raw_data"
CLEAN_DATA_DIR = TOOL_DIR / "clean_data"
LOG_DIR = SCRIPT_DIR / "log"

DEFAULT_SQL_API_URL = "http://sql-api.shiragaserver.lan/query"

T = TypeVar("T")


class ImportToolError(Exception):
    """Raised when a clean/import script cannot continue safely."""


def load_env() -> None:
    """Load environment variables from data_import_tool/.env if it exists."""
    load_dotenv(TOOL_DIR / ".env")


def get_sql_api_url() -> str:
    """Return SQL API URL from env, falling back to the team default."""
    load_env()
    return os.getenv("SQL_API_URL", DEFAULT_SQL_API_URL)


class Logger:
    """Write messages to stdout and optionally mirror them to a log file."""

    def __init__(self, out: str | Path | None = None, *, stdout: bool = True) -> None:
        self.out_path = Path(out) if out else None
        self.stdout = stdout
        if self.out_path is not None:
            if not self.out_path.is_absolute():
                self.out_path = TOOL_DIR / self.out_path
            self.out_path.parent.mkdir(parents=True, exist_ok=True)
            self.out_path.write_text("", encoding="utf-8")

    def write(self, message: str = "") -> None:
        if self.stdout:
            print(message)
        if self.out_path is not None:
            with self.out_path.open("a", encoding="utf-8") as file:
                file.write(message + "\n")

    def section(self, title: str) -> None:
        self.write()
        self.write(f"== {title} ==")

    def error(self, message: str) -> None:
        self.write(f"Error: {message}")


def timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def resolve_tool_path(path: str | Path) -> Path:
    """Resolve a path relative to data_import_tool when it is not absolute."""
    path = Path(path)
    return path if path.is_absolute() else TOOL_DIR / path


def limited(items: Iterable[T], limit: int | None = None, start: int = 0) -> Iterator[T]:
    """Yield items after a zero-based start offset, up to an optional limit."""
    if start < 0:
        raise ImportToolError("--start must be zero or a positive integer.")
    if limit is not None and limit < 0:
        raise ImportToolError("--limit must be zero or a positive integer.")

    end = None if limit is None else start + limit
    for index, item in enumerate(items):
        if index < start:
            continue
        if end is not None and index >= end:
            break
        yield item


def json_dumps(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def run_sql_api(sql: str, api_url: str | None = None, timeout: int = 60) -> dict:
    """Execute SQL through the team's HTTP SQL API."""
    url = api_url or get_sql_api_url()
    try:
        response = requests.post(url, json={"sql": sql}, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ImportToolError(f"SQL API request failed: {exc}") from exc

    try:
        result = response.json()
    except ValueError as exc:
        raise ImportToolError(f"SQL API returned non-JSON response: {response.text}") from exc

    if not result.get("ok", False):
        raise ImportToolError(f"SQL API returned ok=false: {json_dumps(result)}")

    return result


def fail(message: str, logger: Logger | None = None) -> int:
    """Print/log an error and return a process exit code."""
    if logger is None:
        print(f"Error: {message}", file=sys.stderr)
    else:
        logger.error(message)
    return 1
