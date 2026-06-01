#!/usr/bin/env python3
"""Import cleaned daily price rows into project_main.daily_prices."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from common import (
	CLEAN_DATA_DIR,
	ImportToolError,
	Logger,
	fail,
	get_sql_api_url,
	limited,
	load_env,
	resolve_tool_path,
	run_sql_api,
	timestamp,
)


DEFAULT_FILE = CLEAN_DATA_DIR / "dailyprice.tsv"
DEFAULT_BATCH_SIZE = 50
COLUMNS = [
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


def bool_to_int(value: str) -> str:
	return "1" if value.strip().lower() in {"true", "1", "y", "yes"} else "0"


def clean_text(value: str | None) -> str:
	return (value or "").strip()


def parse_date(value: str | None):
	text = clean_text(value)
	if not text:
		return None
	if "T" in text:
		text = text.split("T", 1)[0]
	return datetime.strptime(text, "%Y-%m-%d").date()


def fetch_listing_dates(api_url: str) -> dict[str, object]:
	result = run_sql_api(
		"""
		SELECT
		  stock_id,
		  DATE_FORMAT(listing_date, '%Y-%m-%d') AS listing_date
		FROM project_main.stocks
		""",
		api_url=api_url,
	)

	listing_dates: dict[str, object] = {}
	for row in result.get("rows", []):
		listing_date = parse_date(row.get("listing_date", ""))
		if listing_date is not None:
			listing_dates[str(row["stock_id"]).strip()] = listing_date

	return listing_dates


def read_rows(path: Path):
	with path.open("r", encoding="utf-8-sig", newline="") as file:
		reader = csv.DictReader(file, delimiter="\t")
		if reader.fieldnames is None:
			raise ImportToolError(f"No header found in file: {path}")

		for row in reader:
			raw_row = {key: clean_text(value) for key, value in row.items()}
			if not any(raw_row.values()):
				continue

			yield {
				"stock_id": raw_row["stock_id"],
				"trade_date": raw_row["trade_date"],
				"open_price": raw_row["open_price"],
				"high_price": raw_row["high_price"],
				"low_price": raw_row["low_price"],
				"close_price": raw_row["close_price"],
				"volume": raw_row["volume"],
				"ref_price": raw_row["ref_price"],
				"limit_up": raw_row["limit_up"],
				"limit_down": raw_row["limit_down"],
				"is_attention": bool_to_int(raw_row["is_attention"]),
				"is_disposition": bool_to_int(raw_row["is_disposition"]),
				"is_full_delivery": bool_to_int(raw_row["is_full_delivery"]),
				"__csv_row__": raw_row,
			}


def filter_by_listing_date(rows, listing_dates: dict[str, object], logger: Logger):
	sent = 0
	skipped_missing_stock = 0
	skipped_missing_listing_date = 0
	skipped_before_listing = 0

	for row in rows:
		stock_id = row["stock_id"]
		trade_date = parse_date(row["trade_date"])
		listing_date = listing_dates.get(stock_id)

		if listing_date is None:
			skipped_missing_stock += 1
			continue
		if trade_date is None:
			skipped_missing_listing_date += 1
			continue
		if trade_date < listing_date:
			skipped_before_listing += 1
			continue

		sent += 1
		yield row

	logger.write(
		"Daily price filter: "
		f"eligible={sent}, "
		f"skipped_before_listing={skipped_before_listing}, "
		f"skipped_missing_stock_or_listing_date={skipped_missing_stock}, "
		f"skipped_invalid_trade_date={skipped_missing_listing_date}"
	)


def sql_literal(value: object) -> str:
	if value is None:
		return "NULL"

	text = str(value).strip()
	if text == "":
		return "NULL"

	return "'" + text.replace("\\", "\\\\").replace("'", "''") + "'"


def build_insert_sql(*, table: str, columns: list[str], rows: list[dict[str, object]], update: bool) -> str:
	command = "INSERT" if update else "INSERT IGNORE"
	values = [
		"(" + ", ".join(sql_literal(row.get(column)) for column in columns) + ")"
		for row in rows
	]
	joined_values = ",\n  ".join(values)

	sql = (
		f"{command} INTO project_main.{table} ({', '.join(columns)})\n"
		f"VALUES\n  {joined_values}"
	)
	if update:
		assignments = ", ".join(
			f"{column} = VALUES({column})"
			for column in columns
			if column not in {"stock_id", "trade_date"}
		)
		sql += f"\nON DUPLICATE KEY UPDATE {assignments}"
	return sql


def import_rows(
	*,
	api_url: str,
	logger: Logger,
	table: str,
	columns: list[str],
	rows,
	update: bool,
	batch_size: int,
	log_last_row: bool,
) -> int:
	total = 0
	batch_number = 0
	current_batch: list[dict[str, object]] = []
	last_row: dict[str, object] | None = None

	logger.write(f"Started at: {timestamp()}")
	logger.write(f"Mode: {'update existing rows' if update else 'skip duplicate rows'}")

	def send_batch(batch: list[dict[str, object]]) -> None:
		nonlocal batch_number, total
		batch_number += 1
		sql = build_insert_sql(table=table, columns=columns, rows=batch, update=update)
		run_sql_api(sql, api_url=api_url)
		total += len(batch)
		logger.write(f"Batch {batch_number}: sent={len(batch)}, total_sent={total}")

	for row in rows:
		last_row = row
		current_batch.append(row)
		if len(current_batch) >= batch_size:
			send_batch(current_batch)
			current_batch = []

	if current_batch:
		send_batch(current_batch)

	if log_last_row and last_row is not None:
		logger.write(
			"Last CSV row: "
			+ json.dumps(last_row.get("__csv_row__", last_row), ensure_ascii=False)
		)

	logger.write(f"Finished. Total rows sent: {total}")
	return total


def validate_args(args: argparse.Namespace) -> None:
	if args.limit is not None and args.limit < 0:
		raise ImportToolError("--limit must be zero or a positive integer.")
	if args.start < 0:
		raise ImportToolError("--start must be zero or a positive integer.")
	if args.batch_size <= 0:
		raise ImportToolError("--batch-size must be a positive integer.")
	if not args.filename.exists():
		raise ImportToolError(f"File not found: {args.filename}")


def main() -> int:
	load_env()

	parser = argparse.ArgumentParser(description="Import cleaned daily price data into project_main.daily_prices.")
	parser.add_argument(
		"-f",
		"--filename",
		type=Path,
		default=DEFAULT_FILE,
		help=f"File to import. Default: {DEFAULT_FILE}",
	)
	parser.add_argument(
		"-l",
		"--limit",
		type=int,
		help="Maximum number of rows to import. Default: import all rows.",
	)
	parser.add_argument(
		"-s",
		"--start",
		type=int,
		default=0,
		help="Zero-based start offset to skip rows before importing. Default: 0.",
	)
	parser.add_argument(
		"-u",
		"--update",
		action="store_true",
		help="Update existing rows when a primary key conflict occurs.",
	)
	parser.add_argument(
		"-o",
		"--out",
		type=Path,
		help="Write batch logs and the last CSV row to this file.",
	)
	parser.add_argument(
		"--quiet",
		action="store_true",
		help="Do not print log output to the terminal.",
	)
	parser.add_argument(
		"--url",
		default=get_sql_api_url(),
		help="SQL API endpoint. Default: env SQL_API_URL.",
	)
	parser.add_argument(
		"--batch-size",
		type=int,
		default=DEFAULT_BATCH_SIZE,
		help=f"Rows per INSERT request. Default: {DEFAULT_BATCH_SIZE}.",
	)
	args = parser.parse_args()

	logger = None
	try:
		logger = Logger(args.out, stdout=not args.quiet)

		input_path = resolve_tool_path(args.filename)
		args.filename = input_path
		validate_args(args)

		logger.section("upload_dailyprice")
		logger.write(f"File: {args.filename}")
		logger.write(f"Limit: {args.limit if args.limit is not None else 'all'}")
		logger.write(f"Start: {args.start}")

		listing_dates = fetch_listing_dates(args.url)
		logger.write(f"Loaded listing dates: {len(listing_dates)} stocks")

		eligible_rows = filter_by_listing_date(read_rows(args.filename), listing_dates, logger)
		import_rows(
			api_url=args.url,
			logger=logger,
			table="daily_prices",
			columns=COLUMNS,
			rows=limited(eligible_rows, args.limit, args.start),
			update=args.update,
			batch_size=args.batch_size,
			log_last_row=args.out is not None,
		)
	except ImportToolError as exc:
		return fail(str(exc), logger)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
