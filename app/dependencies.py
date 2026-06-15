from typing import Annotated, AsyncGenerator
from fastapi import Depends, Header, HTTPException, Request
import httpx

from .database import SqlApiClient
from .constants import SESSION_TTL_SECONDS


async def get_db() -> AsyncGenerator[SqlApiClient, None]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield SqlApiClient(client)


def get_client_ip(request: Request) -> str:
    # 優先採用 X-Forwarded-For 第一個位址（反向代理場景），否則用連線本身的位址
    # 截斷至 45 字元（IPv6 文字表示法最大長度），避免偽造過長的 header
    # 在寫入 users.session_ip（VARCHAR(45)）時造成 DB 錯誤
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else ""
    return ip[:45]


def _normalize_ip(ip: str) -> str:
    # 將 IPv6 表示的 loopback／IPv4-mapped 位址正規化為對應的 IPv4 字串，
    # 避免同一台機器因連線走 IPv4 或 IPv6（例如 "::1" vs "127.0.0.1"）
    # 而被 _ip_subnet 判定為不同網段，導致合法 session 被誤擋。
    if ip == "::1":
        return "127.0.0.1"
    if ip.startswith("::ffff:"):
        return ip[len("::ffff:"):]
    return ip


def _ip_subnet(ip: str) -> str:
    # IPv4 只比對前三段（/24），容忍同網段內 DHCP 換 IP；
    # 非 IPv4（IPv6 或無法解析）則整串比對
    parts = _normalize_ip(ip).split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        return ".".join(parts[:3])
    return ip


async def verify_session(
    request: Request,
    x_session_id: Annotated[str, Header()],
    db: SqlApiClient = Depends(get_db),
):
    # 只驗證 session 是否有效，**不**滑動續期。供 /auth/me 等「閒置偵測」端點使用：
    # 若這類輪詢端點也續期，會讓 session 因前端定期 ping 而永不過期，
    # 使「長時間未操作」永遠不會被偵測到。真正的續期只由使用者實際操作的端點觸發。
    #
    # 過期判斷交給 DB 端的 NOW()（由 SQL 直接算出 is_expired 旗標），
    # 避免把 session_expires_at 拉回 Python 比較而受應用伺服器與 DB 時區不一致影響。
    # 不在 WHERE 過濾過期，是為了能區分「session 過期」與「不存在/錯誤」並回不同的 401。
    result = await db.query(
        "SELECT user_id, account, session_ip, is_new,"
        " (session_expires_at IS NOT NULL AND session_expires_at <= NOW()) AS is_expired"
        " FROM users WHERE session_id = ?",
        [x_session_id],
    )
    if not result["rows"]:
        # session_id 缺失或不存在：一般未登入
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = result["rows"][0]

    # session 已過期（閒置過久）：回可辨識標記，供前端顯示「長時間未操作，請重新登入」。
    # SQL API 對布林旗標可能回傳 1/0 或 True/False，一律以 truthy 判斷。
    if user["is_expired"]:
        raise HTTPException(status_code=401, detail="session_expired")

    # session 綁定來源 IP（放寬至 /24 網段，容忍 DHCP 換 IP）：
    # 若請求來源網段與登入時記錄的不同，拒絕該次請求
    # （session 本身仍有效，原本的網段不受影響）
    if user["session_ip"] is not None and _ip_subnet(user["session_ip"]) != _ip_subnet(get_client_ip(request)):
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user



async def get_current_user(
    db: SqlApiClient = Depends(get_db),
    user: dict = Depends(verify_session),
):
    # 在 verify_session 通過後滑動續期。所有「使用者實際操作」的端點都用這個依賴，
    # 因此只要使用者持續操作，session 就會被延長；一旦閒置超過 TTL 即過期。
    #
    # 滑動過期：把過期時間延長至 NOW() + SESSION_TTL_SECONDS 秒。
    # SESSION_TTL_SECONDS 為內部常數（非使用者輸入），直接嵌入 SQL 是安全的；
    # INTERVAL 子句不支援以 ? 佔位符傳入數值。以秒為單位避免 INTERVAL 截斷小數小時。
    await db.query(
        f"UPDATE users SET session_expires_at = NOW() + INTERVAL {SESSION_TTL_SECONDS} SECOND"
        " WHERE user_id = ?",
        [int(user["user_id"])],
    )

    return {"user_id": user["user_id"], "account": user["account"]}
