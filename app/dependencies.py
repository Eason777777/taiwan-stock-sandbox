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
    # TODO: SELECT user_id, account FROM User WHERE session_id = ?
    raise HTTPException(status_code=401, detail="Not authenticated")
