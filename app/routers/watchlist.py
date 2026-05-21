from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves/{save_id}/watchlist",
    tags=["watchlist"],
    dependencies=[Depends(get_current_user)],
)


class AddWatchlistRequest(BaseModel):
    stock_id: str


@router.get("/")
async def get_watchlist(save_id: int, db: SqlApiClient = Depends(get_db)):
    # TODO: SELECT Watchlist JOIN Stock WHERE save_id = save_id
    pass


@router.post("/", status_code=201)
async def add_to_watchlist(save_id: int, body: AddWatchlistRequest, db: SqlApiClient = Depends(get_db)):
    # TODO: INSERT INTO Watchlist (save_id, stock_id) ON CONFLICT DO NOTHING
    pass


@router.delete("/{stock_id}", status_code=204)
async def remove_from_watchlist(save_id: int, stock_id: str, db: SqlApiClient = Depends(get_db)):
    # TODO: DELETE FROM Watchlist WHERE save_id = save_id AND stock_id = stock_id
    pass
