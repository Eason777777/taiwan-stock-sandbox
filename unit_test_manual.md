# 後端單元測試手冊 (unit_test_manual)

本手冊說明如何為本次新實作的四個 FastAPI router 進行**單元測試**：

- `app/routers/stocks.py` — 股票查詢 / 個股詳情 / 歷史報價
- `app/routers/orders.py` — 委託單列表 / 下單（含防呆驗證）/ 撤單
- `app/routers/holdings.py` — 持股（含未實現損益）/ 成交紀錄
- `app/routers/watchlist.py` — 自選股列表 / 新增 / 移除

> **本手冊只教「怎麼測」，不會替你執行測試。** 照著步驟做即可在**完全不需要 Tailscale、不需要連線真實資料庫**的情況下驗證後端邏輯。

---

## 1. 測試策略

這四個 router 全部透過 `app/database.py` 的 `SqlApiClient` 與資料庫溝通，而 `SqlApiClient` 是經由 FastAPI 依賴注入（`get_db`）取得的。同時所有路由都受 `get_current_user`（`X-Session-Id` 驗證）保護。

因此單元測試的核心手法是 **FastAPI Dependency Override**：

1. 用一個「假的 DB」物件覆寫 `get_db` —— 它不發送任何 HTTP 請求，只回傳我們預先準備好的假資料，並把收到的 SQL 記錄下來。
2. 覆寫 `get_current_user`，直接回傳一個假的登入使用者，跳過 `X-Session-Id` 查詢。
3. 用 `fastapi.testclient.TestClient` 對 API 發出請求，斷言回傳的 HTTP 狀態碼、JSON 內容，以及（必要時）假 DB 收到的 SQL。

這樣的測試屬於專案慣例中的 `tests/unit/`（純邏輯、無外部依賴），與既有的 Foundry 單元測試放在同一層級。

> **重點**：`SqlApiClient.query()` 回傳的是 `{"ok": bool, "rows": [...]}` 字典，router 內部一律取 `result['rows']`。你的假 DB 必須回傳**同樣形狀**的字典，否則會 `KeyError`。

---

## 2. 環境準備

### 2.1 安裝測試相依套件

`requirements.txt` 目前**沒有**列入 `pytest`。請額外安裝：

```sh
pip install -r requirements.txt
pip install pytest
```

`fastapi` 內建 `TestClient`（底層用 `httpx`，已在 requirements 內），不需要額外安裝測試用 HTTP client。

> 若 import `app.main` 時出現 `passlib`/`bcrypt` 相關錯誤，補裝 `pip install "passlib[bcrypt]"`。這只是因為 `app/main.py` 會連帶載入 `auth.py`；本手冊的測試本身不碰 auth。

### 2.2 測試檔案放置位置

依專案慣例放在 `tests/unit/`：

```
tests/
└── unit/
    ├── conftest.py            # 共用 fixture（假 DB、TestClient）
    ├── test_stocks.py
    ├── test_orders.py
    ├── test_holdings.py
    └── test_watchlist.py
```

---

## 3. 共用測試骨架 `tests/unit/conftest.py`

下面這個 `conftest.py` 提供一個 **可程式化的假 DB** 與一個 **已覆寫依賴的 TestClient**。把它複製進去即可。

```python
# tests/unit/conftest.py
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_db, get_current_user


class FakeDB:
    """
    模擬 app.database.SqlApiClient。

    - query() 不發任何 HTTP 請求。
    - 依「呼叫順序」回傳預先排好的結果（responses）。
    - 把每一次的 (sql, params) 記錄到 self.calls，方便斷言。

    每個結果都必須是 SqlApiClient 真正回傳的形狀：{"ok": True, "rows": [...]}。
    """

    def __init__(self, responses=None):
        # responses: list[dict]，依序對應每一次 query() 呼叫
        self._responses = list(responses or [])
        self.calls = []  # list[tuple[str, list]]

    async def query(self, sql, params=None):
        self.calls.append((sql, params or []))
        if self._responses:
            return self._responses.pop(0)
        # 預設：成功但沒有任何 row
        return {"ok": True, "rows": []}


def rows(*items):
    """方便建立 {"ok": True, "rows": [...]} 的小工具。"""
    return {"ok": True, "rows": list(items)}


@pytest.fixture
def fake_user():
    return {"user_id": 1, "account": "tester"}


@pytest.fixture
def make_client(fake_user):
    """
    回傳一個工廠函式：傳入「依序的 DB 回應」清單，得到 (client, db)。

    用法：
        client, db = make_client([rows({...}), rows()])
    """
    def _make(responses=None):
        db = FakeDB(responses)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: fake_user
        client = TestClient(app)
        return client, db

    yield _make
    # 測試結束後清掉覆寫，避免污染其他測試
    app.dependency_overrides.clear()
```

> **為什麼用「依序回應」而不是真的解析 SQL？**
> 單元測試只驗證 router 的**控制流程**（驗證了哪些東西、依什麼順序打 DB、回傳什麼），不驗證 SQL 在 MySQL 上的真實行為。後者屬於整合測試（見第 8 節）。你只要照著 router 原始碼裡 `await db.query(...)` 出現的**順序**，準備對應的假回應即可。

---

## 4. `test_stocks.py` 範例

`stocks.py` 三個端點的 `db.query` 呼叫順序：

| 端點 | query 順序 |
| --- | --- |
| `GET /stocks/` | 1. SELECT 股票清單 |
| `GET /stocks/{id}` | 1. SELECT 該股票 |
| `GET /stocks/{id}/prices` | 1. 確認股票存在 → 2. SELECT 報價 |

```python
# tests/unit/test_stocks.py
from .conftest import rows


def test_search_stocks_with_query(make_client):
    client, db = make_client([
        rows({"stock_id": "2330", "stock_name_zh": "台積電",
              "stock_full_name_zh": "台灣積體電路製造",
              "market_type": "上市", "sector_name": "半導體業",
              "listing_date": "1994-09-05"}),
    ])
    resp = client.get("/stocks/", params={"q": "2330"})
    assert resp.status_code == 200
    assert resp.json()[0]["stock_id"] == "2330"
    # 帶 q 時應走 LIKE，並帶兩個 %2330% 參數
    sql, params = db.calls[0]
    assert "LIKE" in sql
    assert params[:2] == ["%2330%", "%2330%"]


def test_get_stock_found(make_client):
    client, db = make_client([rows({"stock_id": "2330", "stock_name_zh": "台積電"})])
    resp = client.get("/stocks/2330")
    assert resp.status_code == 200
    assert resp.json()["stock_id"] == "2330"


def test_get_stock_not_found_returns_404(make_client):
    client, db = make_client([rows()])  # 空 rows
    resp = client.get("/stocks/9999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "股票不存在"


def test_price_history_unknown_stock_returns_404(make_client):
    client, db = make_client([rows()])  # 第一個 query（確認股票存在）回傳空
    resp = client.get("/stocks/9999/prices")
    assert resp.status_code == 404


def test_price_history_date_filters(make_client):
    client, db = make_client([
        rows({"stock_id": "2330"}),            # 股票存在
        rows({"trade_date": "2023-01-03"}),    # 報價
    ])
    resp = client.get("/stocks/2330/prices",
                      params={"from_date": "2023-01-01", "to_date": "2023-01-31"})
    assert resp.status_code == 200
    sql, params = db.calls[1]
    assert "trade_date >= ?" in sql and "trade_date <= ?" in sql
    assert "2023-01-01" in params and "2023-01-31" in params
```

---

## 5. `test_orders.py` 範例（最重要，防呆最多）

`place_order` 是測試重點。它的 `db.query` 呼叫順序為：

1. `SELECT * FROM SaveFile`（取存檔、驗證擁有者）
2. `SELECT ... FROM Stock`（股票存在 + listing_date）
3. `SELECT ... FROM DailyPrice`（當日報價 + limit_up/limit_down）
4. （賣單才有）`SELECT quantity FROM Holding` → `SELECT SUM(quantity) ... 待成交`
5. `INSERT INTO StockOrder`
6. `SELECT LAST_INSERT_ID()`
7. `SELECT * FROM StockOrder`（回傳新單）

驗證若在中途失敗，後面的 query 就不會發生 —— 這也是好斷言的點（`len(db.calls)`）。

```python
# tests/unit/test_orders.py
from .conftest import rows

SAVE_ACTIVE_PRE = {
    "save_id": 10, "user_id": 1, "status": "進行中",
    "current_phase": "盤前", "current_date": "2023-01-03",
    "savings_balance": 1_000_000, "trading_balance": 1_000_000,
}


def test_place_limit_buy_success(make_client):
    client, db = make_client([
        rows(SAVE_ACTIVE_PRE),                                   # SaveFile
        rows({"stock_id": "2330", "listing_date": "1994-09-05"}),# Stock
        rows({"low": 500, "high": 510,
              "limit_up": 560, "limit_down": 460}),              # DailyPrice
        rows(),                                                  # INSERT StockOrder
        rows({"order_id": 99}),                                  # LAST_INSERT_ID
        rows({"order_id": 99, "status": "待成交", "side": "買"}), # 回傳新單
    ])
    resp = client.post("/saves/10/orders", json={
        "stock_id": "2330", "order_type": "限價", "side": "買",
        "price": 505, "quantity": 1,
    })
    assert resp.status_code == 201
    assert resp.json()["order_id"] == 99
    # 確認真的有 INSERT StockOrder，且狀態為待成交
    insert_sql = db.calls[3][0]
    assert "INSERT INTO StockOrder" in insert_sql and "待成交" in insert_sql


def test_place_order_in_postmarket_phase_rejected(make_client):
    save = {**SAVE_ACTIVE_PRE, "current_phase": "盤後"}
    client, db = make_client([rows(save)])
    resp = client.post("/saves/10/orders", json={
        "stock_id": "2330", "order_type": "市價", "side": "買", "quantity": 1,
    })
    assert resp.status_code == 400
    assert "盤後" in resp.json()["detail"]
    assert len(db.calls) == 1  # 連 Stock 都還沒查就被擋下


def test_limit_order_without_price_is_422(make_client):
    client, db = make_client([rows(SAVE_ACTIVE_PRE)])
    resp = client.post("/saves/10/orders", json={
        "stock_id": "2330", "order_type": "限價", "side": "買", "quantity": 1,
    })
    assert resp.status_code == 422


def test_price_outside_limit_band_rejected(make_client):
    client, db = make_client([
        rows(SAVE_ACTIVE_PRE),
        rows({"stock_id": "2330", "listing_date": "1994-09-05"}),
        rows({"low": 500, "high": 510, "limit_up": 560, "limit_down": 460}),
    ])
    resp = client.post("/saves/10/orders", json={
        "stock_id": "2330", "order_type": "限價", "side": "買",
        "price": 999, "quantity": 1,   # 超過漲停 560
    })
    assert resp.status_code == 400
    assert "漲停" in resp.json()["detail"] or "跌停" in resp.json()["detail"]


def test_stock_not_yet_listed_rejected(make_client):
    client, db = make_client([
        rows(SAVE_ACTIVE_PRE),
        rows({"stock_id": "9999", "listing_date": "2099-01-01"}),  # 未來才上市
    ])
    resp = client.post("/saves/10/orders", json={
        "stock_id": "9999", "order_type": "市價", "side": "買", "quantity": 1,
    })
    assert resp.status_code == 400
    assert "尚未上市" in resp.json()["detail"]


def test_buy_insufficient_trading_balance(make_client):
    poor = {**SAVE_ACTIVE_PRE, "trading_balance": 100}
    client, db = make_client([
        rows(poor),
        rows({"stock_id": "2330", "listing_date": "1994-09-05"}),
        rows({"low": 500, "high": 510, "limit_up": 560, "limit_down": 460}),
    ])
    resp = client.post("/saves/10/orders", json={
        "stock_id": "2330", "order_type": "限價", "side": "買",
        "price": 505, "quantity": 1,
    })
    assert resp.status_code == 400
    assert "餘額不足" in resp.json()["detail"]


def test_sell_insufficient_holding(make_client):
    client, db = make_client([
        rows(SAVE_ACTIVE_PRE),
        rows({"stock_id": "2330", "listing_date": "1994-09-05"}),
        rows({"low": 500, "high": 510, "limit_up": 560, "limit_down": 460}),
        rows(),                              # Holding：沒有持股
        rows({"committed": 0}),              # 待成交賣單張數
    ])
    resp = client.post("/saves/10/orders", json={
        "stock_id": "2330", "order_type": "限價", "side": "賣",
        "price": 505, "quantity": 1,
    })
    assert resp.status_code == 400
    assert "持股不足" in resp.json()["detail"]


def test_other_users_save_returns_403(make_client):
    foreign = {**SAVE_ACTIVE_PRE, "user_id": 999}
    client, db = make_client([rows(foreign)])
    resp = client.post("/saves/10/orders", json={
        "stock_id": "2330", "order_type": "市價", "side": "買", "quantity": 1,
    })
    assert resp.status_code == 403


def test_cancel_pending_order(make_client):
    client, db = make_client([
        rows(SAVE_ACTIVE_PRE),                       # SaveFile
        rows({"order_id": 99, "status": "待成交"}),   # 查委託單
        rows(),                                      # UPDATE 已撤銷
    ])
    resp = client.delete("/saves/10/orders/99")
    assert resp.status_code == 204
    assert "已撤銷" in db.calls[2][0]


def test_cancel_already_filled_order_rejected(make_client):
    client, db = make_client([
        rows(SAVE_ACTIVE_PRE),
        rows({"order_id": 99, "status": "已成交"}),
    ])
    resp = client.delete("/saves/10/orders/99")
    assert resp.status_code == 400
```

---

## 6. `test_holdings.py` 範例

`list_holdings` 的 query 順序：1. SaveFile → 2. Holding JOIN Stock LEFT JOIN DailyPrice。
重點在驗證未實現損益的計算（`quantity` 以「張」計，1 張 = 1000 股）。

```python
# tests/unit/test_holdings.py
from .conftest import rows

SAVE = {"save_id": 10, "user_id": 1, "current_date": "2023-01-10"}


def test_holdings_unrealized_pnl(make_client):
    client, db = make_client([
        rows(SAVE),
        rows({"stock_id": "2330", "stock_name_zh": "台積電",
              "quantity": 2, "avg_cost": 500.0, "market_price": 510.0}),
    ])
    resp = client.get("/saves/10/holdings")
    assert resp.status_code == 200
    h = resp.json()[0]
    # cost = 500 * 2 * 1000 = 1,000,000；market = 510 * 2 * 1000 = 1,020,000
    assert h["cost_value"] == 1_000_000
    assert h["market_value"] == 1_020_000
    assert h["unrealized_pnl"] == 20_000
    assert h["unrealized_pnl_pct"] == 2.0


def test_holdings_no_price_today_returns_null_pnl(make_client):
    client, db = make_client([
        rows(SAVE),
        rows({"stock_id": "2330", "stock_name_zh": "台積電",
              "quantity": 1, "avg_cost": 500.0, "market_price": None}),
    ])
    resp = client.get("/saves/10/holdings")
    h = resp.json()[0]
    assert h["market_price"] is None
    assert h["unrealized_pnl"] is None


def test_transactions_listing(make_client):
    client, db = make_client([
        rows(SAVE),
        rows({"transaction_id": 1, "order_id": 5, "stock_id": "2330",
              "exec_price": 500.0, "quantity": 1, "fee": 712, "tax": 0}),
    ])
    resp = client.get("/saves/10/holdings/transactions")
    assert resp.status_code == 200
    assert resp.json()[0]["transaction_id"] == 1
```

---

## 7. `test_watchlist.py` 範例

```python
# tests/unit/test_watchlist.py
from .conftest import rows

SAVE = {"save_id": 10, "user_id": 1}


def test_get_watchlist(make_client):
    client, db = make_client([
        rows(SAVE),
        rows({"stock_id": "2330", "stock_name_zh": "台積電",
              "market_type": "上市", "sector_name": "半導體業"}),
    ])
    resp = client.get("/saves/10/watchlist")
    assert resp.status_code == 200
    assert resp.json()[0]["stock_id"] == "2330"


def test_add_to_watchlist(make_client):
    client, db = make_client([
        rows(SAVE),
        rows({"stock_id": "2330"}),  # 股票存在
        rows(),                      # INSERT IGNORE
    ])
    resp = client.post("/saves/10/watchlist", json={"stock_id": "2330"})
    assert resp.status_code == 201
    assert "INSERT IGNORE INTO Watchlist" in db.calls[2][0]


def test_add_unknown_stock_404(make_client):
    client, db = make_client([
        rows(SAVE),
        rows(),  # 股票不存在
    ])
    resp = client.post("/saves/10/watchlist", json={"stock_id": "0000"})
    assert resp.status_code == 404


def test_remove_from_watchlist(make_client):
    client, db = make_client([
        rows(SAVE),
        rows(),  # DELETE
    ])
    resp = client.delete("/saves/10/watchlist/2330")
    assert resp.status_code == 204
    assert "DELETE FROM Watchlist" in db.calls[1][0]
```

---

## 8. 如何執行（指令參考）

> 你問的是「怎麼測」，以下是實際要敲的指令；本手冊本身不替你執行。

```sh
# 跑全部單元測試
pytest tests/unit/

# 只跑某一個檔案
pytest tests/unit/test_orders.py

# 只跑單一個案
pytest tests/unit/test_orders.py::test_place_limit_buy_success

# 顯示詳細輸出
pytest tests/unit/ -v
```

這些單元測試**不需要 Tailscale、不需要連 MySQL**，因為 DB 已被 `FakeDB` 覆寫。

---

## 9. 邊界與整合測試（選做）

單元測試只證明「router 的判斷與分支正確」。要驗證 SQL 在真實 MySQL 上能跑、欄位名稱正確、撮合與帳務一致，需要**整合測試**（`tests/integration/`，需 Tailscale + 真實 DB）。建議至少手動跑一次端到端流程：

1. `uvicorn app.main:app --reload`，開 `http://localhost:8000/docs`。
2. `/auth/register` → `/auth/login` 取得 `session_id`，之後每個請求帶 `X-Session-Id` header。
3. `POST /saves/` 建立存檔（拿到 `save_id`、`current_date`）。
4. `GET /stocks/?q=2330`、`GET /stocks/2330/prices` 確認查得到資料。
5. 在「盤前/盤中」`POST /saves/{id}/orders` 下一張限價買單。
6. `POST /saves/{id}/advance` 推進到「盤後」再推進一次 → 撮合執行。
7. `GET /saves/{id}/holdings` 看持股與未實現損益、`GET /saves/{id}/holdings/transactions` 看成交、`GET /saves/{id}/orders` 看委託狀態變為「已成交/已失效」。
8. `POST /saves/{id}/watchlist`、`GET`、`DELETE` 驗證自選股 CRUD。

### 需要特別注意的已知前提（測試時容易踩雷）

- **回傳形狀**：`SqlApiClient.query()` 回 `{"ok", "rows"}`，所有 router 取 `['rows']`。假 DB 一定要照這個形狀。
- **資料表命名不一致**：這些 router 走 PascalCase（`Stock`、`DailyPrice`、`StockOrder`…），而匯入工具寫的是 `project_main.` 的小寫複數表。整合測試前請先確認你連到的 DB 裡，PascalCase 的表確實存在且有資料。
- **撮合不在 `orders.py`**：下單只負責建立「待成交」委託；真正成交/扣款發生在 `saves.py` 的 `advance_phase`（推進離開「盤後」時）。所以單元測試 `orders.py` 不會看到餘額變動，那是 advance 的職責。
- **狀態字串**：本實作用中文狀態（委託 `待成交`/`已成交`/`已撤銷`/`已失效`；存檔 `進行中`/`已結束`），與 V1 規格的英文 ENUM 不同。斷言時請用中文。
```
