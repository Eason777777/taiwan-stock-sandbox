from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves/{save_id}/watchlist",
    tags=["watchlist"],
    dependencies=[Depends(get_current_user)],
)

MAX_WATCHLIST_SIZE = 100


class AddWatchlistRequest(BaseModel):
    stock_id: str


async def _fetch_save_owned(save_id: int, current_user: dict, db: SqlApiClient) -> dict:
    result = await db.query(
        "SELECT save_id, user_id FROM save_files WHERE save_id = ?",
        [int(save_id)],
    )
    if not result["rows"]:
        raise HTTPException(status_code=404, detail="存檔不存在")
    save = result["rows"][0]
    if int(save["user_id"]) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    return save


@router.get("")
async def get_watchlist(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)

    save_result = await db.query(
        "SELECT current_trade_date, current_phase FROM save_files WHERE save_id = ?",
        [int(save_id)],
    )
    current_trade_date = str(save_result["rows"][0]["current_trade_date"])[:10]
    current_phase = save_result["rows"][0]["current_phase"]

    if current_phase == "PRE_MARKET":
        prev_result = await db.query(
            "SELECT MAX(trade_date) AS prev_date FROM daily_prices WHERE trade_date < ?",
            [current_trade_date],
        )
        price_date = str(prev_result["rows"][0]["prev_date"])[:10] if prev_result["rows"][0]["prev_date"] else current_trade_date
        price_col = "close_price"
    elif current_phase == "INTRADAY":
        price_date = current_trade_date
        price_col = "open_price"
    else:  # POST_MARKET / CLOSED
        price_date = current_trade_date
        price_col = "close_price"

    result = await db.query(
        f"SELECT w.stock_id, s.stock_name_zh, s.market_type, s.sector_name,"
        f" dp_current.{price_col} AS current_price, dp_today.ref_price,"
        f" dp_current.is_attention, dp_current.is_disposition, dp_current.is_full_delivery"
        f" FROM watchlists w"
        f" JOIN stocks s ON s.stock_id = w.stock_id"
        f" LEFT JOIN daily_prices dp_current"
        f"   ON dp_current.stock_id = w.stock_id AND dp_current.trade_date = ?"
        f" LEFT JOIN daily_prices dp_today"
        f"   ON dp_today.stock_id = w.stock_id AND dp_today.trade_date = ?"
        f" WHERE w.save_id = ?"
        f" ORDER BY w.stock_id",
        [price_date, current_trade_date, int(save_id)],
    )

    rows = []
    for row in result["rows"]:
        row = dict(row)
        cp = float(row["current_price"]) if row.get("current_price") is not None else None
        rp = float(row["ref_price"]) if row.get("ref_price") is not None else None
        row["current_price"] = cp
        row["ref_price"] = rp
        if current_phase == "PRE_MARKET" or cp is None or rp is None:
            row["price_change"] = 0.0
            row["price_change_percent"] = 0.0
        else:
            change = cp - rp
            row["price_change"] = round(change, 2)
            row["price_change_percent"] = round(change / rp * 100, 2) if rp != 0 else 0.0
        rows.append(row)

    return rows


@router.post("", status_code=201)
async def add_to_watchlist(
    save_id: int,
    body: AddWatchlistRequest,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)

    stock_result = await db.query(
        "SELECT stock_id FROM stocks WHERE stock_id = ?",
        [str(body.stock_id)],
    )
    if not stock_result["rows"]:
        raise HTTPException(status_code=404, detail="股票不存在")

    count_result = await db.query(
        "SELECT COUNT(*) AS c FROM watchlists WHERE save_id = ?", [int(save_id)],
    )
    if int(count_result["rows"][0]["c"]) >= MAX_WATCHLIST_SIZE:
        raise HTTPException(status_code=400, detail=f"自選股已達上限（{MAX_WATCHLIST_SIZE} 檔）")

    # Composite PK (save_id, stock_id) — INSERT IGNORE makes re-adding a no-op.
    await db.query(
        "INSERT IGNORE INTO watchlists (save_id, stock_id) VALUES (?, ?)",
        [int(save_id), str(body.stock_id)],
    )
    return {"save_id": int(save_id), "stock_id": str(body.stock_id)}


@router.delete("/{stock_id}", status_code=204)
async def remove_from_watchlist(
    save_id: int,
    stock_id: str,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)
    await db.query(
        "DELETE FROM watchlists WHERE save_id = ? AND stock_id = ?",
        [int(save_id), str(stock_id)],
    )
