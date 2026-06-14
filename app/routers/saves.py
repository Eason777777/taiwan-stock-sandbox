import math
import random
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user
from ..save_access import fetch_save_owned

router = APIRouter(
    prefix="/saves",
    tags=["saves"],
    dependencies=[Depends(get_current_user)],
)

MAX_ACTIVE_SAVES = 5
MAX_TOTAL_SAVES = 10
MIN_INITIAL_FUNDS = 50_000
MAX_INITIAL_FUNDS = 1_000_000

PHASE_SEQUENCE = ["PRE_MARKET", "INTRADAY", "POST_MARKET", "CLOSED"]


class CreateSaveRequest(BaseModel):
    save_name: str = Field(min_length=1, max_length=100)
    start_date: str | None = None       # YYYY-MM-DD；未提供則由系統隨機抽取有效交易日
    initial_funds: float | None = Field(default=None, allow_inf_nan=False)  # 50,000 ~ 1,000,000；未提供則由系統隨機決定


async def _holdings_market_value(db: SqlApiClient, save_id: int, current_phase: str, current_trade_date: str) -> float:
    """依目前交易階段估算所有持股市值總和。

    盤前：以前一有效交易日收盤價估算；盤中：以當日開盤價估算；
    盤後／收市：以當日收盤價估算。
    """
    holdings = (await db.query(
        "SELECT stock_id, quantity FROM holdings WHERE save_id = ?", [int(save_id)],
    ))["rows"]

    total = 0.0
    for h in holdings:
        stock_id = h["stock_id"]
        quantity = int(h["quantity"])

        if current_phase == "PRE_MARKET":
            rows = (await db.query(
                "SELECT close_price FROM daily_prices WHERE stock_id = ? AND trade_date < ?"
                " ORDER BY trade_date DESC LIMIT 1",
                [stock_id, current_trade_date],
            ))["rows"]
            price = float(rows[0]["close_price"]) if rows else None
        elif current_phase == "INTRADAY":
            rows = (await db.query(
                "SELECT open_price FROM daily_prices WHERE stock_id = ? AND trade_date = ?",
                [stock_id, current_trade_date],
            ))["rows"]
            price = float(rows[0]["open_price"]) if rows else None
        else:  # POST_MARKET / CLOSED
            rows = (await db.query(
                "SELECT close_price FROM daily_prices WHERE stock_id = ? AND trade_date = ?",
                [stock_id, current_trade_date],
            ))["rows"]
            price = float(rows[0]["close_price"]) if rows else None

        if price is not None:
            total += price * quantity * 1000

    return total


async def _save_summary(db: SqlApiClient, save: dict) -> dict:
    """在存檔資料上補上 total_asset 與 cumulative_return。"""
    save_id = int(save["save_id"])
    current_trade_date = str(save["current_trade_date"])[:10]

    holdings_value = await _holdings_market_value(db, save_id, save["current_phase"], current_trade_date)
    total_asset = float(save["savings_balance"]) + float(save["trading_balance"]) + holdings_value

    init_rows = (await db.query(
        "SELECT amount FROM account_transactions WHERE save_id = ? AND seq = 1", [save_id],
    ))["rows"]
    initial_funds = float(init_rows[0]["amount"]) if init_rows else None

    cumulative_return = (
        (total_asset - initial_funds) / initial_funds if initial_funds else None
    )

    summary = {
        **save,
        "start_date": str(save["start_date"])[:10],
        "current_trade_date": current_trade_date,
        "savings_balance": float(save["savings_balance"]),
        "trading_balance": float(save["trading_balance"]),
        "total_asset": round(total_asset, 2),
        "cumulative_return": round(cumulative_return, 4) if cumulative_return is not None else None,
    }
    # advancing 為內部推進鎖旗標，非對外 API 欄位
    summary.pop("advancing", None)
    return summary


def _compute_exec_price(
    phase_to_settle: str,
    side: str,
    order_type: str,
    price: float | None,
    dp: dict,
) -> float | None:
    """依結算階段與委託內容，回傳成交價；若本次無法成交則回傳 None。"""
    open_price = float(dp["open_price"])
    high_price = float(dp["high_price"])
    low_price = float(dp["low_price"])
    close_price = float(dp["close_price"])

    if phase_to_settle == "PRE_MARKET":
        # 盤前限價單：成交價一律為開盤價
        if side == "BUY" and price is not None and price >= open_price:
            return open_price
        if side == "SELL" and price is not None and price <= open_price:
            return open_price
        return None

    if phase_to_settle == "INTRADAY":
        if order_type == "LIMIT":
            # 盤中限價單：不提供價格改善，成交價為玩家指定限價
            if side == "BUY" and price is not None and price >= low_price:
                return price
            if side == "SELL" and price is not None and price <= high_price:
                return price
            return None
        return close_price  # MARKET

    return close_price  # POST_MARKET（盤後定價交易）


def _compute_fee_tax(principal: int, side: str) -> tuple[int, int]:
    """手續費／證交稅：元以下無條件捨去。"""
    fee = max(20, math.floor(principal * 0.001425))
    tax = math.floor(principal * 0.003) if side == "SELL" else 0
    return fee, tax


async def _record_fill(
    db: SqlApiClient,
    order_id: int,
    exec_price: float,
    quantity: int,
    fee: int,
    tax: int,
    avg_cost_snap: float,
) -> None:
    # status 已由搶佔 UPDATE 設為 FILLED，此處無需再次更新
    await db.query(
        "INSERT INTO stock_transactions (order_id, exec_price, quantity, fee, tax, avg_cost_at_transact)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [order_id, round(exec_price, 2), quantity, fee, tax, round(avg_cost_snap, 4)],
    )


async def _settle_buy(
    db: SqlApiClient,
    save_id: int,
    sim_date: str,
    order: dict,
    exec_price: float,
    principal: int,
    fee: int,
    trading_balance: float,
    next_seq: int,
) -> tuple[float, int] | None:
    """結算單筆 BUY 成交。回傳 (結算後餘額, 下一個 seq)；資金不足則回傳 None（破產）。"""
    order_id = int(order["order_id"])
    stock_id = str(order["stock_id"])
    quantity = int(order["quantity"])
    total_cost = principal + fee

    if trading_balance < total_cost:
        # 交割戶餘額不足：存檔破產，終止該存檔本次的交易與時間推進
        # 此單已透過搶佔 UPDATE 標記為 FILLED，但實際未成交，復原為 PENDING
        await db.query("UPDATE stock_orders SET status = 'PENDING' WHERE order_id = ?", [order_id])
        return None

    holding_rows = (await db.query(
        "SELECT quantity, avg_cost FROM holdings WHERE save_id = ? AND stock_id = ?",
        [save_id, stock_id],
    ))["rows"]
    has_holding = bool(holding_rows)
    old_qty = int(holding_rows[0]["quantity"]) if has_holding else 0
    old_avg = float(holding_rows[0]["avg_cost"]) if has_holding else 0.0

    new_qty = old_qty + quantity
    new_avg = (old_avg * old_qty + exec_price * quantity) / new_qty
    new_balance = trading_balance - total_cost

    if has_holding:
        await db.query(
            "UPDATE holdings SET quantity = ?, avg_cost = ? WHERE save_id = ? AND stock_id = ?",
            [new_qty, round(new_avg, 4), save_id, stock_id],
        )
    else:
        await db.query(
            "INSERT INTO holdings (save_id, stock_id, quantity, avg_cost) VALUES (?, ?, ?, ?)",
            [save_id, stock_id, quantity, round(exec_price, 4)],
        )

    await db.query(
        "INSERT INTO account_transactions"
        " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
        " VALUES (?, ?, 'TRADING', ?, 'BUY', ?, ?, ?)",
        [save_id, next_seq, sim_date, int(total_cost), int(new_balance),
         f"買入 {stock_id} {quantity}張"],
    )

    await _record_fill(db, order_id, exec_price, quantity, fee, 0, new_avg)
    return new_balance, next_seq + 1


async def _settle_sell(
    db: SqlApiClient,
    save_id: int,
    sim_date: str,
    order: dict,
    exec_price: float,
    principal: int,
    fee: int,
    tax: int,
    trading_balance: float,
    next_seq: int,
) -> tuple[float, int]:
    """結算單筆 SELL 成交。回傳 (結算後餘額, 下一個 seq)。"""
    order_id = int(order["order_id"])
    stock_id = str(order["stock_id"])
    quantity = int(order["quantity"])

    holding_rows = (await db.query(
        "SELECT quantity, avg_cost FROM holdings WHERE save_id = ? AND stock_id = ?",
        [save_id, stock_id],
    ))["rows"]
    old_qty = int(holding_rows[0]["quantity"]) if holding_rows else 0
    old_avg = float(holding_rows[0]["avg_cost"]) if holding_rows else 0.0

    new_qty = old_qty - quantity
    proceeds = principal - fee - tax
    new_balance = trading_balance + proceeds

    if new_qty > 0:
        await db.query(
            "UPDATE holdings SET quantity = ? WHERE save_id = ? AND stock_id = ?",
            [new_qty, save_id, stock_id],
        )
    else:
        await db.query("DELETE FROM holdings WHERE save_id = ? AND stock_id = ?", [save_id, stock_id])

    await db.query(
        "INSERT INTO account_transactions"
        " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
        " VALUES (?, ?, 'TRADING', ?, 'SELL', ?, ?, ?)",
        [save_id, next_seq, sim_date, int(proceeds), int(new_balance),
         f"賣出 {stock_id} {quantity}張"],
    )

    await _record_fill(db, order_id, exec_price, quantity, fee, tax, old_avg)
    return new_balance, next_seq + 1


async def _settle_phase(db: SqlApiClient, save: dict, phase_to_settle: str) -> tuple[float, bool]:
    """結算指定階段（phase_to_settle）送出且尚未結算的委託單。

    回傳 (結算後的交割戶餘額, 是否破產)。
    """
    save_id = int(save["save_id"])
    sim_date = str(save["current_trade_date"])[:10]
    trading_balance = float(save["trading_balance"])

    orders = (await db.query(
        "SELECT * FROM stock_orders WHERE save_id = ? AND phase = ? AND status = 'PENDING'",
        [save_id, phase_to_settle],
    ))["rows"]

    if not orders:
        return trading_balance, False

    seq_row = (await db.query(
        "SELECT COALESCE(MAX(seq), 0) AS max_seq FROM account_transactions WHERE save_id = ?", [save_id],
    ))["rows"][0]
    next_seq = int(seq_row["max_seq"]) + 1

    for order in orders:
        order_id = int(order["order_id"])
        stock_id = str(order["stock_id"])
        side = order["side"]              # BUY | SELL
        order_type = order["order_type"]  # LIMIT | MARKET
        quantity = int(order["quantity"])
        price = float(order["price"]) if order["price"] is not None else None

        # 條件式 UPDATE：搶佔仍為 PENDING 的訂單，與 cancel_order 互斥，
        # 避免「結算進行中同時被玩家撤銷」造成的 race condition。
        # 以 affectedRows 判斷是否搶到此單（== 0 代表已被 cancel_order 搶先撤銷）。
        claim = await db.query(
            "UPDATE stock_orders SET status = 'FILLED' WHERE order_id = ? AND status = 'PENDING'",
            [order_id],
        )
        if int(claim["rows"]["affectedRows"]) == 0:
            # 已被玩家撤銷，跳過此單
            continue

        dp_rows = (await db.query(
            "SELECT open_price, high_price, low_price, close_price FROM daily_prices"
            " WHERE stock_id = ? AND trade_date = ?",
            [stock_id, sim_date],
        ))["rows"]

        if not dp_rows:
            await db.query("UPDATE stock_orders SET status = 'EXPIRED' WHERE order_id = ?", [order_id])
            continue

        exec_price = _compute_exec_price(phase_to_settle, side, order_type, price, dp_rows[0])
        if exec_price is None:
            await db.query("UPDATE stock_orders SET status = 'EXPIRED' WHERE order_id = ?", [order_id])
            continue

        # 成交本金（元）：tick size 最多 2 位小數 * 1000 股，理論上必為整數，先 round 消除浮點誤差
        principal = round(exec_price * quantity * 1000)
        fee, tax = _compute_fee_tax(principal, side)

        if side == "BUY":
            result = await _settle_buy(db, save_id, sim_date, order, exec_price, principal, fee, trading_balance, next_seq)
            if result is None:
                return trading_balance, True
            trading_balance, next_seq = result
        else:
            trading_balance, next_seq = await _settle_sell(
                db, save_id, sim_date, order, exec_price, principal, fee, tax, trading_balance, next_seq,
            )

    return trading_balance, False


@router.get("")
async def list_saves(
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.query(
        "SELECT * FROM save_files WHERE user_id = ? ORDER BY created_at DESC",
        [int(current_user["user_id"])],
    )
    return [await _save_summary(db, save) for save in result["rows"]]


async def _check_save_name_available(db: SqlApiClient, user_id: int, save_name: str) -> None:
    dup = await db.query(
        "SELECT 1 FROM save_files WHERE user_id = ? AND save_name = ?", [user_id, save_name],
    )
    if dup["rows"]:
        raise HTTPException(status_code=409, detail="已存在同名存檔")


async def _check_save_limits(db: SqlApiClient, user_id: int) -> None:
    """建檔數量上限（快速預檢，仍為 TOCTOU；真正的把關在 INSERT 之後的回滾檢查）。"""
    active_result = await db.query(
        "SELECT COUNT(*) AS c FROM save_files WHERE user_id = ? AND status = 'ACTIVE'", [user_id],
    )
    if int(active_result["rows"][0]["c"]) >= MAX_ACTIVE_SAVES:
        raise HTTPException(status_code=400, detail=f"進行中存檔已達上限（{MAX_ACTIVE_SAVES} 個）")

    total_result = await db.query("SELECT COUNT(*) AS c FROM save_files WHERE user_id = ?", [user_id])
    if int(total_result["rows"][0]["c"]) >= MAX_TOTAL_SAVES:
        raise HTTPException(status_code=400, detail=f"存檔總數已達上限（{MAX_TOTAL_SAVES} 個）")


async def _resolve_start_date(db: SqlApiClient, requested: str | None) -> str:
    """起始日期：須為資料庫範圍內的有效交易日；未指定則隨機抽取。"""
    if requested is None:
        random_date_rows = (await db.query(
            "SELECT DISTINCT trade_date FROM daily_prices ORDER BY RAND() LIMIT 1", [],
        ))["rows"]
        return str(random_date_rows[0]["trade_date"])[:10]

    date_range = (await db.query(
        "SELECT MIN(trade_date) AS mn, MAX(trade_date) AS mx FROM daily_prices", [],
    ))["rows"][0]
    min_date = str(date_range["mn"])[:10]
    max_date = str(date_range["mx"])[:10]
    if requested < min_date or requested > max_date:
        raise HTTPException(status_code=400, detail=f"起始日期須介於 {min_date} 與 {max_date} 之間")

    valid = await db.query("SELECT 1 FROM daily_prices WHERE trade_date = ? LIMIT 1", [requested])
    if not valid["rows"]:
        raise HTTPException(status_code=400, detail="起始日期非有效交易日")
    return requested


def _resolve_initial_funds(requested: float | None) -> int:
    """起始資金：50,000 ~ 1,000,000；未指定則隨機決定。"""
    if requested is None:
        return random.randint(MIN_INITIAL_FUNDS, MAX_INITIAL_FUNDS)

    initial_funds = int(requested)
    if initial_funds < MIN_INITIAL_FUNDS or initial_funds > MAX_INITIAL_FUNDS:
        raise HTTPException(
            status_code=400,
            detail=f"initial_funds 須介於 {MIN_INITIAL_FUNDS} 與 {MAX_INITIAL_FUNDS} 之間",
        )
    return initial_funds


async def _enforce_save_limits_or_rollback(db: SqlApiClient, user_id: int, save_id: int) -> None:
    """上面的數量上限預檢與 INSERT 之間並非原子操作，並發建檔時可能多個請求都通過
    預檢、各自成功 INSERT，導致實際存檔數量超過上限。INSERT 完成後依 save_id（建立
    先後）重新計算累計數量：若加上本筆後超過上限，代表本筆是「後到」者，刪除剛剛
    建立的 save_files row（rollback）並回 400。較小 save_id（先到）者保留。
    """
    active_rank = await db.query(
        "SELECT COUNT(*) AS c FROM save_files WHERE user_id = ? AND status = 'ACTIVE' AND save_id <= ?",
        [user_id, save_id],
    )
    if int(active_rank["rows"][0]["c"]) > MAX_ACTIVE_SAVES:
        await db.query("DELETE FROM save_files WHERE save_id = ?", [save_id])
        raise HTTPException(status_code=400, detail=f"進行中存檔已達上限（{MAX_ACTIVE_SAVES} 個）")

    total_rank = await db.query(
        "SELECT COUNT(*) AS c FROM save_files WHERE user_id = ? AND save_id <= ?",
        [user_id, save_id],
    )
    if int(total_rank["rows"][0]["c"]) > MAX_TOTAL_SAVES:
        await db.query("DELETE FROM save_files WHERE save_id = ?", [save_id])
        raise HTTPException(status_code=400, detail=f"存檔總數已達上限（{MAX_TOTAL_SAVES} 個）")


@router.post("", status_code=201)
async def create_save(
    body: CreateSaveRequest,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = int(current_user["user_id"])

    await _check_save_name_available(db, user_id, body.save_name)
    await _check_save_limits(db, user_id)

    start_date = await _resolve_start_date(db, body.start_date)
    initial_funds = _resolve_initial_funds(body.initial_funds)

    # 直接讀取本次 INSERT 回應中的 insertId，不另外呼叫 SELECT LAST_INSERT_ID()：
    # 每次 db.query() 都是獨立的 HTTP request，sql-api 不保證後續查詢與這次 INSERT
    # 使用同一條 MySQL connection，LAST_INSERT_ID() 在不同 connection 上不可靠
    # （並發下會拿到 0 或別的 request 的值，導致後續以錯誤的 save_id 操作）。
    insert_result = await db.query(
        "INSERT INTO save_files"
        " (user_id, save_name, start_date, current_trade_date, current_phase, status, savings_balance, trading_balance)"
        " VALUES (?, ?, ?, ?, 'PRE_MARKET', 'ACTIVE', ?, 0)",
        [user_id, body.save_name, start_date, start_date, initial_funds],
    )
    save_id = int(insert_result["rows"]["insertId"])

    await _enforce_save_limits_or_rollback(db, user_id, save_id)

    await db.query(
        "INSERT INTO account_transactions"
        " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
        " VALUES (?, 1, 'SAVINGS', ?, 'INITIAL_DEPOSIT', ?, ?, '模擬開始初始存款')",
        [save_id, start_date, initial_funds, initial_funds],
    )
    await db.query(
        "INSERT INTO account_transactions"
        " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
        " VALUES (?, 2, 'TRADING', ?, 'INITIAL_DEPOSIT', 0, 0, '模擬開始初始存款')",
        [save_id, start_date],
    )

    save = (await db.query("SELECT * FROM save_files WHERE save_id = ?", [save_id]))["rows"][0]
    return await _save_summary(db, save)


@router.get("/{save_id}")
async def get_save(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    save = await fetch_save_owned(save_id, current_user, db)
    return await _save_summary(db, save)


@router.patch("/{save_id}/finish")
async def finish_save(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    save = await fetch_save_owned(save_id, current_user, db)
    save_id = int(save_id)

    if save["status"] != "ACTIVE":
        raise HTTPException(status_code=400, detail="存檔已結束，無法再次結束")

    # 條件式 UPDATE：僅在仍為 ACTIVE 且未被 /advance 鎖住（advancing = 0）時才結束。
    # /advance 在呼叫 _settle_phase 之前會先把 advancing 設為 1，並在結算完成、
    # 寫回 save_files 的同一個陳述句中才設回 0；因此只要 /advance 正在進行中，
    # finish 必定 affectedRows == 0，避免「結算副作用已寫入但 finish 把狀態
    # 改成 FINISHED」造成的資料不一致。
    update_result = await db.query(
        "UPDATE save_files SET status = 'FINISHED' WHERE save_id = ? AND status = 'ACTIVE' AND advancing = 0",
        [save_id],
    )
    if int(update_result["rows"]["affectedRows"]) == 0:
        raise HTTPException(status_code=400, detail="存檔已結束或正在推進中，無法結束")
    save["status"] = "FINISHED"
    return await _save_summary(db, save)


@router.delete("/{save_id}", status_code=204)
async def delete_save(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await fetch_save_owned(save_id, current_user, db)
    save_id = int(save_id)

    await db.query(
        "DELETE FROM stock_transactions WHERE order_id IN"
        " (SELECT order_id FROM stock_orders WHERE save_id = ?)",
        [save_id],
    )
    await db.query("DELETE FROM stock_orders WHERE save_id = ?", [save_id])
    await db.query("DELETE FROM holdings WHERE save_id = ?", [save_id])
    await db.query("DELETE FROM account_transactions WHERE save_id = ?", [save_id])
    await db.query("DELETE FROM watchlists WHERE save_id = ?", [save_id])
    await db.query("DELETE FROM save_files WHERE save_id = ?", [save_id])


async def _advance_within_day(db: SqlApiClient, save: dict, save_id: int, phase: str, current_date: str) -> dict:
    """結算「目前階段」自己送出且尚未結算的委託單，再切換到下一階段。"""
    new_balance, bankrupt = await _settle_phase(db, save, phase)
    next_phase = PHASE_SEQUENCE[PHASE_SEQUENCE.index(phase) + 1]
    new_status = "BANKRUPT" if bankrupt else "ACTIVE"

    await db.query(
        "UPDATE save_files SET current_phase = ?, trading_balance = ?, status = ?, advancing = 0"
        " WHERE save_id = ?",
        [next_phase, int(new_balance), new_status, save_id],
    )
    return {"current_phase": next_phase, "current_trade_date": current_date, "status": new_status}


async def _advance_from_closed(db: SqlApiClient, save: dict, save_id: int, current_date: str) -> dict:
    """CLOSED -> 結算盤後定價單 -> 下一交易日盤前 或 FINISHED。"""
    new_balance, bankrupt = await _settle_phase(db, save, "POST_MARKET")

    if bankrupt:
        await db.query(
            "UPDATE save_files SET trading_balance = ?, status = 'BANKRUPT', advancing = 0 WHERE save_id = ?",
            [int(new_balance), save_id],
        )
        return {"current_phase": "CLOSED", "current_trade_date": current_date, "status": "BANKRUPT"}

    next_date_rows = (await db.query(
        "SELECT MIN(trade_date) AS next_date FROM daily_prices WHERE trade_date > ?", [current_date],
    ))["rows"]
    next_date = next_date_rows[0].get("next_date")

    if next_date is None:
        await db.query(
            "UPDATE save_files SET trading_balance = ?, status = 'FINISHED', advancing = 0 WHERE save_id = ?",
            [int(new_balance), save_id],
        )
        return {"current_phase": "CLOSED", "current_trade_date": current_date, "status": "FINISHED"}

    next_date = str(next_date)[:10]
    await db.query(
        "UPDATE save_files SET current_trade_date = ?, current_phase = 'PRE_MARKET', trading_balance = ?,"
        " advancing = 0 WHERE save_id = ?",
        [next_date, int(new_balance), save_id],
    )
    return {"current_phase": "PRE_MARKET", "current_trade_date": next_date, "status": "ACTIVE"}


@router.post("/{save_id}/advance")
async def advance_phase(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    save = await fetch_save_owned(save_id, current_user, db)
    save_id = int(save_id)

    if save["status"] != "ACTIVE":
        raise HTTPException(status_code=400, detail="存檔已破產或結束，無法推進")

    # 推進鎖：在呼叫 _settle_phase（會寫入 stock_orders/holdings/account_transactions
    # 等副作用）之前，先搶佔 advancing 旗標。finish_save 僅在 advancing = 0 時才能
    # 成功，因此本次 advance 完成並寫回 save_files（同一陳述句中把 advancing 設回 0）
    # 之前，finish 不可能把 status 改成 FINISHED，避免「結算副作用已寫入但
    # save_files 最終狀態未更新」的不一致。
    claim = await db.query(
        "UPDATE save_files SET advancing = 1 WHERE save_id = ? AND status = 'ACTIVE' AND advancing = 0",
        [save_id],
    )
    if int(claim["rows"]["affectedRows"]) == 0:
        raise HTTPException(status_code=409, detail="存檔正在推進中或狀態已變更，請稍後再試")

    phase = save["current_phase"]
    current_date = str(save["current_trade_date"])[:10]

    if phase != "CLOSED":
        return await _advance_within_day(db, save, save_id, phase, current_date)

    return await _advance_from_closed(db, save, save_id, current_date)
