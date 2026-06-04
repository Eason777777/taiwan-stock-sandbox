from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves/{save_id}/accounts",
    tags=["accounts"],
    dependencies=[Depends(get_current_user)],
)


class TransferRequest(BaseModel):
    direction: str   # "savings_to_trading" | "trading_to_savings"
    amount: float


async def _fetch_save(save_id: int, current_user: dict, db: SqlApiClient) -> dict:
    result = await db.query(
        "SELECT save_id, user_id, current_date, savings_balance, trading_balance"
        " FROM SaveFile WHERE save_id = ?",
        [save_id],
    )
    if not result['rows']:
        raise HTTPException(status_code=404, detail="存檔不存在")
    save = result['rows'][0]
    if int(save['user_id']) != int(current_user['user_id']):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    return save


@router.get("/history")
async def get_account_history(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save(save_id, current_user, db)
    result = await db.query(
        "SELECT * FROM AccountTransaction WHERE save_id = ? ORDER BY seq",
        [save_id],
    )
    return result['rows']


@router.post("/transfer")
async def transfer(
    save_id: int,
    body: TransferRequest,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if body.direction not in ("savings_to_trading", "trading_to_savings"):
        raise HTTPException(status_code=422, detail="direction 必須為 'savings_to_trading' 或 'trading_to_savings'")
    amount = int(body.amount)
    if amount <= 0:
        raise HTTPException(status_code=422, detail="amount 必須為正整數")

    save = await _fetch_save(save_id, current_user, db)
    savings = int(save['savings_balance'])
    trading = int(save['trading_balance'])
    sim_date = save['current_date']

    if body.direction == "savings_to_trading":
        if savings < amount:
            raise HTTPException(status_code=400, detail="存款戶餘額不足")
        new_savings = savings - amount
        new_trading = trading + amount
        debit_acct, credit_acct = "存款戶", "交割戶"
    else:
        if trading < amount:
            raise HTTPException(status_code=400, detail="交割戶餘額不足")
        new_savings = savings + amount
        new_trading = trading - amount
        debit_acct, credit_acct = "交割戶", "存款戶"

    # Get current max seq for this save to assign the next two seq numbers atomically
    seq_result = await db.query(
        "SELECT COALESCE(MAX(seq), 0) AS max_seq FROM AccountTransaction WHERE save_id = ?",
        [save_id],
    )
    next_seq = int(seq_result['rows'][0]['max_seq']) + 1

    await db.query(
        "UPDATE SaveFile SET savings_balance = ?, trading_balance = ? WHERE save_id = ?",
        [new_savings, new_trading, save_id],
    )

    debit_balance_after = new_savings if debit_acct == "存款戶" else new_trading
    await db.query(
        "INSERT INTO AccountTransaction"
        " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [save_id, next_seq, debit_acct, sim_date, "轉出", amount, debit_balance_after, "帳戶轉帳"],
    )

    credit_balance_after = new_trading if credit_acct == "交割戶" else new_savings
    await db.query(
        "INSERT INTO AccountTransaction"
        " (save_id, seq, account_type, sim_date, change_type, amount, balance_after, note)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [save_id, next_seq + 1, credit_acct, sim_date, "轉入", amount, credit_balance_after, "帳戶轉帳"],
    )

    return {"savings_balance": new_savings, "trading_balance": new_trading}
