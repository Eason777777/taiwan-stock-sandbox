from typing import Annotated, AsyncGenerator
from fastapi import Depends, Header, HTTPException
import httpx

from .database import SqlApiClient, SQL_API_URL


async def get_db() -> AsyncGenerator[SqlApiClient, None]:
    async with httpx.AsyncClient() as client:
        yield SqlApiClient(client)


async def get_current_user(
    x_session_id: Annotated[str, Header()],
    db: SqlApiClient = Depends(get_db),
):
    rows = await db.query(f"""
        SELECT user_id, account FROM users
        WHERE session_id = '{x_session_id}'
    """)
    print("rows: ",rows)
    if not rows:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return rows['rows'][0]   # {"user_id": ..., "account": ...}

