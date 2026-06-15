import asyncio
import secrets
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from passlib.context import CryptContext
from pydantic import BaseModel
from ..database import SqlApiClient
from ..dependencies import get_db, get_current_user, get_client_ip, verify_session
from ..constants import SESSION_TTL_SECONDS

router = APIRouter(prefix="/auth", tags=["auth"])
# bcrypt__rounds 由預設 12 提高到 14：單次 hash 耗時隨之倍增（約 4 倍），
# 提高腳本大量註冊帳號的成本，且不需要前端配合（CAPTCHA/email 驗證）。
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=14)

# 註冊時的 bcrypt hash 屬於 CPU-bound 同步運算，丟到獨立 thread pool 執行，
# 避免卡住主 event loop（影響其他使用者的請求）。
# max_workers 限制同時計算 hash 的數量；HASH_QUEUE_MAX 限制「正在等待或計算中」
# 的總數，超過就直接回 429，避免請求無限堆積。
_hash_executor = ThreadPoolExecutor(max_workers=2)
HASH_QUEUE_MAX = 10
_hash_pending = 0
_hash_pending_lock = asyncio.Lock()

# 登入暴力破解防護：每個帳號在 LOGIN_WINDOW_SECONDS 內失敗次數達上限即鎖定
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60
_failed_logins: dict[str, list[float]] = defaultdict(list)

# session 有效期限 SESSION_TTL_HOURS 定義於 app/constants.py（供 dependencies 一同 import）。
# 改為滑動過期：每次通過驗證的請求都會把過期時間延長至 NOW() + SESSION_TTL_HOURS 小時，
# 因此這是「閒置上限」而非從登入起算的總時長上限。

# 註冊防護：honeypot 欄位若被填值，將該 IP 寫入 blacklisted_ips 黑名單；常見腳本工具的 User-Agent 直接拒絕
_BLOCKED_USER_AGENT_PREFIXES = ("curl", "python-requests", "go-http-client", "postmanruntime", "wget")

_DECOY_HTML = """<!DOCTYPE html>
<html lang="zh-Hant">
<head><meta charset="utf-8"><title>Admin Panel</title></head>
<body>
<h1>Internal Admin Panel</h1>
<p>Debug mode is enabled.</p>
<!-- FLAG{nice_try_but_this_is_a_decoy} -->
</body>
</html>"""


class RegisterRequest(BaseModel):
    account: str
    password: str
    website: str | None = None  # honeypot：正常前端不會送這個欄位

class LoginRequest(BaseModel):
    account: str
    password: str


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, request: Request, db: SqlApiClient = Depends(get_db)):
    ip = get_client_ip(request)
    blacklisted = await db.query("SELECT 1 FROM blacklisted_ips WHERE ip = ?", [ip])
    if blacklisted["rows"]:
        return HTMLResponse(_DECOY_HTML)

    # honeypot：正常前端不會送 website 欄位，有值代表是自動填表的 bot
    if body.website:
        await db.query(
            "INSERT INTO blacklisted_ips (ip, reason) VALUES (?, 'honeypot')"
            " ON DUPLICATE KEY UPDATE reason = reason",
            [ip],
        )
        return HTMLResponse(_DECOY_HTML)

    user_agent = request.headers.get("user-agent", "").strip().lower()
    if not user_agent or user_agent.startswith(_BLOCKED_USER_AGENT_PREFIXES):
        raise HTTPException(status_code=400, detail="請求格式錯誤")

    # 0. 帳號/密碼基本格式檢查
    if not body.account.strip() or not body.password:
        raise HTTPException(status_code=400, detail="帳號與密碼不可為空")
    if len(body.account) > 50 or len(body.password) > 72:
        raise HTTPException(status_code=400, detail="帳號或密碼長度超過限制")

    # 1. 檢查 account 是否已存在
    rows = await db.query(
        "SELECT user_id FROM users WHERE account = ?",
        [body.account],
    )
    if rows['ok'] and rows['rows']:
        raise HTTPException(status_code=409, detail="帳號已存在")

    # 2. Hash 密碼（丟到 thread pool，避免卡住 event loop），INSERT
    global _hash_pending
    async with _hash_pending_lock:
        if _hash_pending >= HASH_QUEUE_MAX:
            raise HTTPException(status_code=429, detail="目前註冊請求過多，請稍後再試")
        _hash_pending += 1
    try:
        loop = asyncio.get_running_loop()
        hashed = await loop.run_in_executor(_hash_executor, pwd_context.hash, body.password)
    finally:
        async with _hash_pending_lock:
            _hash_pending -= 1

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
        # SESSION_TTL_SECONDS 為內部常數（非使用者輸入），直接嵌入 SQL 是安全的；
        # INTERVAL 子句不支援以 ? 佔位符傳入數值。以秒為單位避免 INTERVAL 截斷小數小時。
        f"UPDATE users SET session_id = ?, session_expires_at = NOW() + INTERVAL {SESSION_TTL_SECONDS} SECOND,"
        " session_ip = ? WHERE user_id = ?",
        [session_id, get_client_ip(request), int(user["user_id"])],
    )

    return {"session_id": session_id}


@router.get("/me")
async def me(user: dict = Depends(verify_session)):
    # 用途：前端定期 ping 以偵測 session 是否仍有效。
    # 刻意使用 verify_session（不續期）：若此輪詢端點也續期，session 會因前端定期 ping
    # 而永不過期，使「長時間未操作」永遠偵測不到。續期只由使用者實際操作的端點負責。
    return {"user_id": user["user_id"], "account": user["account"]}


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
