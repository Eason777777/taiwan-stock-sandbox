#!/usr/bin/env python3
"""Clean raw stock data into the import format.

Input format:
  - file: data_import_tool/raw_data/stock.csv
  - encoding: UTF-16 LE
  - delimiter: tab

Output default:
  data_import_tool/clean_data/stock.tsv
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


DEFAULT_INPUT = RAW_DATA_DIR / "stock.csv"
DEFAULT_OUTPUT = CLEAN_DATA_DIR / "stock.tsv"

RAW_ENCODING = "utf-16-le"
RAW_DELIMITER = "\t"
EMPTY_VALUES = {"", ".", "N.A.", "N.A", "NA", "n.a.", "n.a", "null", "NULL"}

OUTPUT_COLUMNS = [
    "stock_id",
    "stock_name_zh",
    "stock_full_name_zh",
    "stock_name_en",
    "stock_full_name_en",
    "market_type",
    "sector_name",
    "listing_date",
    "par_value",
    "phone",
    "address",
    "website",
]

RAW_COLUMNS = {
    "stock_code": "證券代碼",
    "market_type": "上市別",
    "listing_date": "最近上市日",
    "par_value": "面額",
    "phone": "電話",
    "website": "網址",
    "sector_name": "TSE產業_名稱",
    "stock_full_name_zh": "公司中文全稱",
    "stock_full_name_en": "公司英文全稱",
    "stock_name_zh": "公司中文簡稱",
    "stock_name_en": "公司英文簡稱",
    "address": "公司中文地址",
}

MARKET_TYPE_MAP = {
    "TSE": "TSE",
    "OTC": "OTC",
    "ROTC": "EMERGING",
    "REG": "EMERGING",
    "EMERGING": "EMERGING",
    "INDEX": "INDEX",
}

MAX_LENGTHS = {
    "stock_id": 16,
    "stock_name_zh": 64,
    "stock_full_name_zh": 128,
    "stock_name_en": 64,
    "stock_full_name_en": 128,
    "sector_name": 64,
    "phone": 32,
    "address": 255,
    "website": 255,
}


def clean_text(value: str | None) -> str:
    text = (value or "").strip()
    return "" if text in EMPTY_VALUES else text


def truncate(value: str, max_length: int) -> str:
    return value[:max_length] if len(value) > max_length else value


def parse_date(value: str | None) -> str:
    text = clean_text(value)
    if not text:
        return ""

    for fmt in ("%Y%m%d", "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ImportToolError(f"Invalid date: {text!r}")


def parse_decimal(value: str | None) -> str:
    text = clean_text(value)
    if not text:
        return ""
    return text.replace(",", "")


def extract_stock_id(value: str | None) -> str:
    text = clean_text(value)
    if not text:
        return ""

    first_token = text.split()[0].strip("*,.()[]")
    if first_token:
        return first_token

    match = re.search(r"[A-Za-z]?\d{1,6}", text)
    return match.group(0) if match else text


def normalize_market_type(value: str | None) -> str:
    text = clean_text(value)
    market_type = MARKET_TYPE_MAP.get(text)
    if market_type is None:
        raise ImportToolError(f"Unsupported market_type: {text!r}")
    return market_type


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {
        "stock_id": extract_stock_id(row.get(RAW_COLUMNS["stock_code"], "")),
        "stock_name_zh": clean_text(row.get(RAW_COLUMNS["stock_name_zh"], "")),
        "stock_full_name_zh": clean_text(row.get(RAW_COLUMNS["stock_full_name_zh"], "")),
        "stock_name_en": clean_text(row.get(RAW_COLUMNS["stock_name_en"], "")),
        "stock_full_name_en": clean_text(row.get(RAW_COLUMNS["stock_full_name_en"], "")),
        "market_type": normalize_market_type(row.get(RAW_COLUMNS["market_type"], "")),
        "sector_name": clean_text(row.get(RAW_COLUMNS["sector_name"], "")),
        "listing_date": parse_date(row.get(RAW_COLUMNS["listing_date"], "")),
        "par_value": parse_decimal(row.get(RAW_COLUMNS["par_value"], "")),
        "phone": clean_text(row.get(RAW_COLUMNS["phone"], "")),
        "address": clean_text(row.get(RAW_COLUMNS["address"], "")),
        "website": clean_text(row.get(RAW_COLUMNS["website"], "")),
    }

    if not normalized["stock_id"]:
        raise ImportToolError(f"Missing stock_id in row: {row}")
    if not normalized["stock_name_zh"]:
        raise ImportToolError(f"Missing stock_name_zh for stock_id={normalized['stock_id']}")
    if not normalized["stock_full_name_zh"]:
        normalized["stock_full_name_zh"] = normalized["stock_name_zh"]

    for column, max_length in MAX_LENGTHS.items():
        normalized[column] = truncate(normalized[column], max_length)

    return normalized


def index_row() -> dict[str, str]:
    return {
        "stock_id": "Y9999",
        "stock_name_zh": "加權指數",
        "stock_full_name_zh": "臺灣證券交易所發行量加權股價指數",
        "stock_name_en": "TAIEX",
        "stock_full_name_en": "Taiwan Capitalization Weighted Stock Index",
        "market_type": "INDEX",
        "sector_name": "INDEX",
        "listing_date": "1967-01-05",
        "par_value": "",
        "phone": "",
        "address": "",
        "website": "https://www.twse.com.tw",
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


def clean_stock(
    input_path: Path,
    output_path: Path,
    limit: int | None,
    include_index: bool,
    logger: Logger,
) -> int:
    logger.section("clean_stock")
    logger.write(f"Started at: {timestamp()}")
    logger.write(f"Input: {input_path}")
    logger.write(f"Input encoding: {RAW_ENCODING}")
    logger.write("Input delimiter: tab")
    logger.write(f"Output: {output_path}")
    logger.write(f"Limit: {limit if limit is not None else 'all'}")

    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    duplicate_count = 0

    for row in limited(read_raw_rows(input_path), limit):
        stock_id = row["stock_id"]
        if stock_id in seen_ids:
            duplicate_count += 1
            continue
        seen_ids.add(stock_id)
        rows.append(row)

    if include_index and "Y9999" not in seen_ids:
        rows.append(index_row())
        seen_ids.add("Y9999")
        logger.write("Added index row: Y9999")

    write_clean_rows(rows, output_path)

    logger.write(f"Rows written: {len(rows)}")
    logger.write(f"Duplicates skipped: {duplicate_count}")
    logger.write("Sample:")
    for row in rows[:5]:
        logger.write(str(row))

    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean raw stock data.")
    parser.add_argument("-f", "--filename", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("-l", "--limit", type=int)
    parser.add_argument("--no-index", action="store_true", help="Do not append the Y9999 index row.")
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

        clean_stock(input_path, output_path, args.limit, not args.no_index, logger)
    except ImportToolError as exc:
        return fail(str(exc), logger)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
