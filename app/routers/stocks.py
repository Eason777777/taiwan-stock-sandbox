from fastapi import APIRouter, Depends, HTTPException, Query
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/stocks",
    tags=["stocks"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def search_stocks(
    q: str | None = Query(None, description="Search by stock_id or stock_name_zh"),
    sector: str | None = Query(None, description="Filter by sector_name"),
    limit: int = Query(50, ge=1, le=500),
    db: SqlApiClient = Depends(get_db),
):
    sql = (
        "SELECT stock_id, stock_name_zh, stock_full_name_zh, market_type,"
        " sector_name, listing_date"
        " FROM stocks"
    )
    clauses: list[str] = []
    params: list = []

    if q:
        like = f"%{q}%"
        if q.isascii():
            # 股號為 ASCII，只有在關鍵字也是 ASCII 時才需要比對 stock_id，
            # 避免中文關鍵字與 stock_id 欄位比對時的編碼相容性問題。
            clauses.append("(stock_id LIKE ? OR stock_name_zh LIKE ? OR stock_full_name_zh LIKE ?)")
            params.extend([like, like, like])
        else:
            clauses.append("(stock_name_zh LIKE ? OR stock_full_name_zh LIKE ?)")
            params.extend([like, like])
    if sector:
        clauses.append("sector_name = ?")
        params.append(sector)

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY stock_id LIMIT ?"
    params.append(int(limit))

    result = await db.query(sql, params)
    return result["rows"]


@router.get("/{stock_id}")
async def get_stock(stock_id: str, db: SqlApiClient = Depends(get_db)):
    result = await db.query(
        "SELECT * FROM stocks WHERE stock_id = ?",
        [str(stock_id)],
    )
    if not result["rows"]:
        raise HTTPException(status_code=404, detail="股票不存在")
    return result["rows"][0]


@router.get("/{stock_id}/prices")
async def get_price_history(
    stock_id: str,
    from_date: str | None = Query(None, description="YYYY-MM-DD"),
    to_date: str | None = Query(None, description="YYYY-MM-DD"),
    save_id: int | None = Query(None, description="若提供，僅回傳該存檔目前交易日之前的資料（時空隔離）"),
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Confirm the stock exists so callers can tell "no such stock" from "no prices".
    stock = await db.query(
        "SELECT stock_id FROM stocks WHERE stock_id = ?",
        [str(stock_id)],
    )
    if not stock["rows"]:
        raise HTTPException(status_code=404, detail="股票不存在")

    sql = (
        "SELECT stock_id, trade_date, open_price, high_price, low_price, close_price, volume,"
        " ref_price, limit_up, limit_down,"
        " is_attention, is_disposition, is_full_delivery"
        " FROM daily_prices WHERE stock_id = ?"
    )
    params: list = [str(stock_id)]

    if save_id is not None:
        save = await db.query(
            "SELECT user_id, current_trade_date FROM save_files WHERE save_id = ?", [int(save_id)],
        )
        if not save["rows"]:
            raise HTTPException(status_code=404, detail="存檔不存在")
        if int(save["rows"][0]["user_id"]) != int(current_user["user_id"]):
            raise HTTPException(status_code=403, detail="無權存取此存檔")
        sql += " AND trade_date < ?"
        params.append(str(save["rows"][0]["current_trade_date"])[:10])

    if from_date:
        sql += " AND trade_date >= ?"
        params.append(from_date)
    if to_date:
        sql += " AND trade_date <= ?"
        params.append(to_date)

    sql += " ORDER BY trade_date"
    result = await db.query(sql, params)
    return result["rows"]
