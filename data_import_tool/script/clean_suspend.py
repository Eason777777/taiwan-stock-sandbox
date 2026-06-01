#!/usr/bin/env python3
"""Clean raw suspend-date data into the import format.

Input format:
  - file: data_import_tool/raw_data/20221230to20260601_suspend.csv
  - encoding: UTF-16 LE
  - delimiter: tab

Output default:
  data_import_tool/clean_data/suspend.tsv

Output columns:
  stock_id, suspend_start_date, resume_date, reason
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from pathlib import Path

from common import (
    CLEAN_DATA_DIR,
    RAW_DATA_DIR,
    ImportToolError,
    Logger,
    fail,
    limited,
    resolve_tool_path,
    timestamp,
)


DEFAULT_INPUT = RAW_DATA_DIR / "20221230to20260601_suspend.csv"
DEFAULT_OUTPUT = CLEAN_DATA_DIR / "suspend.tsv"

RAW_ENCODING = "utf-16-le"
RAW_DELIMITER = "\t"
RAW_COLUMNS = {
    "stock": "證券代碼",
    "start": "年月日",
    "resume": "恢復交易日",
    "reason": "暫停交易原因",
}

OUTPUT_COLUMNS = ["stock_id", "suspend_start_date", "resume_date", "reason"]
EMPTY_VALUES = {"", "N.A.", "N.A", "NA", "n.a.", "n.a", "null", "NULL"}


def parse_date(value: str | None) -> str:
    text = (value or "").strip()
    if text in EMPTY_VALUES:
        return ""

    for fmt in ("%Y%m%d", "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ImportToolError(f"Invalid date: {text!r}")


def extract_stock_id(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""

    first_token = text.split()[0].strip("*,.()[]")
    if first_token:
        return first_token

    match = re.search(r"[A-Za-z]?\d{1,6}", text)
    return match.group(0) if match else text


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    stock_id = extract_stock_id(row.get(RAW_COLUMNS["stock"], ""))
    suspend_start_date = parse_date(row.get(RAW_COLUMNS["start"], ""))
    resume_date = parse_date(row.get(RAW_COLUMNS["resume"], ""))
    reason = (row.get(RAW_COLUMNS["reason"], "") or "").strip()

    if not stock_id:
        raise ImportToolError(f"Missing stock_id in row: {row}")
    if not suspend_start_date:
        raise ImportToolError(f"Missing suspend_start_date in row: {row}")
    if not reason:
        raise ImportToolError(f"Missing reason in row: {row}")

    return {
        "stock_id": stock_id,
        "suspend_start_date": suspend_start_date,
        "resume_date": resume_date,
        "reason": reason,
    }


def read_raw_rows(path: Path):
    text = path.read_text(encoding=RAW_ENCODING)
    reader = csv.DictReader(text.splitlines(), delimiter=RAW_DELIMITER)
    if reader.fieldnames is None:
        raise ImportToolError(f"No header found in file: {path}")
    reader.fieldnames = [field.lstrip("\ufeff") for field in reader.fieldnames]

    missing = set(RAW_COLUMNS.values()) - set(reader.fieldnames)
    if missing:
        raise ImportToolError(f"Missing required columns: {sorted(missing)}")

    for row in reader:
        if not any((value or "").strip() for value in row.values()):
            continue
        yield normalize_row(row)


def write_clean_rows(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def clean_suspend(input_path: Path, output_path: Path, limit: int | None, logger: Logger) -> int:
    logger.section("clean_suspend")
    logger.write(f"Started at: {timestamp()}")
    logger.write(f"Input: {input_path}")
    logger.write(f"Input encoding: {RAW_ENCODING}")
    logger.write("Input delimiter: tab")
    logger.write(f"Output: {output_path}")
    logger.write(f"Limit: {limit if limit is not None else 'all'}")

    seen_keys: set[tuple[str, str]] = set()
    cleaned_rows: list[dict[str, str]] = []
    duplicate_count = 0

    for row in limited(read_raw_rows(input_path), limit):
        key = (row["stock_id"], row["suspend_start_date"])
        if key in seen_keys:
            duplicate_count += 1
            continue
        seen_keys.add(key)
        cleaned_rows.append(row)

    write_clean_rows(cleaned_rows, output_path)

    logger.write(f"Rows written: {len(cleaned_rows)}")
    logger.write(f"Duplicates skipped: {duplicate_count}")
    logger.write("Sample:")
    for row in cleaned_rows[:5]:
        logger.write(str(row))

    return len(cleaned_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean raw suspend-date data.")
    parser.add_argument("-f", "--filename", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-l", "--limit", type=int)
    parser.add_argument("-o", "--out", type=Path, help="Also write terminal output to this log file.")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print log output to the terminal.",
    )
    args = parser.parse_args()

    logger = None
    try:
        logger = Logger(args.out, stdout=not args.quiet)
        input_path = resolve_tool_path(args.filename)
        output_path = resolve_tool_path(args.output)

        if not input_path.exists():
            raise ImportToolError(f"Input file not found: {input_path}")
        if args.limit is not None and args.limit < 0:
            raise ImportToolError("--limit must be zero or a positive integer.")

        clean_suspend(input_path, output_path, args.limit, logger)
    except ImportToolError as exc:
        return fail(str(exc), logger)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
