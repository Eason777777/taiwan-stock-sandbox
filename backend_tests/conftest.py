"""共用設定、常數與 fixture，供 test_smoke.py / test_security.py 使用。"""

import random
import string

import httpx
import pytest

BASE_URL = "http://localhost:8000"
SQL_API_URL = "http://sql-api.shiragaserver.lan/query"
# 本機備案 sql-api（docker compose，見 ../sql-api）：與 app/database.py 的 FALLBACK_SQL_API_URL 一致，
# 確保 db_query 與 app 連的是同一份 DB
FALLBACK_SQL_API_URL = "http://localhost:3000/query"
_resolved_sql_api_url = None

STOCK_ID = "2330"
START_DATE = "2023-01-04"  # 2023-01-03 也有資料，可當「前一交易日」
MAX_ACTIVE_SAVES_LIMIT = 5
HASH_QUEUE_MAX = 10  # 對應 app/routers/auth.py 的 HASH_QUEUE_MAX

PHASE_SEQUENCE = ["PRE_MARKET", "INTRADAY", "POST_MARKET", "CLOSED"]


def db_query(sql, params=None):
    global _resolved_sql_api_url
    if _resolved_sql_api_url is None:
        try:
            httpx.post(SQL_API_URL, json={"sql": "SELECT 1"}, timeout=3)
            _resolved_sql_api_url = SQL_API_URL
        except (httpx.ConnectError, httpx.ConnectTimeout):
            _resolved_sql_api_url = FALLBACK_SQL_API_URL

    r = httpx.post(_resolved_sql_api_url, json={"sql": sql, "params": params or []}, timeout=10)
    r.raise_for_status()
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(f"sql-api error: {body}")
    return body["rows"]


def _tick_size(price):
    """依台股升降單位規則，回傳該價位適用的最小跳動單位。"""
    if price < 10:
        return 0.01
    if price < 50:
        return 0.05
    if price < 100:
        return 0.1
    if price < 500:
        return 0.5
    if price < 1000:
        return 1.0
    return 5.0


def _round_to_tick(price):
    tick = _tick_size(price)
    return round(round(price / tick) * tick, 2)


def get_order_price(stock_id, trade_date):
    rows = db_query(
        "SELECT ref_price FROM daily_prices WHERE stock_id=? AND trade_date=?",
        [stock_id, trade_date],
    )
    ref = float(rows[0]["ref_price"]) if rows else 100.0
    return _round_to_tick(ref)


def register_and_login(client, account, password):
    client.post("/auth/register", json={"account": account, "password": password})
    r = client.post("/auth/login", json={"account": account, "password": password})
    if r.status_code != 200:
        return None
    return r.json().get("session_id")


def random_suffix(k=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=k))


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="session", autouse=True)
def _server_health_check(client):
    """所有測試開始前先確認 server 是否可連線；連不上就讓整個 session fail fast。"""
    try:
        r = client.get("/")
    except httpx.ConnectError as e:
        pytest.exit(f"無法連線到 {BASE_URL}，請先啟動 uvicorn app.main:app --reload ({e})", returncode=1)
    assert r.status_code == 200, f"health check failed: {r.status_code}: {r.text}"
