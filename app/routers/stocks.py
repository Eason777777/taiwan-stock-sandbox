from fastapi import APIRouter, Depends, HTTPException, Query
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/stocks",
    tags=["stocks"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def search_stocks(
    q: str | None = Query(None, description="Search by stock_id or stock_name_zh"),
    sector: str | None = Query(None, description="Filter by sector_name"),
    limit: int = Query(50, ge=1, le=500),
    db: SqlApiClient = Depends(get_db),
):
    sql = (
        "SELECT stock_id, stock_name_zh, stock_full_name_zh, market_type,"
        " sector_name, listing_date"
        " FROM Stock"
    )
    clauses: list[str] = []
    params: list = []

    if q:
        clauses.append("(stock_id LIKE ? OR stock_name_zh LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])
    if sector:
        clauses.append("sector_name = ?")
        params.append(sector)

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY stock_id LIMIT ?"
    params.append(int(limit))

    result = await db.query(sql, params)
    return result['rows']


@router.get("/{stock_id}")
async def get_stock(stock_id: str, db: SqlApiClient = Depends(get_db)):
    result = await db.query(
        "SELECT * FROM Stock WHERE stock_id = ?",
        [str(stock_id)],
    )
    if not result['rows']:
        raise HTTPException(status_code=404, detail="股票不存在")
    return result['rows'][0]


@router.get("/{stock_id}/prices")
async def get_price_history(
    stock_id: str,
    from_date: str | None = Query(None, description="YYYY-MM-DD"),
    to_date: str | None = Query(None, description="YYYY-MM-DD"),
    db: SqlApiClient = Depends(get_db),
):
    # Confirm the stock exists so callers can tell "no such stock" from "no prices".
    stock = await db.query(
        "SELECT stock_id FROM Stock WHERE stock_id = ?",
        [str(stock_id)],
    )
    if not stock['rows']:
        raise HTTPException(status_code=404, detail="股票不存在")

    sql = (
        "SELECT stock_id, trade_date, open, high, low, close, volume,"
        " ref_price, limit_up, limit_down,"
        " is_attention, is_disposition, is_full_delivery"
        " FROM DailyPrice WHERE stock_id = ?"
    )
    params: list = [str(stock_id)]

    if from_date:
        sql += " AND trade_date >= ?"
        params.append(from_date)
    if to_date:
        sql += " AND trade_date <= ?"
        params.append(to_date)

    sql += " ORDER BY trade_date"
    result = await db.query(sql, params)
    return result['rows']
