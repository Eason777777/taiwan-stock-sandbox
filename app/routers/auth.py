import secrets
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Request
from passlib.context import CryptContext
from pydantic import BaseModel
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user, get_client_ip

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 登入暴力破解防護：每個帳號在 LOGIN_WINDOW_SECONDS 內失敗次數達上限即鎖定
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60
_failed_logins: dict[str, list[float]] = defaultdict(list)

# session 有效期限：每次登入後 SESSION_TTL_HOURS 小時內有效，過期需重新登入
SESSION_TTL_HOURS = 2


class RegisterRequest(BaseModel):
    account: str
    password: str

class LoginRequest(BaseModel):
    account: str
    password: str


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: SqlApiClient = Depends(get_db)):
    # 0. 帳號/密碼基本格式檢查
    if not body.account.strip() or not body.password:
        raise HTTPException(status_code=422, detail="帳號與密碼不可為空")
    if len(body.account) > 50 or len(body.password) > 72:
        raise HTTPException(status_code=422, detail="帳號或密碼長度超過限制")

    # 1. 檢查 account 是否已存在
    rows = await db.query(
        "SELECT user_id FROM users WHERE account = ?",
        [body.account],
    )
    if rows['ok'] and rows['rows']:
        raise HTTPException(status_code=409, detail="帳號已存在")

    # 2. Hash 密碼，INSERT
    hashed = pwd_context.hash(body.password)
    try:
        await db.query(
            "INSERT INTO users (account, password_hash) VALUES (?, ?)",
            [body.account, hashed],
        )
    except RuntimeError as e:
        # 步驟 1 的存在性檢查與此處的 INSERT 之間並非原子操作；
        # 並發註冊同一帳號時，第二個請求會違反 uq_users_account 而由 sql-api 回傳錯誤。
        # 將此情況視為「帳號已存在」(409)，而非讓其以未預期錯誤 (500) 外洩。
        if "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="帳號已存在")
        raise
    return {"message": "註冊成功"}


@router.post("/login")
async def login(body: LoginRequest, request: Request, db: SqlApiClient = Depends(get_db)):
    # 0. 暴力破解防護：近期失敗次數過多則直接鎖定
    now = time.time()
    attempts = _failed_logins[body.account]
    attempts[:] = [t for t in attempts if now - t < LOGIN_WINDOW_SECONDS]
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="登入失敗次數過多，請稍後再試")

    # 1. 查出該 account 的 row
    rows = await db.query(
        "SELECT user_id, password_hash FROM users WHERE account = ?",
        [body.account],
    )
    if not rows['ok'] or not rows['rows']:
        attempts.append(now)
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    user = rows['rows'][0]

    # 2. 驗證密碼
    if not pwd_context.verify(body.password, user["password_hash"]):
        attempts.append(now)
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    attempts.clear()

    # 3. Rotate session_id（每次 login 都換新的，舊 session 自動失效）
    # 過期時間交由 DB 端的 NOW() 計算，避免應用伺服器與 DB 時區不一致的問題
    # 同時記錄來源 IP，後續請求若來源 IP 不同則拒絕（降低 session_id 外洩後的可用範圍）
    session_id = secrets.token_hex(18)  # 36 chars fits char(36)
    await db.query(
        # SESSION_TTL_HOURS 為內部常數（非使用者輸入），直接嵌入 SQL 是安全的；
        # INTERVAL 子句不支援以 ? 佔位符傳入數值。
        f"UPDATE users SET session_id = ?, session_expires_at = NOW() + INTERVAL {SESSION_TTL_HOURS} HOUR,"
        " session_ip = ? WHERE user_id = ?",
        [session_id, get_client_ip(request), int(user["user_id"])],
    )

    return {"session_id": session_id}


@router.post("/logout")
async def logout(
    db: SqlApiClient = Depends(get_db),
    current_user: dict = Depends(get_current_user),   # 需要先登入
):
    await db.query(
        "UPDATE users SET session_id = NULL, session_expires_at = NULL, session_ip = NULL WHERE user_id = ?",
        [int(current_user["user_id"])],
    )
    return {"message": "已登出"}
