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
        if r.status_code >= 400:
            # 不附帶 params：可能包含密碼雜湊等敏感資料，避免外洩至例外訊息／日誌
            raise RuntimeError(f"sql-api error {r.status_code} for {sql!r}: {r.text}")
        return r.json()
