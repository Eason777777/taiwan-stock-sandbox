from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..database import SqlApiClient
from ..dependencies import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    account: str
    password: str


class LoginRequest(BaseModel):
    account: str
    password: str


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: SqlApiClient = Depends(get_db)):
    # TODO: hash password, INSERT INTO "User", enforce unique account
    pass


@router.post("/login")
async def login(body: LoginRequest, db: SqlApiClient = Depends(get_db)):
    # TODO: verify password hash, rotate session_id, return session_id
    pass


@router.post("/logout")
async def logout(db: SqlApiClient = Depends(get_db)):
    # TODO: clear session_id for current user
    pass
