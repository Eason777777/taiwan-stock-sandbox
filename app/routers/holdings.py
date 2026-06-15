from fastapi import APIRouter, Depends, Query
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user
from ..save_access import fetch_save_owned

router = APIRouter(
    prefix="/saves/{save_id}/holdings",
    tags=["holdings"],
    dependencies=[Depends(get_current_user)],
)


async def _resolve_price_basis(db: SqlApiClient, current_phase: str, current_trade_date: str) -> tuple[str | None, str]:
    """依目前交易階段決定估價基準日與價格欄位：
    盤前：前一交易日收盤價；盤中：當日開盤價；盤後／收市：當日收盤價。
    """
    if current_phase == "PRE_MARKET":
        price_date_rows = (await db.query(
            "SELECT MAX(trade_date) AS price_date FROM daily_prices WHERE trade_date < ?",
            [current_trade_date],
        ))["rows"]
        price_date = price_date_rows[0]["price_date"]
        price_date = str(price_date)[:10] if price_date is not None else None
        return price_date, "close_price"
    if current_phase == "INTRADAY":
        return current_trade_date, "open_price"
    return current_trade_date, "close_price"  # POST_MARKET / CLOSED


async def _fetch_holdings_with_prices(db: SqlApiClient, save_id: int, price_date: str | None, price_column: str) -> list[dict]:
    if price_date is not None:
        result = await db.query(
            f"SELECT h.stock_id, s.stock_name_zh, h.quantity, h.avg_cost, dp.{price_column} AS market_price"
            " FROM holdings h"
            " JOIN stocks s ON s.stock_id = h.stock_id"
            " LEFT JOIN daily_prices dp ON dp.stock_id = h.stock_id AND dp.trade_date = ?"
            " WHERE h.save_id = ?"
            " ORDER BY h.stock_id",
            [price_date, save_id],
        )
    else:
        result = await db.query(
            "SELECT h.stock_id, s.stock_name_zh, h.quantity, h.avg_cost, NULL AS market_price"
            " FROM holdings h"
            " JOIN stocks s ON s.stock_id = h.stock_id"
            " WHERE h.save_id = ?"
            " ORDER BY h.stock_id",
            [save_id],
        )
    return result["rows"]


def _holding_with_pnl(row: dict) -> dict:
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

    return {
        "stock_id": row["stock_id"],
        "stock_name_zh": row["stock_name_zh"],
        "quantity": quantity,
        "avg_cost": avg_cost,
        "market_price": market_price,
        "cost_value": cost_value,
        "market_value": market_value,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
    }


@router.get("")
async def list_holdings(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    save = await fetch_save_owned(save_id, current_user, db, columns="save_id, user_id, current_trade_date, current_phase")
    current_trade_date = str(save["current_trade_date"])[:10]

    price_date, price_column = await _resolve_price_basis(db, save["current_phase"], current_trade_date)
    rows = await _fetch_holdings_with_prices(db, int(save_id), price_date, price_column)
    return [_holding_with_pnl(row) for row in rows]


def _settled_transaction_fields(row: dict) -> dict:
    """依 stock_transactions 的成交結果補上已實現損益／報酬率／投資成本／出帳入帳金額。"""
    quantity = int(row["quantity"])
    side = row["side"]
    exec_price = float(row["exec_price"])
    avg_cost = float(row["avg_cost_at_transact"])
    fee = int(float(row["fee"]))
    tax = int(float(row["tax"]))
    principal = round(exec_price * quantity * 1000)

    row["avg_cost"] = avg_cost
    row["exec_price"] = exec_price
    row["price"] = exec_price  # 前端相容性：對齊為 record.price

    if side == "BUY":
        row["net_amount"] = principal + fee
        row["realized_pnl"] = None
        row["return_rate"] = None
    else:
        row["net_amount"] = principal - fee - tax
        cost_basis = avg_cost * quantity * 1000
        row["realized_pnl"] = round(row["net_amount"] - cost_basis, 2)
        row["return_rate"] = round(row["realized_pnl"] / cost_basis * 100, 2) if cost_basis else None

    return row


@router.get("/transactions")
async def list_transactions(
    save_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await fetch_save_owned(save_id, current_user, db, columns="save_id, user_id")
    result = await db.query(
        "SELECT t.transaction_id, t.order_id, o.stock_id, s.stock_name_zh,"
        " o.side, o.order_type, o.sim_date,"
        " t.exec_price, t.quantity, t.fee, t.tax, t.avg_cost_at_transact"
        " FROM stock_transactions t"
        " JOIN stock_orders o ON o.order_id = t.order_id"
        " LEFT JOIN stocks s ON s.stock_id = o.stock_id"
        " WHERE o.save_id = ?"
        " ORDER BY t.transaction_id DESC LIMIT ? OFFSET ?",
        [int(save_id), limit, offset],
    )
    return [_settled_transaction_fields(row) for row in result["rows"]]
