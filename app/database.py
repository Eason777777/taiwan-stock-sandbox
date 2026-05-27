import os
import httpx

SQL_API_URL = os.getenv("SQL_API_URL", "http://sql-api.shiragaserver.lan/query")


def sql_str(value: str) -> str:
    # 同時逸出反斜線（必須先做，否則會重複逸出）
    value = value.replace("\\", "\\\\")
    value = value.replace("'", "''")
    value = value.replace("\x00", "")   # 刪除 null byte
    return value


class SqlApiClient:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def query(self, sql: str) -> list[dict]:
        r = await self._client.post(SQL_API_URL, json={"sql": sql})
        r.raise_for_status()
        return r.json()
