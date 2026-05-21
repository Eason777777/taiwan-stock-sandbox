from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user

router = APIRouter(
    prefix="/saves",
    tags=["saves"],
    dependencies=[Depends(get_current_user)],
)


class CreateSaveRequest(BaseModel):
    save_name: str
    start_date: str          # YYYY-MM-DD; system picks a random historical date if omitted
    initial_savings: float
    initial_trading: float


@router.get("/")
async def list_saves(db: SqlApiClient = Depends(get_db)):
    # TODO: SELECT * FROM SaveFile WHERE user_id = current_user.user_id
    pass


@router.post("/", status_code=201)
async def create_save(body: CreateSaveRequest, db: SqlApiClient = Depends(get_db)):
    # TODO: INSERT INTO SaveFile; create two AccountTransaction seed rows
    pass


@router.get("/{save_id}")
async def get_save(save_id: int, db: SqlApiClient = Depends(get_db)):
    # TODO: return SaveFile + current phase
    pass


@router.delete("/{save_id}", status_code=204)
async def delete_save(save_id: int, db: SqlApiClient = Depends(get_db)):
    # TODO: DELETE SaveFile (cascade)
    pass


@router.post("/{save_id}/advance")
async def advance_phase(save_id: int, db: SqlApiClient = Depends(get_db)):
    # TODO: advance current_phase enum; on 盤後→next day trigger order expiry + matching
    pass
