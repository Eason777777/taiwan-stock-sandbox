from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves/{save_id}/watchlist",
    tags=["watchlist"],
    dependencies=[Depends(get_current_user)],
)

MAX_WATCHLIST_SIZE = 100


class AddWatchlistRequest(BaseModel):
    stock_id: str


async def _fetch_save_owned(save_id: int, current_user: dict, db: SqlApiClient) -> dict:
    result = await db.query(
        "SELECT save_id, user_id FROM save_files WHERE save_id = ?",
        [int(save_id)],
    )
    if not result["rows"]:
        raise HTTPException(status_code=404, detail="存檔不存在")
    save = result["rows"][0]
    if int(save["user_id"]) != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="無權存取此存檔")
    return save


@router.get("")
async def get_watchlist(
    save_id: int,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)
    result = await db.query(
        "SELECT w.stock_id, s.stock_name_zh, s.market_type, s.sector_name"
        " FROM watchlists w"
        " JOIN stocks s ON s.stock_id = w.stock_id"
        " WHERE w.save_id = ?"
        " ORDER BY w.stock_id",
        [int(save_id)],
    )
    return result["rows"]


@router.post("", status_code=201)
async def add_to_watchlist(
    save_id: int,
    body: AddWatchlistRequest,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)

    stock_result = await db.query(
        "SELECT stock_id FROM stocks WHERE stock_id = ?",
        [str(body.stock_id)],
    )
    if not stock_result["rows"]:
        raise HTTPException(status_code=404, detail="股票不存在")

    count_result = await db.query(
        "SELECT COUNT(*) AS c FROM watchlists WHERE save_id = ?", [int(save_id)],
    )
    if int(count_result["rows"][0]["c"]) >= MAX_WATCHLIST_SIZE:
        raise HTTPException(status_code=400, detail=f"自選股已達上限（{MAX_WATCHLIST_SIZE} 檔）")

    # Composite PK (save_id, stock_id) — INSERT IGNORE makes re-adding a no-op.
    await db.query(
        "INSERT IGNORE INTO watchlists (save_id, stock_id) VALUES (?, ?)",
        [int(save_id), str(body.stock_id)],
    )
    return {"save_id": int(save_id), "stock_id": str(body.stock_id)}


@router.delete("/{stock_id}", status_code=204)
async def remove_from_watchlist(
    save_id: int,
    stock_id: str,
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await _fetch_save_owned(save_id, current_user, db)
    await db.query(
        "DELETE FROM watchlists WHERE save_id = ? AND stock_id = ?",
        [int(save_id), str(stock_id)],
    )
