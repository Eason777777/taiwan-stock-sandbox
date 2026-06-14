from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves/{save_id}/accounts",
    tags=["accounts"],
    dependencies=[Depends(get_current_user)],
)


class TransferRequest(BaseModel):
    direction: str   # "savings_to_trading" | "trading_to_savings"
    amount: float = Field(allow_inf_nan=False)


MAX_SEQ_RETRIES = 5


async def _insert_account_transaction(
    db: SqlApiClient,
    save_id: int,
    account_type: str,
    sim_date: str,
    change_type: str,
    amount: float,
    balance_after: float,
    note: str,
) -> None:
    """以 CAS（compare-and-swap）方式寫入 account_transactions：
    """
    for attempt in range(MAX_SEQ_RETRIES):
        seq_result = await db.query(
            "SELECT COALESCE(MAX(seq), 0) AS max_seq FROM account_transactions WHERE save_id = ?",
            [save_id],
        )
        next_seq = int(seq_result["rows"][0]["max_seq"]) + 1
        try:
            await db.query(
                "INSERT INTO account_transactions"
                " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [save_id, next_seq, account_type, sim_date, change_type, amount, balance_after, note],
            )
            return
        except RuntimeError as e:
            if "account_transactions.PRIMARY" in str(e) and attempt < MAX_SEQ_RETRIES - 1:
                continue
            raise


async def _fetch_save(save_id: int, current_user: dict, db: SqlApiClient) -> dict:
    result = await db.query(
        "SELECT save_id, user_id, current_trade_date, savings_balance, trading_balance"
        " FROM save_files WHERE save_id = ?",
        [save_id],
    )
    if not result["rows"]:
        raise HTTPException(status_code=404, detail="存檔不存在")
    save = result["rows"][0]
    if int(save["user_id"]) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    return save


@router.get("/history")
async def get_account_history(
    save_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save(save_id, current_user, db)
    result = await db.query(
        "SELECT * FROM account_transactions WHERE save_id = ? ORDER BY seq LIMIT ? OFFSET ?",
        [save_id, limit, offset],
    )
    return result["rows"]


@router.post("/transfer")
async def transfer(
    save_id: int,
    body: TransferRequest,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if body.direction not in ("savings_to_trading", "trading_to_savings"):
        raise HTTPException(status_code=400, detail="direction 必須為 'savings_to_trading' 或 'trading_to_savings'")
    amount = float(body.amount)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount 必須為正數")

    save = await _fetch_save(save_id, current_user, db)
    savings = float(save["savings_balance"])
    trading = float(save["trading_balance"])
    sim_date = str(save["current_trade_date"])[:10]

    if body.direction == "savings_to_trading":
        if savings < amount:
            raise HTTPException(status_code=400, detail="存款戶餘額不足")
        new_savings = savings - amount
        new_trading = trading + amount
        debit_acct, credit_acct = "SAVINGS", "TRADING"
    else:
        if trading < amount:
            raise HTTPException(status_code=400, detail="交割戶餘額不足")
        new_savings = savings + amount
        new_trading = trading - amount
        debit_acct, credit_acct = "TRADING", "SAVINGS"

    await db.query(
        "UPDATE save_files SET savings_balance = ?, trading_balance = ? WHERE save_id = ?",
        [round(new_savings, 2), round(new_trading, 2), save_id],
    )

    debit_balance_after = new_savings if debit_acct == "SAVINGS" else new_trading
    await _insert_account_transaction(
        db, save_id, debit_acct, sim_date, "TRANSFER_OUT", round(amount, 2), round(debit_balance_after, 2), "帳戶轉帳",
    )

    credit_balance_after = new_trading if credit_acct == "TRADING" else new_savings
    await _insert_account_transaction(
        db, save_id, credit_acct, sim_date, "TRANSFER_IN", round(amount, 2), round(credit_balance_after, 2), "帳戶轉帳",
    )

    return {"savings_balance": round(new_savings, 2), "trading_balance": round(new_trading, 2)}
