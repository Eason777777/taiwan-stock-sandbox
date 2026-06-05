from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves/{save_id}/orders",
    tags=["orders"],
    dependencies=[Depends(get_current_user)],
)


class PlaceOrderRequest(BaseModel):
    stock_id: str
    order_type: str   # "限價" | "市價"
    side: str         # "買" | "賣"
    price: float | None = None   # required for 限價, null for 市價
    quantity: int     # lots (張); must be >= 1


async def _fetch_save_owned(save_id: int, current_user: dict, db: SqlApiClient) -> dict:
    result = await db.query(
        "SELECT * FROM SaveFile WHERE save_id = ?",
        [int(save_id)],
    )
    if not result['rows']:
        raise HTTPException(status_code=404, detail="存檔不存在")
    save = result['rows'][0]
    if int(save['user_id']) != int(current_user['user_id']):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    return save


@router.get("/")
async def list_orders(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)
    result = await db.query(
        "SELECT * FROM StockOrder WHERE save_id = ? ORDER BY order_id DESC",
        [int(save_id)],
    )
    return result['rows']


@router.post("/", status_code=201)
async def place_order(
    save_id: int,
    body: PlaceOrderRequest,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    save = await _fetch_save_owned(save_id, current_user, db)

    if save['status'] != '進行中':
        raise HTTPException(status_code=400, detail="模擬已結束，無法下單")

    phase = save['current_phase']
    current_date = str(save['current_date'])

    # Orders can only be placed before matching runs (盤後 → next day), so 盤後 is closed.
    if phase == '盤後':
        raise HTTPException(status_code=400, detail="盤後階段無法下單")

    # ── Validate request shape ──────────────────────────────────────────
    if body.order_type not in ('限價', '市價'):
        raise HTTPException(status_code=422, detail="order_type 必須為 '限價' 或 '市價'")
    if body.side not in ('買', '賣'):
        raise HTTPException(status_code=422, detail="side 必須為 '買' 或 '賣'")
    if body.quantity < 1:
        raise HTTPException(status_code=422, detail="quantity 必須 >= 1 (張)")
    if body.order_type == '限價' and body.price is None:
        raise HTTPException(status_code=422, detail="限價單必須指定 price")
    if body.order_type == '市價' and body.price is not None:
        raise HTTPException(status_code=422, detail="市價單不可指定 price")

    quantity = int(body.quantity)
    price = float(body.price) if body.price is not None else None

    # ── Stock must exist and be listed on/before current_date ───────────
    stock_result = await db.query(
        "SELECT stock_id, listing_date FROM Stock WHERE stock_id = ?",
        [str(body.stock_id)],
    )
    if not stock_result['rows']:
        raise HTTPException(status_code=404, detail="股票不存在")
    listing_date = str(stock_result['rows'][0]['listing_date'])
    if listing_date > current_date:
        raise HTTPException(status_code=400, detail="該股票於當前日期尚未上市")

    # ── Today must have a price record (also supplies limit_up/limit_down) ─
    dp_result = await db.query(
        "SELECT low, high, limit_up, limit_down FROM DailyPrice"
        " WHERE stock_id = ? AND trade_date = ?",
        [str(body.stock_id), current_date],
    )
    if not dp_result['rows']:
        raise HTTPException(status_code=400, detail="當前日期無此股票報價（可能停牌或非交易日）")
    dp = dp_result['rows'][0]
    limit_up = float(dp['limit_up'])
    limit_down = float(dp['limit_down'])

    # ── Price-limit check (限價 only) ───────────────────────────────────
    if body.order_type == '限價':
        if price < limit_down or price > limit_up:
            raise HTTPException(
                status_code=400,
                detail=f"委託價格須介於跌停 {limit_down} 與漲停 {limit_up} 之間",
            )

    # ── Funds / holdings pre-check ──────────────────────────────────────
    if body.side == '買':
        # Worst-case cost: 限價 uses the limit price, 市價 uses today's high.
        est_price = price if price is not None else float(dp['high'])
        principal = int(est_price * quantity * 1000)
        fee = max(20, int(principal * 0.001425))
        est_cost = principal + fee
        if int(save['trading_balance']) < est_cost:
            raise HTTPException(status_code=400, detail="交割戶餘額不足以支應此買單")
    else:  # 賣 — must hold enough lots, net of lots already committed by pending sells
        holding_result = await db.query(
            "SELECT quantity FROM Holding WHERE save_id = ? AND stock_id = ?",
            [int(save_id), str(body.stock_id)],
        )
        held = int(holding_result['rows'][0]['quantity']) if holding_result['rows'] else 0
        pending_result = await db.query(
            "SELECT COALESCE(SUM(quantity), 0) AS committed FROM StockOrder"
            " WHERE save_id = ? AND stock_id = ? AND side = '賣' AND status = '待成交'",
            [int(save_id), str(body.stock_id)],
        )
        committed = int(pending_result['rows'][0]['committed'])
        if held - committed < quantity:
            raise HTTPException(status_code=400, detail="持股不足以支應此賣單")

    # ── Insert the order as 待成交 ──────────────────────────────────────
    await db.query(
        "INSERT INTO StockOrder"
        " (save_id, stock_id, sim_date, phase, order_type, side, price, quantity, status)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, '待成交')",
        [int(save_id), str(body.stock_id), current_date, phase,
         body.order_type, body.side, price, quantity],
    )

    id_result = await db.query("SELECT LAST_INSERT_ID() AS order_id", [])
    order_id = int(id_result['rows'][0]['order_id'])

    order_result = await db.query(
        "SELECT * FROM StockOrder WHERE order_id = ?",
        [order_id],
    )
    return order_result['rows'][0]


@router.delete("/{order_id}", status_code=204)
async def cancel_order(
    save_id: int,
    order_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)

    result = await db.query(
        "SELECT order_id, status FROM StockOrder WHERE order_id = ? AND save_id = ?",
        [int(order_id), int(save_id)],
    )
    if not result['rows']:
        raise HTTPException(status_code=404, detail="委託單不存在")

    if result['rows'][0]['status'] != '待成交':
        raise HTTPException(status_code=400, detail="僅能撤銷待成交的委託單")

    await db.query(
        "UPDATE StockOrder SET status = '已撤銷' WHERE order_id = ?",
        [int(order_id)],
    )
