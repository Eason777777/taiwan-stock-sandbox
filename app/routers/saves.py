import random
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves",
    tags=["saves"],
    dependencies=[Depends(get_current_user)],
)


class CreateSaveRequest(BaseModel):
    save_name: str
    start_date: str          # YYYY-MM-DD; system picks a random historical date if omitted
    initial_savings: float
    initial_trading: float


async def _fetch_save_owned(save_id: int, current_user: dict, db: SqlApiClient) -> dict:
    result = await db.query(
        "SELECT * FROM SaveFile WHERE save_id = ?",
        [save_id],
    )
    if not result['rows']:
        raise HTTPException(status_code=404, detail="存檔不存在")
    save = result['rows'][0]
    if int(save['user_id']) != int(current_user['user_id']):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    return save


@router.get("/")
async def list_saves(
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.query(
        "SELECT * FROM SaveFile WHERE user_id = ? ORDER BY created_at DESC",
        [int(current_user['user_id'])],
    )
    return result['rows']


@router.post("/", status_code=201)
async def create_save(
    body: CreateSaveRequest,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    initial_savings = int(body.initial_savings)
    initial_trading = int(body.initial_trading)

    await db.query(
        "INSERT INTO SaveFile"
        " (user_id, save_name, start_date, current_date, current_phase, status, savings_balance, trading_balance)"
        " VALUES (?, ?, ?, ?, '盤前', '進行中', ?, ?)",
        [int(current_user['user_id']), body.save_name, body.start_date, body.start_date,
         initial_savings, initial_trading],
    )

    id_result = await db.query("SELECT LAST_INSERT_ID() AS save_id", [])
    save_id = int(id_result['rows'][0]['save_id'])

    # Seed AccountTransaction rows for the two initial deposits
    await db.query(
        "INSERT INTO AccountTransaction"
        " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
        " VALUES (?, 1, '存款戶', ?, '初始存入', ?, ?, '模擬開始初始存款')",
        [save_id, body.start_date, initial_savings, initial_savings],
    )
    await db.query(
        "INSERT INTO AccountTransaction"
        " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
        " VALUES (?, 2, '交割戶', ?, '初始存入', ?, ?, '模擬開始初始存款')",
        [save_id, body.start_date, initial_trading, initial_trading],
    )

    save_result = await db.query(
        "SELECT * FROM SaveFile WHERE save_id = ?",
        [save_id],
    )
    return save_result['rows'][0]


@router.get("/{save_id}")
async def get_save(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await _fetch_save_owned(save_id, current_user, db)


@router.delete("/{save_id}", status_code=204)
async def delete_save(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)
    await db.query("DELETE FROM SaveFile WHERE save_id = ?", [save_id])


@router.post("/{save_id}/advance")
async def advance_phase(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    save = await _fetch_save_owned(save_id, current_user, db)

    if save['status'] == '已結束':
        raise HTTPException(status_code=400, detail="模擬已結束，無法繼續推進")

    phase = save['current_phase']
    current_date = str(save['current_date'])

    PHASES = ['盤前', '盤中', '盤後']
    if phase not in PHASES:
        raise HTTPException(status_code=400, detail=f"未知的交易階段: {phase}")

    # 盤前 → 盤中 or 盤中 → 盤後: just advance the phase label
    if phase != '盤後':
        next_phase = PHASES[PHASES.index(phase) + 1]
        await db.query(
            "UPDATE SaveFile SET current_phase = ? WHERE save_id = ?",
            [next_phase, save_id],
        )
        return {"current_phase": next_phase, "current_date": current_date}

    # ── 盤後 → next trading day 盤前 ──────────────────────────────────────
    # Run order matching then expiry for all 待成交 orders of today.
    # Balance debits/credits happen here (T+0 settlement = same-day close).

    trading_balance = int(save['trading_balance'])

    seq_result = await db.query(
        "SELECT COALESCE(MAX(seq), 0) AS max_seq FROM AccountTransaction WHERE save_id = ?",
        [save_id],
    )
    next_seq = int(seq_result['rows'][0]['max_seq']) + 1

    orders_result = await db.query(
        "SELECT * FROM StockOrder WHERE save_id = ? AND status = '待成交'",
        [save_id],
    )

    for order in orders_result['rows']:
        order_id   = int(order['order_id'])
        stock_id   = str(order['stock_id'])
        order_type = order['order_type']          # 限價 | 市價
        side       = order['side']                # 買 | 賣
        price      = float(order['price']) if order.get('price') is not None else None
        quantity   = int(order['quantity'])       # lots

        # Look up today's OHLC
        dp_result = await db.query(
            "SELECT low, high FROM DailyPrice WHERE stock_id = ? AND trade_date = ?",
            [stock_id, current_date],
        )
        if not dp_result['rows']:
            await db.query(
                "UPDATE StockOrder SET status = '已失效' WHERE order_id = ?",
                [order_id],
            )
            continue

        dp   = dp_result['rows'][0]
        low  = float(dp['low'])
        high = float(dp['high'])

        # Determine whether the order fills and at what price
        if order_type == '限價':
            if side == '買':
                fills      = (price is not None and price >= low)
                exec_price = price
            else:
                fills      = (price is not None and price <= high)
                exec_price = price
        else:  # 市價 — always fills at a random price within today's range
            fills      = True
            exec_price = round(random.uniform(low, high), 2)

        if not fills:
            await db.query(
                "UPDATE StockOrder SET status = '已失效' WHERE order_id = ?",
                [order_id],
            )
            continue

        principal = int(exec_price * quantity * 1000)
        fee       = max(20, int(principal * 0.001425))
        tax       = int(principal * 0.003) if side == '賣' else 0

        # Fetch current holding
        holding_result = await db.query(
            "SELECT quantity, avg_cost FROM Holding WHERE save_id = ? AND stock_id = ?",
            [save_id, stock_id],
        )
        has_holding = bool(holding_result['rows'])
        old_qty     = int(holding_result['rows'][0]['quantity']) if has_holding else 0
        old_avg     = float(holding_result['rows'][0]['avg_cost']) if has_holding else 0.0

        if side == '買':
            total_cost = principal + fee
            if trading_balance < total_cost:
                # Insufficient funds at settlement — expire rather than overspend
                await db.query(
                    "UPDATE StockOrder SET status = '已失效' WHERE order_id = ?",
                    [order_id],
                )
                continue

            new_qty     = old_qty + quantity
            new_avg     = round((old_avg * old_qty + exec_price * quantity) / new_qty, 2)
            trading_balance -= total_cost

            if has_holding:
                await db.query(
                    "UPDATE Holding SET quantity = ?, avg_cost = ? WHERE save_id = ? AND stock_id = ?",
                    [new_qty, new_avg, save_id, stock_id],
                )
            else:
                await db.query(
                    "INSERT INTO Holding (save_id, stock_id, quantity, avg_cost) VALUES (?, ?, ?, ?)",
                    [save_id, stock_id, quantity, exec_price],
                )

            avg_cost_snap = new_avg

            await db.query(
                "INSERT INTO AccountTransaction"
                " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
                " VALUES (?, ?, '交割戶', ?, '買股', ?, ?, ?)",
                [save_id, next_seq, current_date, total_cost, trading_balance,
                 f"買入 {stock_id} {quantity}張"],
            )
            next_seq += 1

        else:  # 賣
            if not has_holding or old_qty < quantity:
                await db.query(
                    "UPDATE StockOrder SET status = '已失效' WHERE order_id = ?",
                    [order_id],
                )
                continue

            new_qty  = old_qty - quantity
            proceeds = principal - fee - tax
            trading_balance += proceeds
            avg_cost_snap = round(old_avg, 2)

            if new_qty > 0:
                await db.query(
                    "UPDATE Holding SET quantity = ? WHERE save_id = ? AND stock_id = ?",
                    [new_qty, save_id, stock_id],
                )
            else:
                await db.query(
                    "DELETE FROM Holding WHERE save_id = ? AND stock_id = ?",
                    [save_id, stock_id],
                )

            await db.query(
                "INSERT INTO AccountTransaction"
                " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
                " VALUES (?, ?, '交割戶', ?, '賣股', ?, ?, ?)",
                [save_id, next_seq, current_date, proceeds, trading_balance,
                 f"賣出 {stock_id} {quantity}張"],
            )
            next_seq += 1

        await db.query(
            "INSERT INTO StockTransaction (order_id, exec_price, quantity, fee, tax, avg_cost_at_transact)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [order_id, exec_price, quantity, fee, tax, avg_cost_snap],
        )
        await db.query(
            "UPDATE StockOrder SET status = '已成交' WHERE order_id = ?",
            [order_id],
        )

    # Advance to next trading day (the nearest date that has any DailyPrice record)
    next_date_result = await db.query(
        "SELECT MIN(trade_date) AS next_date FROM DailyPrice WHERE trade_date > ?",
        [current_date],
    )
    next_date = next_date_result['rows'][0].get('next_date')

    if next_date is None:
        await db.query(
            "UPDATE SaveFile SET current_phase = '盤前', trading_balance = ?, status = '已結束'"
            " WHERE save_id = ?",
            [trading_balance, save_id],
        )
        return {"current_phase": "盤前", "current_date": current_date, "status": "已結束"}

    await db.query(
        "UPDATE SaveFile SET current_phase = '盤前', current_date = ?, trading_balance = ?"
        " WHERE save_id = ?",
        [next_date, trading_balance, save_id],
    )
    return {"current_phase": "盤前", "current_date": next_date}
