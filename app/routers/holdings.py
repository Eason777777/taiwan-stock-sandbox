from fastapi import APIRouter, Depends
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves/{save_id}/holdings",
    tags=["holdings"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def list_holdings(save_id: int, db: SqlApiClient = Depends(get_db)):
    # TODO: JOIN Holding + DailyPrice on current_date for unrealized P&L
    pass


@router.get("/transactions")
async def list_transactions(save_id: int, db: SqlApiClient = Depends(get_db)):
    # TODO: SELECT StockTransaction JOIN StockOrder WHERE save_id = save_id
    pass
