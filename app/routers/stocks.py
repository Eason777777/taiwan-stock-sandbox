from fastapi import APIRouter, Depends, Query
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/stocks",
    tags=["stocks"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def search_stocks(
    q: str | None = Query(None, description="Search by stock_id or name"),
    sector: str | None = Query(None),
    db: SqlApiClient = Depends(get_db),
):
    # TODO: SELECT FROM Stock WHERE stock_id ILIKE %q% OR stock_name_zh ILIKE %q%
    pass


@router.get("/{stock_id}")
async def get_stock(stock_id: str, db: SqlApiClient = Depends(get_db)):
    # TODO: SELECT * FROM Stock WHERE stock_id = stock_id
    pass


@router.get("/{stock_id}/prices")
async def get_price_history(
    stock_id: str,
    from_date: str | None = Query(None, description="YYYY-MM-DD"),
    to_date: str | None = Query(None, description="YYYY-MM-DD"),
    db: SqlApiClient = Depends(get_db),
):
    # TODO: SELECT FROM DailyPrice WHERE stock_id = stock_id AND trade_date BETWEEN ...
    pass
