from typing import Annotated, AsyncGenerator
from fastapi import Depends, Header, HTTPException, Request
import httpx

from .database import SqlApiClient


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


async def get_current_user(
    request: Request,
    x_session_id: Annotated[str, Header()],
    db: SqlApiClient = Depends(get_db),
):
    # 過期判斷交給 DB 端的 NOW()，避免應用伺服器與 DB 時區不一致
    result = await db.query(
        "SELECT user_id, account, session_ip FROM users WHERE session_id = ?"
        " AND (session_expires_at IS NULL OR session_expires_at > NOW())",
        [x_session_id],
    )
    if not result["rows"]:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = result["rows"][0]

    # session 綁定來源 IP（放寬至 /24 網段，容忍 DHCP 換 IP）：
    # 若請求來源網段與登入時記錄的不同，拒絕該次請求
    # （session 本身仍有效，原本的網段不受影響）
    if user["session_ip"] is not None and _ip_subnet(user["session_ip"]) != _ip_subnet(get_client_ip(request)):
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {"user_id": user["user_id"], "account": user["account"]}
