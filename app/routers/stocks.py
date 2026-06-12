from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/stocks",
    tags=["stocks"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def search_stocks(
    q: str | None = Query(None, description="Search by stock_id or stock_name_zh"),
    sector: str | None = Query(None, description="Filter by sector_name"),
    limit: int = Query(50, ge=1, le=500),
    db: SqlApiClient = Depends(get_db),
):
    sql = (
        "SELECT stock_id, stock_name_zh, stock_full_name_zh, market_type,"
        " sector_name, listing_date"
        " FROM stocks"
    )
    clauses: list[str] = []
    params: list = []

    if q:
        like = f"%{q}%"
        if q.isascii():
            # 股號為 ASCII，只有在關鍵字也是 ASCII 時才需要比對 stock_id，
            # 避免中文關鍵字與 stock_id 欄位比對時的編碼相容性問題。
            clauses.append("(stock_id LIKE ? OR stock_name_zh LIKE ? OR stock_full_name_zh LIKE ?)")
            params.extend([like, like, like])
        else:
            clauses.append("(stock_name_zh LIKE ? OR stock_full_name_zh LIKE ?)")
            params.extend([like, like])
    if sector:
        clauses.append("sector_name = ?")
        params.append(sector)

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY stock_id LIMIT ?"
    params.append(int(limit))

    result = await db.query(sql, params)
    return result["rows"]


@router.get("/{stock_id}")
async def get_stock(stock_id: str, db: SqlApiClient = Depends(get_db)):
    result = await db.query(
        "SELECT * FROM stocks WHERE stock_id = ?",
        [str(stock_id)],
    )
    if not result["rows"]:
        raise HTTPException(status_code=404, detail="股票不存在")
    return result["rows"][0]


@router.get("/{stock_id}/prices")
async def get_price_history(
    stock_id: str,
    from_date: str | None = Query(None, description="YYYY-MM-DD"),
    to_date: str | None = Query(None, description="YYYY-MM-DD"),
    save_id: int = Query(..., description="必填；僅回傳該存檔目前交易日之前的資料（時空隔離）"),
    interval: str = Query("day", pattern="^(day|week|month)$", description="K 線週期：day/week/month"),
    indicators: str | None = Query(
        None,
        description="逗號分隔的技術指標清單，支援 maN（如 ma5,ma20）、rsiN（如 rsi14）、macd",
    ),
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Confirm the stock exists so callers can tell "no such stock" from "no prices".
    stock = await db.query(
        "SELECT stock_id FROM stocks WHERE stock_id = ?",
        [str(stock_id)],
    )
    if not stock["rows"]:
        raise HTTPException(status_code=404, detail="股票不存在")

    save = await db.query(
        "SELECT user_id, current_trade_date FROM save_files WHERE save_id = ?", [int(save_id)],
    )
    if not save["rows"]:
        raise HTTPException(status_code=404, detail="存檔不存在")
    if int(save["rows"][0]["user_id"]) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    current_trade_date = str(save["rows"][0]["current_trade_date"])[:10]

    # 取得時空隔離範圍內的完整歷史序列（不在 SQL 端套用 from/to），
    # 讓技術指標有足夠的回溯資料可計算，最後再依 from/to 裁切輸出範圍。
    result = await db.query(
        "SELECT stock_id, trade_date, open_price, high_price, low_price, close_price, volume,"
        " ref_price, limit_up, limit_down,"
        " is_attention, is_disposition, is_full_delivery"
        " FROM daily_prices WHERE stock_id = ? AND trade_date < ? ORDER BY trade_date",
        [str(stock_id), current_trade_date],
    )

    float_fields = ("open_price", "high_price", "low_price", "close_price", "ref_price", "limit_up", "limit_down")
    rows = []
    for row in result["rows"]:
        row = dict(row)
        row["trade_date"] = str(row["trade_date"])[:10]
        for field in float_fields:
            if row.get(field) is not None:
                row[field] = float(row[field])
        if row.get("volume") is not None:
            row["volume"] = int(row["volume"])
        rows.append(row)

    if interval != "day" and rows:
        rows = _aggregate_prices(rows, interval)

    if indicators and rows:
        rows = _apply_indicators(rows, indicators)

    if from_date:
        rows = [row for row in rows if row["trade_date"] >= from_date]
    if to_date:
        rows = [row for row in rows if row["trade_date"] <= to_date]

    return rows


def _aggregate_prices(rows: list[dict], interval: str) -> list[dict]:
    """將日線資料依週/月聚合成 K 線（open=區間第一筆, close=區間最後一筆,
    high/low=區間極值, volume=區間總和, trade_date=區間最後一個交易日）。"""
    groups: dict[tuple, list[dict]] = {}
    for row in rows:
        d = date.fromisoformat(row["trade_date"])
        if interval == "week":
            key = d.isocalendar()[:2]  # (ISO year, ISO week)
        else:  # month
            key = (d.year, d.month)
        groups.setdefault(key, []).append(row)

    aggregated = []
    for key in sorted(groups.keys()):
        bucket = groups[key]
        aggregated.append({
            "stock_id": bucket[0]["stock_id"],
            "trade_date": bucket[-1]["trade_date"],
            "open_price": bucket[0]["open_price"],
            "high_price": max(r["high_price"] for r in bucket),
            "low_price": min(r["low_price"] for r in bucket),
            "close_price": bucket[-1]["close_price"],
            "volume": sum(r["volume"] for r in bucket if r.get("volume") is not None),
        })
    return aggregated


def _apply_indicators(rows: list[dict], indicators: str) -> list[dict]:
    """依 indicators 參數（逗號分隔，如 ma5,ma20,rsi14,macd）為每筆資料加上技術指標欄位。"""
    requested = {token.strip().lower() for token in indicators.split(",") if token.strip()}
    closes = [row["close_price"] for row in rows]

    ma_periods = sorted({int(t[2:]) for t in requested if t.startswith("ma") and t[2:].isdigit()})
    for period in ma_periods:
        for row, value in zip(rows, _moving_average(closes, period)):
            row[f"ma{period}"] = value

    rsi_periods = sorted({int(t[3:]) for t in requested if t.startswith("rsi") and t[3:].isdigit()})
    for period in rsi_periods:
        for row, value in zip(rows, _rsi(closes, period)):
            row[f"rsi{period}"] = value

    if "macd" in requested:
        macd_line, signal_line, hist = _macd(closes)
        for row, m, s, h in zip(rows, macd_line, signal_line, hist):
            row["macd"] = m
            row["macd_signal"] = s
            row["macd_hist"] = h

    return rows


def _moving_average(closes: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    for i in range(len(closes)):
        if i + 1 < period:
            result.append(None)
        else:
            window = closes[i + 1 - period : i + 1]
            result.append(round(sum(window) / period, 2))
    return result


def _rsi(closes: list[float], period: int = 14) -> list[float | None]:
    result: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return result

    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result[period] = _rsi_from_avg(avg_gain, avg_loss)

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        result[i + 1] = _rsi_from_avg(avg_gain, avg_loss)

    return result


def _rsi_from_avg(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def _ema(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result

    sma = sum(values[:period]) / period
    result[period - 1] = sma
    k = 2 / (period + 1)
    for i in range(period, len(values)):
        result[i] = values[i] * k + result[i - 1] * (1 - k)
    return result


def _macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line: list[float | None] = [
        (f - s) if f is not None and s is not None else None
        for f, s in zip(ema_fast, ema_slow)
    ]

    valid = [v for v in macd_line if v is not None]
    signal_ema = _ema(valid, signal)
    offset = len(macd_line) - len(valid)
    signal_line: list[float | None] = [None] * len(macd_line)
    for i, value in enumerate(signal_ema):
        signal_line[offset + i] = value

    hist: list[float | None] = [
        round(m - s, 4) if m is not None and s is not None else None
        for m, s in zip(macd_line, signal_line)
    ]
    macd_line = [round(v, 4) if v is not None else None for v in macd_line]
    signal_line = [round(v, 4) if v is not None else None for v in signal_line]
    return macd_line, signal_line, hist
