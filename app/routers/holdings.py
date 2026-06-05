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
        "SELECT save_id, user_id, current_date FROM SaveFile WHERE save_id = ?",
        [int(save_id)],
    )
    if not result['rows']:
        raise HTTPException(status_code=404, detail="存檔不存在")
    save = result['rows'][0]
    if int(save['user_id']) != int(current_user['user_id']):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    return save


@router.get("/")
async def list_holdings(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    save = await _fetch_save_owned(save_id, current_user, db)
    current_date = str(save['current_date'])

    # Mark each holding to the close price on the save's current trading day.
    # If the current day has no price row (e.g. a non-trading day), market_price
    # is NULL and the client should treat unrealized P&L as unavailable.
    result = await db.query(
        "SELECT h.stock_id, s.stock_name_zh, h.quantity, h.avg_cost, dp.close AS market_price"
        " FROM Holding h"
        " JOIN Stock s ON s.stock_id = h.stock_id"
        " LEFT JOIN DailyPrice dp ON dp.stock_id = h.stock_id AND dp.trade_date = ?"
        " WHERE h.save_id = ?"
        " ORDER BY h.stock_id",
        [current_date, int(save_id)],
    )

    holdings = []
    for row in result['rows']:
        quantity = int(row['quantity'])
        avg_cost = float(row['avg_cost'])
        cost_value = int(avg_cost * quantity * 1000)
        market_price = float(row['market_price']) if row.get('market_price') is not None else None

        if market_price is not None:
            market_value = int(market_price * quantity * 1000)
            unrealized_pnl = market_value - cost_value
            unrealized_pnl_pct = round(unrealized_pnl / cost_value * 100, 2) if cost_value else None
        else:
            market_value = None
            unrealized_pnl = None
            unrealized_pnl_pct = None

        holdings.append({
            "stock_id": row['stock_id'],
            "stock_name_zh": row['stock_name_zh'],
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
        " FROM StockTransaction t"
        " JOIN StockOrder o ON o.order_id = t.order_id"
        " LEFT JOIN Stock s ON s.stock_id = o.stock_id"
        " WHERE o.save_id = ?"
        " ORDER BY t.transaction_id DESC",
        [int(save_id)],
    )
    return result['rows']
