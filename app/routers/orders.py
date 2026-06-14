import math

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves/{save_id}/orders",
    tags=["orders"],
    dependencies=[Depends(get_current_user)],
)


class PlaceOrderRequest(BaseModel):
    stock_id: str
    order_type: str   # "LIMIT" | "MARKET"
    side: str         # "BUY" | "SELL"
    price: float | None = Field(default=None, allow_inf_nan=False)   # required for LIMIT, null for MARKET
    quantity: int = Field(ge=1, le=10 ** 9)  # lots (張); 上限為避免巨大整數導致浮點運算 OverflowError


def _tick_size(price: float) -> float:
    """依台股升降單位規則，回傳該價位適用的最小跳動單位。"""
    if price < 10:
        return 0.01
    if price < 50:
        return 0.05
    if price < 100:
        return 0.1
    if price < 500:
        return 0.5
    if price < 1000:
        return 1.0
    return 5.0


async def _fetch_save_owned(save_id: int, current_user: dict, db: SqlApiClient) -> dict:
    result = await db.query(
        "SELECT * FROM save_files WHERE save_id = ?",
        [int(save_id)],
    )
    if not result["rows"]:
        raise HTTPException(status_code=404, detail="存檔不存在")
    save = result["rows"][0]
    if int(save["user_id"]) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    return save


@router.get("")
async def list_orders(
    save_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)
    result = await db.query(
        "SELECT * FROM stock_orders WHERE save_id = ? ORDER BY order_id DESC LIMIT ? OFFSET ?",
        [int(save_id), limit, offset],
    )
    return result["rows"]


@router.post("", status_code=201)
async def place_order(
    save_id: int,
    body: PlaceOrderRequest,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    save = await _fetch_save_owned(save_id, current_user, db)

    if save["status"] != "ACTIVE":
        raise HTTPException(status_code=400, detail="模擬已結束，無法下單")

    phase = save["current_phase"]
    current_date = str(save["current_trade_date"])[:10]

    # ── Validate request shape ──────────────────────────────────────────
    if body.order_type not in ("LIMIT", "MARKET"):
        raise HTTPException(status_code=400, detail="order_type 必須為 'LIMIT' 或 'MARKET'")
    if body.side not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="side 必須為 'BUY' 或 'SELL'")
    if body.quantity < 1:
        raise HTTPException(status_code=400, detail="quantity 必須 >= 1 (張)")
    if body.order_type == "LIMIT" and body.price is None:
        raise HTTPException(status_code=400, detail="限價單必須指定 price")
    if body.order_type == "MARKET" and body.price is not None:
        raise HTTPException(status_code=400, detail="市價單不可指定 price")

    # ── Phase-based order type restrictions ──────────────────────────────
    if phase == "CLOSED":
        raise HTTPException(status_code=400, detail="收市階段無法下單")
    if phase == "PRE_MARKET" and body.order_type != "LIMIT":
        raise HTTPException(status_code=400, detail="盤前僅限限價單")
    if phase == "POST_MARKET" and body.order_type != "MARKET":
        raise HTTPException(status_code=400, detail="盤後僅限定價單")

    quantity = int(body.quantity)
    price = float(body.price) if body.price is not None else None

    # ── Stock must exist and be listed on/before current_date ───────────
    stock_result = await db.query(
        "SELECT stock_id, listing_date FROM stocks WHERE stock_id = ?",
        [str(body.stock_id)],
    )
    if not stock_result["rows"]:
        raise HTTPException(status_code=404, detail="股票不存在")
    listing_date = stock_result["rows"][0]["listing_date"]
    if listing_date is not None and str(listing_date)[:10] > current_date:
        raise HTTPException(status_code=400, detail="該股票於當前日期尚未上市")

    # ── Stock must not be suspended on current_date ──────────────────────
    suspension_result = await db.query(
        "SELECT 1 FROM suspension_dates WHERE stock_id = ? AND suspend_start_date <= ?"
        " AND (resume_date IS NULL OR resume_date > ?)",
        [str(body.stock_id), current_date, current_date],
    )
    if suspension_result["rows"]:
        raise HTTPException(status_code=400, detail="該股票目前處於停牌狀態")

    # ── Today must have a price record (also supplies limit_up/limit_down) ─
    dp_result = await db.query(
        "SELECT low_price, high_price, limit_up, limit_down FROM daily_prices"
        " WHERE stock_id = ? AND trade_date = ?",
        [str(body.stock_id), current_date],
    )
    if not dp_result["rows"]:
        raise HTTPException(status_code=400, detail="當前日期無此股票報價（可能停牌或非交易日）")
    dp = dp_result["rows"][0]
    limit_up = float(dp["limit_up"]) if dp["limit_up"] is not None else None
    limit_down = float(dp["limit_down"]) if dp["limit_down"] is not None else None

    # ── Price-limit check (LIMIT only) ───────────────────────────────────
    if body.order_type == "LIMIT":
        if (limit_up is not None and price > limit_up) or (limit_down is not None and price < limit_down):
            raise HTTPException(
                status_code=400,
                detail=f"委託價格須介於跌停 {limit_down} 與漲停 {limit_up} 之間",
            )

        # ── Tick size check (LIMIT only) ─────────────────────────────────
        tick = _tick_size(price)
        if abs(round(price / tick) * tick - price) > 1e-6:
            raise HTTPException(status_code=400, detail=f"委託價格須符合升降單位（{tick} 元）")

    # ── Funds / holdings pre-check ──────────────────────────────────────
    if body.side == "BUY":
        # Worst-case cost: LIMIT 用限價，MARKET 用今日最高價估算
        est_price = price if price is not None else float(dp["high_price"])
        principal = round(est_price * quantity * 1000)
        fee = max(20, math.floor(principal * 0.001425))
        est_cost = principal + fee
        if float(save["trading_balance"]) < est_cost:
            raise HTTPException(status_code=400, detail="交割戶餘額不足以支應此買單")
    else:  # SELL — must hold enough lots, net of lots already committed by pending sells
        holding_result = await db.query(
            "SELECT quantity FROM holdings WHERE save_id = ? AND stock_id = ?",
            [int(save_id), str(body.stock_id)],
        )
        held = int(holding_result["rows"][0]["quantity"]) if holding_result["rows"] else 0
        pending_result = await db.query(
            "SELECT COALESCE(SUM(quantity), 0) AS committed FROM stock_orders"
            " WHERE save_id = ? AND stock_id = ? AND side = 'SELL' AND status = 'PENDING'",
            [int(save_id), str(body.stock_id)],
        )
        committed = int(pending_result["rows"][0]["committed"])
        if held - committed < quantity:
            raise HTTPException(status_code=400, detail="持股不足以支應此賣單")

    # ── Insert the order as PENDING ──────────────────────────────────────
    # 直接讀取本次 INSERT 回應中的 insertId，不另外呼叫 SELECT LAST_INSERT_ID()：
    # 每次 db.query() 都是獨立的 HTTP request，sql-api 不保證後續查詢與這次 INSERT
    # 使用同一條 MySQL connection，LAST_INSERT_ID() 在不同 connection 上不可靠
    # （並發下會拿到 0 或別的 request 的值）。
    try:
        insert_result = await db.query(
            "INSERT INTO stock_orders"
            " (save_id, stock_id, sim_date, phase, order_type, side, price, quantity, status)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')",
            [int(save_id), str(body.stock_id), current_date, phase,
             body.order_type, body.side, price, quantity],
        )
    except RuntimeError as e:
        # 上面讀取的 phase（save["current_phase"]）與這筆 INSERT 之間並非原子操作；
        # 若同時有 /advance 推進了階段，DB 端的 trigger 會擋下「訂單 phase 與
        # save_files.current_phase 不符」的 INSERT 並回傳錯誤。將此情況視為
        # 「下單時存檔階段已變更」(409)，而非讓其以未預期錯誤 (500) 外洩。
        if "phase" in str(e).lower():
            raise HTTPException(status_code=409, detail="存檔階段已變更，請重新查詢存檔狀態後再下單")
        raise
    order_id = int(insert_result["rows"]["insertId"])

    if body.side == "SELL":
        # 上面的「持股 - 待成交賣單」預檢與這筆 INSERT 之間並非原子操作，並發下單時
        # 多個請求可能都通過預檢、各自成功 INSERT，導致賣單總量超過實際持股。
        # INSERT 完成後依 order_id（下單先後）重新計算累計賣單數量：
        # 若加上本單後超過實際持股，代表本單是「後到」的超賣單，撤銷本單並回 400。
        holding_check = await db.query(
            "SELECT quantity FROM holdings WHERE save_id = ? AND stock_id = ?",
            [int(save_id), str(body.stock_id)],
        )
        held_now = int(holding_check["rows"][0]["quantity"]) if holding_check["rows"] else 0

        pending_sells = (await db.query(
            "SELECT order_id, quantity FROM stock_orders"
            " WHERE save_id = ? AND stock_id = ? AND side = 'SELL' AND status = 'PENDING'"
            " ORDER BY order_id",
            [int(save_id), str(body.stock_id)],
        ))["rows"]

        cumulative = 0
        for o in pending_sells:
            cumulative += int(o["quantity"])
            if int(o["order_id"]) == order_id:
                if cumulative > held_now:
                    await db.query(
                        "UPDATE stock_orders SET status = 'CANCELED' WHERE order_id = ? AND status = 'PENDING'",
                        [order_id],
                    )
                    raise HTTPException(status_code=400, detail="持股不足以支應此賣單")
                break

    order_result = await db.query(
        "SELECT * FROM stock_orders WHERE order_id = ?",
        [order_id],
    )
    return order_result["rows"][0]


@router.delete("/{order_id}", status_code=204)
async def cancel_order(
    save_id: int,
    order_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)

    result = await db.query(
        "SELECT order_id, status FROM stock_orders WHERE order_id = ? AND save_id = ?",
        [int(order_id), int(save_id)],
    )
    if not result["rows"]:
        raise HTTPException(status_code=404, detail="委託單不存在")

    if result["rows"][0]["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="僅能撤銷待成交的委託單")

    # 條件式 UPDATE：僅在仍為 PENDING 時才撤銷，避免與 /advance 結算、或另一個並發的
    # cancel 請求發生 race condition。以 affectedRows 判斷本次請求是否真正搶到此單
    # （兩個並發請求即使都讀到 status='PENDING'，MySQL 仍會序列化這兩個 UPDATE，
    # 只有一個能真正將 status 從 PENDING 改為 CANCELED）。
    update_result = await db.query(
        "UPDATE stock_orders SET status = 'CANCELED' WHERE order_id = ? AND status = 'PENDING'",
        [int(order_id)],
    )
    if int(update_result["rows"]["affectedRows"]) == 0:
        raise HTTPException(status_code=400, detail="僅能撤銷待成交的委託單")
