import secrets
from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel
from ..database import SqlApiClient, sql_str
from ..dependencies import get_db, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegisterRequest(BaseModel):
    account: str
    password: str

class LoginRequest(BaseModel):
    account: str
    password: str


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: SqlApiClient = Depends(get_db)):
    # 1. 檢查 account 是否已存在
    rows = await db.query(f"""
        SELECT user_id FROM users WHERE account = '{sql_str(body.account)}'
    """)
    if rows['ok'] and rows['rows']:
        raise HTTPException(status_code=409, detail="帳號已存在")

    # 2. Hash 密碼，INSERT
    hashed = pwd_context.hash(body.password)
    await db.query(f"""
        INSERT INTO users (account, password_hash)
        VALUES ('{sql_str(body.account)}', '{hashed}')
    """)
    return {"message": "註冊成功"}


@router.post("/login")
async def login(body: LoginRequest, db: SqlApiClient = Depends(get_db)):
    # 1. 查出該 account 的 row
    rows = await db.query(f"""
        SELECT user_id, password_hash FROM users WHERE account = '{sql_str(body.account)}'
    """)
    if not rows['ok'] or not rows['rows']:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    
    user = rows['rows'][0]

    # 2. 驗證密碼
    if not pwd_context.verify(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    # 3. Rotate session_id（每次 login 都換新的，舊 session 自動失效）
    session_id = secrets.token_hex(18)  # 36 chars fits char(36)
    await db.query(f"""
        UPDATE users SET session_id = '{session_id}'
        WHERE user_id = {int(user["user_id"])}
    """)

    return {"session_id": session_id}


@router.post("/logout")
async def logout(
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),   # 需要先登入
):
    await db.query(f"""
        UPDATE users SET session_id = NULL
        WHERE user_id = {int(current_user["user_id"])}
    """)
    return {"message": "已登出"}
