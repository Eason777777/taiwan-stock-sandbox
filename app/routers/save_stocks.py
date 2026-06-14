from fastapi import APIRouter, Depends, HTTPException
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user
from ..save_access import fetch_save_owned

router = APIRouter(
    prefix="/saves/{save_id}/stocks",
    tags=["stocks"],
    dependencies=[Depends(get_current_user)],
)

# 各交易階段對應的「估價基準價格」欄位：盤前=昨日收盤，盤中=今日開盤，盤後／收市=今日收盤。
_PRICE_COLUMN_BY_PHASE = {
    "PRE_MARKET": "close_price",
    "INTRADAY": "open_price",
    "POST_MARKET": "close_price",
    "CLOSED": "close_price",
}


async def _resolve_price_date(db: SqlApiClient, current_phase: str, current_trade_date: str) -> str | None:
    """盤前以前一交易日做為估價基準日，其餘階段以當前交易日為基準日。"""
    if current_phase != "PRE_MARKET":
        return current_trade_date
    rows = (await db.query(
        "SELECT MAX(trade_date) AS price_date FROM daily_prices WHERE trade_date < ?",
        [current_trade_date],
    ))["rows"]
    price_date = rows[0]["price_date"]
    return str(price_date)[:10] if price_date is not None else None


async def _fetch_stock_detail_row(
    db: SqlApiClient, stock_id: str, price_date: str | None, current_trade_date: str, price_column: str,
) -> dict | None:
    """同時取得「估價基準日」（dp_current，提供當前價格與警示旗標）與
    「當前交易日」（dp_today，提供開盤參考價與今日開高低收量）的報價。
    盤中／盤後／收市時兩者為同一天，盤前時 dp_current 為前一交易日。
    """
    if price_date is None:
        return None
    result = await db.query(
        f"SELECT s.stock_id, s.stock_name_zh, s.market_type, s.sector_name,"
        f" dp_today.ref_price,"
        f" dp_current.{price_column} AS current_price,"
        f" dp_current.is_attention, dp_current.is_disposition, dp_current.is_full_delivery,"
        f" dp_today.open_price, dp_today.high_price, dp_today.low_price, dp_today.close_price, dp_today.volume"
        " FROM stocks s"
        " LEFT JOIN daily_prices dp_current ON dp_current.stock_id = s.stock_id AND dp_current.trade_date = ?"
        " LEFT JOIN daily_prices dp_today ON dp_today.stock_id = s.stock_id AND dp_today.trade_date = ?"
        " WHERE s.stock_id = ?",
        [price_date, current_trade_date, stock_id],
    )
    return result["rows"][0] if result["rows"] else None


def _build_stock_detail(row: dict, current_phase: str) -> dict:
    current_price = float(row["current_price"]) if row["current_price"] is not None else None
    ref_price = float(row["ref_price"]) if row["ref_price"] is not None else None

    if current_phase == "PRE_MARKET" or current_price is None or ref_price is None:
        price_change = 0.0
        price_change_pct = 0.0
    else:
        price_change = round(current_price - ref_price, 2)
        price_change_pct = round(price_change / ref_price * 100, 2) if ref_price else 0.0

    # 盤前：今日開高低收量全部隱藏；盤中：再額外隱藏最高/最低/收盤（僅開盤已知）。
    show_today_open = current_phase != "PRE_MARKET"
    show_today_high_low_close = current_phase not in ("PRE_MARKET", "INTRADAY")

    return {
        "stock_id": row["stock_id"],
        "stock_name_zh": row["stock_name_zh"],
        "market_type": row["market_type"],
        "sector_name": row["sector_name"],
        "current_price": current_price,
        "ref_price": ref_price,
        "price_change": price_change,
        "price_change_percent": price_change_pct,
        "open_price": float(row["open_price"]) if show_today_open and row["open_price"] is not None else None,
        "high_price": float(row["high_price"]) if show_today_high_low_close and row["high_price"] is not None else None,
        "low_price": float(row["low_price"]) if show_today_high_low_close and row["low_price"] is not None else None,
        "close_price": float(row["close_price"]) if show_today_high_low_close and row["close_price"] is not None else None,
        "volume": int(row["volume"]) if show_today_high_low_close and row["volume"] is not None else 0,
        "is_attention": bool(row["is_attention"]),
        "is_disposition": bool(row["is_disposition"]),
        "is_full_delivery": bool(row["is_full_delivery"]),
    }


@router.get("/{stock_id}")
async def get_save_stock_detail(
    save_id: int,
    stock_id: str,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    save = await fetch_save_owned(save_id, current_user, db, columns="save_id, user_id, current_trade_date, current_phase")
    current_phase = save["current_phase"]
    current_trade_date = str(save["current_trade_date"])[:10]

    stock_result = await db.query("SELECT stock_id FROM stocks WHERE stock_id = ?", [str(stock_id)])
    if not stock_result["rows"]:
        raise HTTPException(status_code=404, detail="股票不存在")

    price_date = await _resolve_price_date(db, current_phase, current_trade_date)
    row = await _fetch_stock_detail_row(
        db, str(stock_id), price_date, current_trade_date, _PRICE_COLUMN_BY_PHASE[current_phase],
    )
    if row is None:
        raise HTTPException(status_code=404, detail="查無報價資料")

    return _build_stock_detail(row, current_phase)
