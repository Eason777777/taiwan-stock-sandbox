import os
import httpx

SQL_API_URL = os.getenv("SQL_API_URL", "http://sql-api.shiragaserver.lan/query")
# 本機備案 sql-api（docker compose，見 ../sql-api）：主要 sql-api 連線層失敗時的 fallback
FALLBACK_SQL_API_URL = os.getenv("FALLBACK_SQL_API_URL", "http://localhost:3000/query")


class SqlApiClient:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def query(self, sql: str, params: list | None = None) -> list[dict]:
        payload = {"sql": sql}
        if params is not None:
            payload["params"] = params

        try:
            r = await self._client.post(SQL_API_URL, json=payload)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            # 主要 sql-api 連不上（伺服器掛掉）：改打本機備案
            r = await self._client.post(FALLBACK_SQL_API_URL, json=payload)

        if r.status_code >= 400:
            # 不附帶 params：可能包含密碼雜湊等敏感資料，避免外洩至例外訊息／日誌
            raise RuntimeError(f"sql-api error {r.status_code} for {sql!r}: {r.text}")
        return r.json()
