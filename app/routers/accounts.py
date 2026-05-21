from fastapi import APIRouter, Depends
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


@router.get("/history")
async def get_account_history(save_id: int, db: SqlApiClient = Depends(get_db)):
    # TODO: SELECT * FROM AccountTransaction WHERE save_id = save_id ORDER BY seq
    pass


@router.post("/transfer")
async def transfer(save_id: int, body: TransferRequest, db: SqlApiClient = Depends(get_db)):
    # TODO: update savings_balance / trading_balance in SaveFile; INSERT AccountTransaction rows
    pass
