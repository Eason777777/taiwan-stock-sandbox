import os
import httpx

SQL_API_URL = os.getenv("SQL_API_URL", "http://sql-api.shiragaserver.lan/query")


class SqlApiClient:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def query(self, sql: str, params: list | None = None) -> list[dict]:
        payload = {"sql": sql}
        if params is not None:
            payload["params"] = params
        r = await self._client.post(SQL_API_URL, json=payload)
        r.raise_for_status()
        return r.json()
