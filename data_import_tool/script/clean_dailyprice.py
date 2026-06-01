#!/usr/bin/env python3
"""Clean raw daily price data into the import format.

Input format:
  - file: data_import_tool/raw_data/20221230to20260601_dailyprice.csv
    - encoding: CP950
  - delimiter: comma

Output default:
  data_import_tool/clean_data/dailyprice.tsv

Important TEJ rule:
  次日開盤參考價, 次日漲停價, 次日跌停價 from a row become the next
  trading day's ref_price, limit_up, limit_down for the same stock.
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import date, datetime
from pathlib import Path

from common import (
    CLEAN_DATA_DIR,
    LOG_DIR,
    RAW_DATA_DIR,
    ImportToolError,
    Logger,
    fail,
    resolve_tool_path,
    timestamp,
)


DEFAULT_INPUT = RAW_DATA_DIR / "20221230to20260601_dailyprice.csv"
DEFAULT_OUTPUT = CLEAN_DATA_DIR / "dailyprice.tsv"
DEFAULT_LOG = LOG_DIR / "clean_dailyprice.log"

RAW_ENCODING = "cp950"
RAW_DELIMITER = ","
START_DATE = date(2023, 1, 3)
END_DATE = date(2026, 6, 1)

RAW_COLUMNS = {
    "stock": "證券代碼",
    "date": "年月日",
    "open": "開盤價(元)",
    "high": "最高價(元)",
    "low": "最低價(元)",
    "close": "收盤價(元)",
    "volume": "成交量(千股)",
    "next_ref": "次日開盤參考價",
    "next_limit_up": "次日漲停價",
    "next_limit_down": "次日跌停價",
    "attention": "注意股票(A)",
    "disposition": "處置股票(D)",
    "full_delivery": "全額交割(Y)",
    "market": "市場別",
}

OUTPUT_COLUMNS = [
    "stock_id",
    "trade_date",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume",
    "ref_price",
    "limit_up",
    "limit_down",
    "is_attention",
    "is_disposition",
    "is_full_delivery",
]

EMPTY_VALUES = {"", ".", "N.A.", "N.A", "NA", "n.a.", "n.a", "null", "NULL"}


def clean_text(value: str | None) -> str:
    text = (value or "").strip()
    return "" if text in EMPTY_VALUES else text


def parse_date(value: str | None) -> date | None:
    text = clean_text(value)
    if not text:
        return None

    for fmt in ("%Y%m%d", "%Y/%m/%d", "%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    raise ImportToolError(f"Invalid date: {text!r}")


def format_date(value: date | None) -> str:
    return "" if value is None else value.strftime("%Y-%m-%d")


def extract_stock_id(value: str | None) -> str:
    text = clean_text(value)
    if not text:
        return ""

    first_token = text.split()[0].strip("*,.()[]")
    if first_token:
        return first_token

    match = re.search(r"[A-Za-z]?\d{1,6}", text)
    return match.group(0) if match else text


def parse_decimal(value: str | None, *, required: bool = False) -> str:
    text = clean_text(value)
    if not text:
        if required:
            raise ImportToolError("Missing required decimal value.")
        return ""
    return str(round(float(text.replace(",", "")), 2))


def parse_int(value: str | None, *, required: bool = False) -> str:
    text = clean_text(value)
    if not text:
        if required:
            raise ImportToolError("Missing required integer value.")
        return ""
    return str(int(float(text.replace(",", ""))))


def flag_to_bool(value: str | None) -> str:
    return "false" if clean_text(value).upper() == "N" else "true"


def load_listing_dates(stock_path: Path) -> dict[str, date]:
    if not stock_path.exists():
        raise ImportToolError(f"Stock clean file not found: {stock_path}")

    listing_dates: dict[str, date] = {}
    with stock_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        for row in reader:
            stock_id = clean_text(row.get("stock_id"))
            listing_date = parse_date(row.get("listing_date"))
            if stock_id and listing_date:
                listing_dates[stock_id] = listing_date
    return listing_dates


def read_raw_rows(path: Path):
    with path.open("r", encoding=RAW_ENCODING, newline="") as file:
        reader = csv.DictReader(file, delimiter=RAW_DELIMITER)
        if reader.fieldnames is None:
            raise ImportToolError(f"No header found in file: {path}")

        missing = set(RAW_COLUMNS.values()) - set(reader.fieldnames)
        if missing:
            raise ImportToolError(f"Missing required columns: {sorted(missing)}")

        for line_no, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            yield line_no, row


def make_output_row(raw_row: dict[str, str], prev_row: dict[str, str] | None) -> dict[str, str]:
    return {
        "stock_id": extract_stock_id(raw_row.get(RAW_COLUMNS["stock"])),
        "trade_date": format_date(parse_date(raw_row.get(RAW_COLUMNS["date"]))),
        "open_price": parse_decimal(raw_row.get(RAW_COLUMNS["open"]), required=True),
        "high_price": parse_decimal(raw_row.get(RAW_COLUMNS["high"]), required=True),
        "low_price": parse_decimal(raw_row.get(RAW_COLUMNS["low"]), required=True),
        "close_price": parse_decimal(raw_row.get(RAW_COLUMNS["close"]), required=True),
        "volume": parse_int(raw_row.get(RAW_COLUMNS["volume"]), required=True),
        "ref_price": parse_decimal(prev_row.get(RAW_COLUMNS["next_ref"]) if prev_row else None),
        "limit_up": parse_decimal(prev_row.get(RAW_COLUMNS["next_limit_up"]) if prev_row else None),
        "limit_down": parse_decimal(prev_row.get(RAW_COLUMNS["next_limit_down"]) if prev_row else None),
        "is_attention": flag_to_bool(raw_row.get(RAW_COLUMNS["attention"])),
        "is_disposition": flag_to_bool(raw_row.get(RAW_COLUMNS["disposition"])),
        "is_full_delivery": flag_to_bool(raw_row.get(RAW_COLUMNS["full_delivery"])),
    }


def write_row(writer: csv.DictWriter, row: dict[str, str]) -> None:
    writer.writerow({column: row[column] for column in OUTPUT_COLUMNS})


def log_skip(logger: Logger, line_no: int, row: dict[str, str], reason: str) -> None:
    stock_id = extract_stock_id(row.get(RAW_COLUMNS["stock"]))
    trade_date = clean_text(row.get(RAW_COLUMNS["date"]))
    market = clean_text(row.get(RAW_COLUMNS["market"]))
    logger.write(
        f"SKIP line={line_no}, stock_id={stock_id}, date={trade_date}, "
        f"market={market}, reason={reason}"
    )


def clean_dailyprice(
    input_path: Path,
    output_path: Path,
    stock_path: Path,
    limit: int | None,
    logger: Logger,
) -> int:
    logger.section("clean_dailyprice")
    logger.write(f"Started at: {timestamp()}")
    logger.write(f"Input: {input_path}")
    logger.write(f"Input encoding: {RAW_ENCODING}")
    logger.write("Input delimiter: comma")
    logger.write(f"Output: {output_path}")
    logger.write(f"Stock listing source: {stock_path}")
    logger.write(f"Output date range: {START_DATE} to {END_DATE}")
    logger.write(f"Limit: {limit if limit is not None else 'all'}")

    listing_dates = load_listing_dates(stock_path)
    logger.write(f"Loaded listing dates: {len(listing_dates)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    previous_by_stock: dict[str, dict[str, str]] = {}
    written = 0
    read_count = 0
    skipped_non_tse = 0
    skipped_before_start = 0
    skipped_after_end = 0
    skipped_before_listing = 0
    skipped_missing_stock = 0
    skipped_invalid = 0

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS, delimiter="\t")
        writer.writeheader()

        for line_no, raw_row in read_raw_rows(input_path):
            if limit is not None and read_count >= limit:
                break
            read_count += 1

            stock_id = extract_stock_id(raw_row.get(RAW_COLUMNS["stock"]))
            market = clean_text(raw_row.get(RAW_COLUMNS["market"]))

            try:
                trade_date = parse_date(raw_row.get(RAW_COLUMNS["date"]))
            except ImportToolError as exc:
                skipped_invalid += 1
                log_skip(logger, line_no, raw_row, str(exc))
                continue

            if stock_id:
                previous_row = previous_by_stock.get(stock_id)
                previous_by_stock[stock_id] = raw_row
            else:
                previous_row = None

            if market != "TSE":
                skipped_non_tse += 1
                log_skip(logger, line_no, raw_row, "market is not TSE")
                continue
            if trade_date is None:
                skipped_invalid += 1
                log_skip(logger, line_no, raw_row, "missing trade date")
                continue
            if trade_date < START_DATE:
                skipped_before_start += 1
                continue
            if trade_date > END_DATE:
                skipped_after_end += 1
                continue

            listing_date = listing_dates.get(stock_id)
            if listing_date is None:
                skipped_missing_stock += 1
                log_skip(logger, line_no, raw_row, "stock_id not found in clean stock listing dates")
                continue
            if trade_date < listing_date:
                skipped_before_listing += 1
                log_skip(
                    logger,
                    line_no,
                    raw_row,
                    f"trade date before listing_date {listing_date.strftime('%Y-%m-%d')}",
                )
                continue

            try:
                write_row(writer, make_output_row(raw_row, previous_row))
                written += 1
            except (ImportToolError, ValueError) as exc:
                skipped_invalid += 1
                log_skip(logger, line_no, raw_row, f"invalid row: {exc}")

    logger.write(f"Rows read: {read_count}")
    logger.write(f"Rows written: {written}")
    logger.write(f"Skipped non-TSE rows: {skipped_non_tse}")
    logger.write(f"Skipped before {START_DATE}: {skipped_before_start}")
    logger.write(f"Skipped after {END_DATE}: {skipped_after_end}")
    logger.write(f"Skipped before listing date: {skipped_before_listing}")
    logger.write(f"Skipped missing stock/listing date: {skipped_missing_stock}")
    logger.write(f"Skipped invalid rows: {skipped_invalid}")

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean raw daily price data.")
    parser.add_argument("-f", "--filename", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stock-file", type=Path, default=CLEAN_DATA_DIR / "stock.tsv")
    parser.add_argument("-l", "--limit", type=int)
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=DEFAULT_LOG,
        help="Write log output to this file. Default: script/log/clean_dailyprice.log.",
    )
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
        stock_path = resolve_tool_path(args.stock_file)

        if not input_path.exists():
            raise ImportToolError(f"Input file not found: {input_path}")
        if not stock_path.exists():
            raise ImportToolError(f"Stock file not found: {stock_path}")
        if args.limit is not None and args.limit < 0:
            raise ImportToolError("--limit must be zero or a positive integer.")

        clean_dailyprice(input_path, output_path, stock_path, args.limit, logger)
    except ImportToolError as exc:
        return fail(str(exc), logger)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
