from fastapi import APIRouter, Depends
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


@router.get("/")
async def list_orders(save_id: int, db: SqlApiClient = Depends(get_db)):
    # TODO: SELECT * FROM StockOrder WHERE save_id = save_id
    pass


@router.post("/", status_code=201)
async def place_order(save_id: int, body: PlaceOrderRequest, db: SqlApiClient = Depends(get_db)):
    # TODO: validate phase (not 盤後), check listing_date, check limit_up/limit_down,
    #       check trading_balance (for buys), INSERT StockOrder status=待成交
    pass


@router.delete("/{order_id}", status_code=204)
async def cancel_order(save_id: int, order_id: int, db: SqlApiClient = Depends(get_db)):
    # TODO: set StockOrder.status = 已撤銷 (only if status = 待成交)
    pass
