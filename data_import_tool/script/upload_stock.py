#!/usr/bin/env python3
"""Import cleaned stock rows into project_main.stocks."""

from __future__ import annotations

import argparse
import csv
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
)


DEFAULT_FILE = CLEAN_DATA_DIR / "stock.tsv"
DEFAULT_BATCH_SIZE = 50
COLUMNS = [
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
MARKET_TYPE_MAP = {
	"上市": "TSE",
	"上櫃": "OTC",
	"興櫃": "EMERGING",
	"TSE": "TSE",
	"OTC": "OTC",
	"EMERGING": "EMERGING",
	"INDEX": "INDEX",
}
PRIMARY_KEY_COLUMNS = {"stock_id"}


def clean_text(value: str | None) -> str:
	return (value or "").strip()


def read_rows(path: Path):
	with path.open("r", encoding="utf-8-sig", newline="") as file:
		reader = csv.DictReader(file, delimiter="\t")
		if reader.fieldnames is None:
			raise ImportToolError(f"No header found in file: {path}")

		for row in reader:
			normalized = {key: clean_text(value) for key, value in row.items()}
			if not any(normalized.values()):
				continue

			stock_id = normalized.get("stock_id", "")
			if not stock_id:
				raise ImportToolError(f"Missing stock_id in row: {row}")

			stock_name_zh = normalized.get("stock_name_zh", "")
			if not stock_name_zh:
				raise ImportToolError(f"Missing stock_name_zh for stock_id={stock_id}")

			stock_full_name_zh = normalized.get("stock_full_name_zh", "")
			if not stock_full_name_zh:
				stock_full_name_zh = stock_name_zh

			yield {
				"stock_id": stock_id,
				"stock_name_zh": stock_name_zh,
				"stock_full_name_zh": stock_full_name_zh,
				"stock_name_en": normalized.get("stock_name_en", ""),
				"stock_full_name_en": normalized.get("stock_full_name_en", ""),
				"market_type": normalized.get("market_type", ""),
				"sector_name": normalized.get("sector_name", ""),
				"listing_date": normalized.get("listing_date", ""),
				"par_value": normalized.get("par_value", ""),
				"phone": normalized.get("phone", ""),
				"address": normalized.get("address", ""),
				"website": normalized.get("website", ""),
			}


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
			if column not in PRIMARY_KEY_COLUMNS
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
) -> int:
	total = 0
	batch_number = 0
	current_batch: list[dict[str, object]] = []

	logger.write(f"Started at: {Path().resolve()}")
	logger.write(f"Mode: {'update existing rows' if update else 'skip duplicate rows'}")

	def send_batch(batch: list[dict[str, object]]) -> None:
		nonlocal batch_number, total
		batch_number += 1
		sql = build_insert_sql(table=table, columns=columns, rows=batch, update=update)
		run_sql_api(sql, api_url=api_url)
		total += len(batch)
		logger.write(f"Batch {batch_number}: sent={len(batch)}, total_sent={total}")

	for row in rows:
		current_batch.append(row)
		if len(current_batch) >= batch_size:
			send_batch(current_batch)
			current_batch = []

	if current_batch:
		send_batch(current_batch)

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

	parser = argparse.ArgumentParser(description="Import cleaned stock data into project_main.stocks.")
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
		help="Also write terminal output to this log file.",
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

		logger.section("upload_stock")
		logger.write(f"File: {args.filename}")
		logger.write(f"Limit: {args.limit if args.limit is not None else 'all'}")
		logger.write(f"Start: {args.start}")

		rows = limited(read_rows(args.filename), args.limit, args.start)
		import_rows(
			api_url=args.url,
			logger=logger,
			table="stocks",
			columns=COLUMNS,
			rows=rows,
			update=args.update,
			batch_size=args.batch_size,
		)
	except ImportToolError as exc:
		return fail(str(exc), logger)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
