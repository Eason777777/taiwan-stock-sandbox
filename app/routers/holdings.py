from fastapi import APIRouter, Depends, HTTPException
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves/{save_id}/holdings",
    tags=["holdings"],
    dependencies=[Depends(get_current_user)],
)


async def _fetch_save_owned(save_id: int, current_user: dict, db: SqlApiClient) -> dict:
    result = await db.query(
        "SELECT save_id, user_id, current_trade_date, current_phase FROM save_files WHERE save_id = ?",
        [int(save_id)],
    )
    if not result["rows"]:
        raise HTTPException(status_code=404, detail="存檔不存在")
    save = result["rows"][0]
    if int(save["user_id"]) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    return save


@router.get("")
async def list_holdings(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    save = await _fetch_save_owned(save_id, current_user, db)
    current_trade_date = str(save["current_trade_date"])[:10]
    current_phase = save["current_phase"]

    # 依目前交易階段決定估價基準日與價格欄位：
    # 盤前：前一交易日收盤價；盤中：當日開盤價；盤後／收市：當日收盤價。
    if current_phase == "PRE_MARKET":
        price_date_rows = (await db.query(
            "SELECT MAX(trade_date) AS price_date FROM daily_prices WHERE trade_date < ?",
            [current_trade_date],
        ))["rows"]
        price_date = price_date_rows[0]["price_date"]
        price_date = str(price_date)[:10] if price_date is not None else None
        price_column = "close_price"
    elif current_phase == "INTRADAY":
        price_date = current_trade_date
        price_column = "open_price"
    else:  # POST_MARKET / CLOSED
        price_date = current_trade_date
        price_column = "close_price"

    if price_date is not None:
        result = await db.query(
            f"SELECT h.stock_id, s.stock_name_zh, h.quantity, h.avg_cost, dp.{price_column} AS market_price"
            " FROM holdings h"
            " JOIN stocks s ON s.stock_id = h.stock_id"
            " LEFT JOIN daily_prices dp ON dp.stock_id = h.stock_id AND dp.trade_date = ?"
            " WHERE h.save_id = ?"
            " ORDER BY h.stock_id",
            [price_date, int(save_id)],
        )
    else:
        result = await db.query(
            "SELECT h.stock_id, s.stock_name_zh, h.quantity, h.avg_cost, NULL AS market_price"
            " FROM holdings h"
            " JOIN stocks s ON s.stock_id = h.stock_id"
            " WHERE h.save_id = ?"
            " ORDER BY h.stock_id",
            [int(save_id)],
        )

    holdings = []
    for row in result["rows"]:
        quantity = int(row["quantity"])
        avg_cost = float(row["avg_cost"])
        cost_value = round(avg_cost * quantity * 1000, 2)
        market_price = float(row["market_price"]) if row.get("market_price") is not None else None

        if market_price is not None:
            market_value = round(market_price * quantity * 1000, 2)
            unrealized_pnl = round(market_value - cost_value, 2)
            unrealized_pnl_pct = round(unrealized_pnl / cost_value * 100, 2) if cost_value else None
        else:
            market_value = None
            unrealized_pnl = None
            unrealized_pnl_pct = None

        holdings.append({
            "stock_id": row["stock_id"],
            "stock_name_zh": row["stock_name_zh"],
            "quantity": quantity,
            "avg_cost": avg_cost,
            "market_price": market_price,
            "cost_value": cost_value,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
        })
    return holdings


@router.get("/transactions")
async def list_transactions(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)
    result = await db.query(
        "SELECT t.transaction_id, t.order_id, o.stock_id, s.stock_name_zh,"
        " o.side, o.order_type, o.sim_date,"
        " t.exec_price, t.quantity, t.fee, t.tax, t.avg_cost_at_transact"
        " FROM stock_transactions t"
        " JOIN stock_orders o ON o.order_id = t.order_id"
        " LEFT JOIN stocks s ON s.stock_id = o.stock_id"
        " WHERE o.save_id = ?"
        " ORDER BY t.transaction_id DESC",
        [int(save_id)],
    )
    return result["rows"]
