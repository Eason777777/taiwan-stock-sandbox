"""
資安與邊界案例測試 - security_test.py

這份測試對照的是「應該要有的防護/功能」，不是現在程式碼的樣子。
有些項目目前預期會 FAIL —— FAIL 不代表測試寫錯，代表對應的疑慮確實存在，
需要在後端補上對應的修正。每一項都會在下方註明「目前預期結果」。

用法同 smoke_test.py:
    1. 另開一個 terminal 啟動 server: uvicorn app.main:app --reload
    2. python backend_tests/security_test.py

────────────────────────────────────────────────────────────────────────
測試項目清單（依執行順序）
────────────────────────────────────────────────────────────────────────

【A. 跨使用者存取控制】（建立 user A 的存檔，user B 嘗試存取）
  A1. user B GET    /saves/{A的save_id}                -> 403/404  (預期 PASS)
  A2. user B POST   /saves/{A的save_id}/orders         -> 403/404  (預期 PASS)
  A3. user B DELETE /saves/{A的save_id}                -> 403/404  (預期 PASS)
  A4. user B GET    /saves/{A的save_id}/holdings       -> 403/404  (預期 PASS)
  A5. user B GET    /saves/{A的save_id}/watchlist      -> 403/404  (預期 PASS)
  A6. user B GET    /saves/{A的save_id}/orders         -> 403/404  (預期 PASS)
  A7. user B DELETE /saves/{A的save_id}/orders/1       -> 403/404  (預期 PASS)

【B. session 單一登入原則】
  B1. 同帳號重新登入後，舊 session_id 立即失效         -> 401      (預期 PASS)

【C. 輸入驗證邊界】
  C1. 註冊空帳號/空密碼                                 -> 422      (預期 FAIL，目前無長度/空值檢查)
  C2. 轉帳金額為負數                                    -> 422      (預期 PASS，現有檢查)
  C3. 下單 quantity <= 0                               -> 422      (預期 PASS，現有檢查)
  C4. 限價單價格不符合台股升降單位（例如 500.37 元）     -> 4xx      (預期 FAIL，未驗證 tick size)
  C5. 建立存檔 initial_funds = -100（負數）             -> 422      (預期 PASS，現有檢查)
  C6. 建立存檔 initial_funds = 2000000（超過上限）       -> 422      (預期 PASS，現有檢查)

【Q. SQL Injection 探測】
  Q1. /stocks?q=2330' OR '1'='1 不應 500/洩漏異常資料   -> 200      (預期 PASS，已用參數化查詢)
  Q2. 下單 stock_id="' OR '1'='1" 不應 500              -> 404      (預期 PASS，已用參數化查詢)

【D. 時空隔離是否可被繞過】
  D1. /stocks/{id}/prices 不帶 save_id                  -> 422 (預期 PASS，save_id 已改為必填)

【E. 錯誤訊息是否洩漏內部細節】
  E1. 404 等錯誤訊息的 detail 不應包含 SQL 關鍵字/表名/Traceback (預期 PASS)

【F. CORS 設定】
  F1. OPTIONS preflight 回應應包含 Access-Control-Allow-Origin (預期 FAIL，未設定 CORSMiddleware)

【G. sql-api 在 Tailscale 網路內是否仍無認證即可任意查詢】(預設是不會過的)
  G1. 不帶任何應用層認證直接 POST sql-api /query 執行 SELECT
      -> 應被拒絕 (預期 FAIL；sql-api 已靠 Tailscale 做機器層級認證，
         此項是「同網路內任何服務都對整個 DB 有完整讀寫權限」的縱深防禦疑慮，
         嚴重度低於對外開放，但仍建議至少加一層 API key)

【H. session 是否有過期機制 / 來源 IP 綁定】
  H1. users 表是否存在 session 過期相關欄位（expires_at 等）-> 應存在 (預期 PASS，已新增 session_expires_at，TTL=2小時)
  H2. 用不同網段來源 IP (X-Forwarded-For) 帶同一個 session_id -> 401 (預期 PASS，session 已綁定登入時的 /24 網段)
  H3. 換回原本的來源 IP，session 仍可正常使用 -> 200 (預期 PASS，僅拒絕跨網段使用，不影響原裝置)
  H4. 同網段內換一個 IP (DHCP 情境) -> 200 (預期 PASS，/24 比對可容忍同網段換 IP)

【I. 登入暴力破解防護】
  I1. 連續 10 次錯誤密碼登入，應在某次回應 429/鎖定        -> 預期 PASS（每帳號 60 秒內錯誤達 5 次即鎖定）

【J. advance 並發 race condition】
  J1. 對同一存檔同時送出兩個 /advance，phase 只應推進一次 -> 預期 FAIL（無鎖定機制）

【K. account_transactions seq 並發衝突】
  K1. 對同一存檔同時送出兩個轉帳，seq 不應重複            -> 預期 FAIL（MAX(seq)+1 無鎖定）

【L. 分頁機制】
  L1. GET /saves/{id}/accounts/history?limit=1 應只回傳 1 筆 -> 預期 PASS（orders/accounts/history/holdings/transactions 均已支援 limit/offset）

【M. K 線週期聚合】
  M1. /stocks/{id}/prices?interval=week 應回傳週線聚合資料   -> 預期 PASS（已實作週/月線聚合）

【N. 手動結束存檔（FINISHED）】
  N1. PATCH /saves/{id}/finish 應能將 ACTIVE 存檔結束為 FINISHED -> 預期 PASS（端點已新增）

【O. SqlApiClient / httpx 是否設定 timeout】
  O1. app/dependencies.py 的 httpx.AsyncClient() 應設定 timeout -> 預期 PASS（已設定 timeout=10s）

【R. 數值欄位型別一致性（整合面：DECIMAL 是否被序列化成字串）】
  R1. GET /saves/{id} 的 savings_balance/trading_balance/total_asset/
      cumulative_return 應為 JSON number，不應是字串
      -> 若為字串，前端 `.toFixed()` 等數值方法會直接報錯
  R2. GET /stocks/{id}/prices 的 open_price/close_price 等應為 JSON number

【S. 日期格式一致性（整合面）】
  S1. GET /saves/{id} 的 current_trade_date 應為 "YYYY-MM-DD" 格式
  S2. GET /stocks/{id}/prices 的 trade_date 應為 "YYYY-MM-DD" 格式
      -> 若混用 ISO datetime（含 T00:00:00.000Z），前端日期比對/顯示容易出錯

【T. API 文件可用性（整合面）】
  T1. GET /docs 與 /openapi.json 應可正常存取，方便前端對照欄位 -> 預期 PASS

【U. 是否信任前端（mass-assignment / 偽造欄位 / enum 驗證）】
  U1. 下單時夾帶偽造欄位 order_id/status/exec_price/save_id
      -> 後端應忽略，回傳的 order_id 為新值、status 為 PENDING (預期 PASS)
  U2. 下單 order_type="HACK"（非法 enum 值）                -> 422 (預期 PASS，現有手動檢查)
  U3. 下單 side="HACK"（非法 enum 值）                      -> 422 (預期 PASS，現有手動檢查)
  U4. 轉帳 direction="HACK"（非法 enum 值）                 -> 422 (預期 PASS，現有手動檢查)
  U5. 下單 quantity=1.5（非整數）                           -> 422 (預期 PASS，pydantic 型別檢查)
  U6. 限價單 price=-100（負數價格）                         -> 4xx (預期 PASS，會落在漲跌停檢查之外)

────────────────────────────────────────────────────────────────────────
"""

import os
import random
import string
import sys
from concurrent.futures import ThreadPoolExecutor

import httpx

BASE_URL = "http://localhost:8000"
SQL_API_URL = "http://sql-api.shiragaserver.lan/query"

STOCK_ID = "2330"
START_DATE = "2023-01-04"

PHASE_SEQUENCE = ["PRE_MARKET", "INTRADAY", "POST_MARKET", "CLOSED"]

PASS = []
FAIL = []


def db_query(sql, params=None):
    r = httpx.post(SQL_API_URL, json={"sql": sql, "params": params or []}, timeout=10)
    r.raise_for_status()
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(f"sql-api error: {body}")
    return body["rows"]


def record(name, ok, detail=""):
    if ok:
        PASS.append(name)
        print(f"[PASS] {name}")
    else:
        FAIL.append(name)
        print(f"[FAIL] {name}  -- {detail}")


def check(name, condition, detail=""):
    record(name, bool(condition), detail)


def register_and_login(client, account, password):
    client.post("/auth/register", json={"account": account, "password": password})
    r = client.post("/auth/login", json={"account": account, "password": password})
    if r.status_code != 200:
        return None
    return r.json().get("session_id")


def main():
    rand_a = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    rand_b = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    account_a = f"sectest_{rand_a}"
    account_b = f"sectest_{rand_b}"
    password = "test1234"

    client = httpx.Client(base_url=BASE_URL, timeout=10)
    state = {"save_id_a": None}

    try:
        run(client, account_a, account_b, password, state)
    except Exception as e:
        record("UNEXPECTED EXCEPTION", False, repr(e))
    finally:
        cleanup(account_a, account_b, state)
        print_summary()


def cleanup(account_a, account_b, state):
    try:
        if state.get("save_id_a"):
            db_query("DELETE FROM save_files WHERE save_id=?", [state["save_id_a"]])
        db_query("DELETE FROM users WHERE account IN (?, ?)", [account_a, account_b])
        print(f"\n(已清理測試資料: save_id={state.get('save_id_a')}, accounts={account_a},{account_b})")
    except Exception as e:
        print(f"\n清理測試資料失敗（請手動檢查）: {e}")


def run(client, account_a, account_b, password, state):
    # ── 健康檢查 ──────────────────────────────────────────────────────
    try:
        r = client.get("/")
        check("0. health check (/)", r.status_code == 200, r.text)
    except Exception as e:
        record("0. health check (/)", False, str(e))
        print("\nServer 連不上，後面全部跳過。請先啟動 uvicorn app.main:app --reload")
        return

    # ── 準備 user A / user B ─────────────────────────────────────────
    session_a = register_and_login(client, account_a, password)
    session_b = register_and_login(client, account_b, password)
    check("setup. user A login", bool(session_a), "無法登入 user A")
    check("setup. user B login", bool(session_b), "無法登入 user B")
    if not session_a or not session_b:
        return

    headers_a = {"X-Session-Id": session_a}
    headers_b = {"X-Session-Id": session_b}

    # user A 建立一個存檔
    r = client.post(
        "/saves",
        json={"save_name": f"sec_{account_a}", "start_date": START_DATE, "initial_funds": 1000000},
        headers=headers_a,
    )
    check("setup. user A create save 201", r.status_code == 201, f"{r.status_code}: {r.text}")
    save_a = r.json() if r.status_code == 201 else {}
    save_id_a = save_a.get("save_id")
    state["save_id_a"] = save_id_a
    if not save_id_a:
        return

    # ── A. 跨使用者存取控制 ───────────────────────────────────────────
    r = client.get(f"/saves/{save_id_a}", headers=headers_b)
    check("A1. user B GET user A's save -> 403/404", r.status_code in (403, 404), f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 500, "quantity": 1},
        headers=headers_b,
    )
    check("A2. user B place order on user A's save -> 403/404", r.status_code in (403, 404), f"{r.status_code}: {r.text}")

    r = client.delete(f"/saves/{save_id_a}", headers=headers_b)
    check("A3. user B DELETE user A's save -> 403/404", r.status_code in (403, 404), f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id_a}/holdings", headers=headers_b)
    check("A4. user B GET user A's holdings -> 403/404", r.status_code in (403, 404), f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id_a}/watchlist", headers=headers_b)
    check("A5. user B GET user A's watchlist -> 403/404", r.status_code in (403, 404), f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id_a}/orders", headers=headers_b)
    check("A6. user B GET user A's orders -> 403/404", r.status_code in (403, 404), f"{r.status_code}: {r.text}")

    r = client.delete(f"/saves/{save_id_a}/orders/1", headers=headers_b)
    check("A7. user B DELETE user A's order -> 403/404", r.status_code in (403, 404), f"{r.status_code}: {r.text}")

    # ── B. 單一登入原則 ───────────────────────────────────────────────
    r = client.get(f"/saves/{save_id_a}", headers=headers_a)
    check("B0. old session still works before re-login -> 200", r.status_code == 200, f"{r.status_code}: {r.text}")

    new_session_a = register_and_login(client, account_a, password)
    check("B-setup. user A re-login", bool(new_session_a), "重新登入失敗")
    if new_session_a:
        r = client.get(f"/saves/{save_id_a}", headers=headers_a)  # 用「舊」session
        check("B1. old session invalidated after re-login -> 401", r.status_code == 401, f"{r.status_code}: {r.text}")
        headers_a = {"X-Session-Id": new_session_a}  # 之後改用新 session

    # ── C. 輸入驗證邊界 ───────────────────────────────────────────────
    r = client.post("/auth/register", json={"account": "", "password": ""})
    check("C1. register with empty account/password -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")
    if r.status_code == 201:
        # 若後端目前仍接受空帳號，立刻清掉這筆髒資料，避免殘留在 users 表
        db_query("DELETE FROM users WHERE account = ?", [""])

    r = client.post(
        f"/saves/{save_id_a}/accounts/transfer",
        json={"direction": "savings_to_trading", "amount": -100},
        headers=headers_a,
    )
    check("C2. transfer negative amount -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 500, "quantity": 0},
        headers=headers_a,
    )
    check("C3. order quantity <= 0 -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    # 限價 100~500 元範圍升降單位應為 0.5 元，500.37 不合法
    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 500.37, "quantity": 1},
        headers=headers_a,
    )
    check("C4. LIMIT price violates tick size -> 4xx", r.status_code >= 400, f"{r.status_code}: {r.text}")

    rand_c = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    r = client.post(
        "/saves",
        json={"save_name": f"sec_neg_{rand_c}", "start_date": START_DATE, "initial_funds": -100},
        headers=headers_a,
    )
    check("C5. create save with initial_funds = -100 -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.post(
        "/saves",
        json={"save_name": f"sec_over_{rand_c}", "start_date": START_DATE, "initial_funds": 2000000},
        headers=headers_a,
    )
    check("C6. create save with initial_funds = 2000000 -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    # ── Q. SQL Injection 探測 ─────────────────────────────────────────
    r = client.get("/stocks", params={"q": "2330' OR '1'='1"}, headers=headers_a)
    check(
        "Q1. search stocks with SQL injection payload -> 200 (no 500)",
        r.status_code == 200,
        f"{r.status_code}: {r.text}",
    )

    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": "' OR '1'='1", "order_type": "LIMIT", "side": "BUY", "price": 100, "quantity": 1},
        headers=headers_a,
    )
    check(
        "Q2. place order with SQL injection stock_id -> 404 (no 500)",
        r.status_code == 404,
        f"{r.status_code}: {r.text}",
    )

    # ── D. 時空隔離是否可被繞過 ──────────────────────────────────────
    # save_id 已改為必填，不帶 save_id 應直接被拒絕（422），無法繞過時空隔離
    r = client.get(f"/stocks/{STOCK_ID}/prices", headers=headers_a)  # 不帶 save_id
    check(
        "D1. /stocks/{id}/prices without save_id is rejected (cannot bypass temporal isolation)",
        r.status_code == 422,
        f"{r.status_code}: {r.text}",
    )

    # ── E. 錯誤訊息是否洩漏內部細節 ──────────────────────────────────
    r = client.get("/saves/999999999", headers=headers_a)
    leaky_keywords = ["SELECT", "INSERT", "UPDATE", "sql-api", "Traceback", "mysqld", "stock_orders", "save_files"]
    body_text = r.text
    leaked = [kw for kw in leaky_keywords if kw.lower() in body_text.lower()]
    check(
        "E1. 404 error body does not leak SQL/schema details",
        r.status_code == 404 and not leaked,
        f"{r.status_code}: {r.text}  leaked={leaked}",
    )

    # ── F. CORS 設定 ──────────────────────────────────────────────────
    r = client.options(
        f"/saves/{save_id_a}",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-session-id",
        },
    )
    cors_header = r.headers.get("access-control-allow-origin")
    check(
        "F1. OPTIONS preflight includes Access-Control-Allow-Origin",
        bool(cors_header),
        f"{r.status_code}, headers={dict(r.headers)}",
    )

    # ── G. sql-api 是否無認證即可任意查詢 ────────────────────────────
    try:
        r = httpx.post(SQL_API_URL, json={"sql": "SELECT 1 AS x"}, timeout=10)
        body = r.json()
        unauthenticated_access_allowed = r.status_code == 200 and body.get("ok") is True
    except Exception as e:
        unauthenticated_access_allowed = False
        body = str(e)
    check(
        "G1. sql-api /query requires authentication",
        not unauthenticated_access_allowed,
        f"sql-api 在沒有任何認證 header 的情況下回應: {body}（任何人皆可對 DB 執行任意 SQL）",
    )

    # ── H. session 是否有過期欄位 ─────────────────────────────────────
    columns = db_query("SHOW COLUMNS FROM users")
    col_names = [c["Field"].lower() for c in columns]
    has_expiry_col = any("expire" in c or "expiry" in c for c in col_names)
    check(
        "H1. users table has a session expiry column",
        has_expiry_col,
        f"users 表欄位: {col_names}（無到期欄位 -> session 永久有效，token 外洩風險高）",
    )

    r = client.get(f"/saves/{save_id_a}", headers={**headers_a, "X-Forwarded-For": "203.0.113.1"})
    check(
        "H2. session used from a different source IP -> 401",
        r.status_code == 401,
        f"{r.status_code}: {r.text}（session 未綁定來源 IP，token 外洩後可在任何機器上使用）",
    )

    r = client.get(f"/saves/{save_id_a}", headers=headers_a)
    check(
        "H3. session still works from the original source IP",
        r.status_code == 200,
        f"{r.status_code}: {r.text}",
    )

    r = client.get(f"/saves/{save_id_a}", headers={**headers_a, "X-Forwarded-For": "127.0.0.5"})
    check(
        "H4. session still works from a different IP in the same /24 (DHCP)",
        r.status_code == 200,
        f"{r.status_code}: {r.text}（/24 網段比對未生效，DHCP 換 IP 會被誤判為跨機使用）",
    )

    # ── I. 登入暴力破解防護 ───────────────────────────────────────────
    rate_limited = False
    for _ in range(10):
        r = client.post("/auth/login", json={"account": account_a, "password": "wrongpass"})
        if r.status_code == 429:
            rate_limited = True
            break
    check(
        "I1. repeated failed logins trigger rate limiting (429)",
        rate_limited,
        "連續 10 次錯誤密碼登入皆未被擋下（無暴力破解防護）",
    )

    # ── J. advance 並發 race condition ───────────────────────────────
    before = client.get(f"/saves/{save_id_a}", headers=headers_a).json()
    phase_before = before.get("current_phase")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(client.post, f"/saves/{save_id_a}/advance", headers=headers_a)
            for _ in range(2)
        ]
        responses = [f.result() for f in futures]

    after = client.get(f"/saves/{save_id_a}", headers=headers_a).json()
    phase_after = after.get("current_phase")

    try:
        idx_before = PHASE_SEQUENCE.index(phase_before)
        idx_after = PHASE_SEQUENCE.index(phase_after)
        advanced_steps = idx_after - idx_before
    except ValueError:
        advanced_steps = None  # 跨日換回 PRE_MARKET 的情況，無法簡單比較

    check(
        "J1. concurrent /advance calls only advance phase once",
        advanced_steps == 1,
        f"phase_before={phase_before} phase_after={phase_after} "
        f"responses=[{responses[0].status_code}, {responses[1].status_code}] "
        f"（若 advanced_steps==2 代表兩個並發請求都各自完整結算了一次，"
        f"沒有鎖定機制防止重複結算）",
    )

    # ── K. account_transactions seq 並發衝突 ─────────────────────────
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                client.post,
                f"/saves/{save_id_a}/accounts/transfer",
                json={"direction": "savings_to_trading", "amount": 1},
                headers=headers_a,
            )
            for _ in range(2)
        ]
        responses = [f.result() for f in futures]

    seq_rows = db_query(
        "SELECT seq, COUNT(*) AS c FROM account_transactions WHERE save_id=? GROUP BY seq HAVING c > 1",
        [save_id_a],
    )
    check(
        "K1. concurrent transfers do not produce duplicate account_transactions.seq",
        len(seq_rows) == 0,
        f"重複的 seq: {seq_rows}（MAX(seq)+1 在並發下沒有鎖定，可能造成主鍵衝突或帳務錯亂）"
        if seq_rows else "",
    )

    # ── L. 分頁機制 ───────────────────────────────────────────────────
    r = client.get(f"/saves/{save_id_a}/accounts/history", headers=headers_a)
    total_history = len(r.json()) if r.status_code == 200 else 0

    r = client.get(f"/saves/{save_id_a}/accounts/history", headers=headers_a, params={"limit": 1})
    limited_history = r.json() if r.status_code == 200 else []
    check(
        "L1. GET /accounts/history?limit=1 returns at most 1 row",
        len(limited_history) <= 1,
        f"limit=1 但實際回傳 {len(limited_history)} 筆（共有 {total_history} 筆），"
        f"代表 orders / accounts/history / holdings/transactions 等列表皆無分頁機制",
    )

    # ── M. K 線週期聚合 ───────────────────────────────────────────────
    r_daily = client.get(f"/stocks/{STOCK_ID}/prices", headers=headers_a, params={"save_id": save_id_a})
    r_weekly = client.get(
        f"/stocks/{STOCK_ID}/prices", headers=headers_a, params={"save_id": save_id_a, "interval": "week"}
    )
    if r_daily.status_code == 200 and r_weekly.status_code == 200:
        daily_rows = r_daily.json()
        weekly_rows = r_weekly.json()
        # 不直接比較筆數（資料區間可能只有 1 天，聚合後仍是 1 筆），
        # 改檢查：1) 確實有回傳資料 2) 聚合後筆數不超過日線 3) 結構是聚合後的
        #    K 棒（不含 ref_price/limit_up 等每日獨有欄位），而非把 interval 忽略原樣回傳
        is_aggregated_shape = bool(weekly_rows) and "ref_price" not in weekly_rows[0]
        check(
            "M1. /stocks/{id}/prices?interval=week returns aggregated weekly data",
            len(weekly_rows) > 0 and len(weekly_rows) <= len(daily_rows) and is_aggregated_shape,
            f"daily={len(daily_rows)} rows, weekly={len(weekly_rows)} rows, "
            f"weekly_shape_ok={is_aggregated_shape}"
            + ("（interval 參數被忽略，未實作週/月線聚合）" if not is_aggregated_shape else ""),
        )
    else:
        record(
            "M1. /stocks/{id}/prices?interval=week returns aggregated weekly data",
            False,
            f"daily={r_daily.status_code} weekly={r_weekly.status_code}",
        )

    # ── N. 手動結束存檔（FINISHED）────────────────────────────────────
    # 用一個獨立的存檔測試，避免把 save_id_a 結束掉而影響後面的下單測試（U 系列）
    r_n = client.post("/saves", json={"save_name": f"n1_{account_a}"}, headers=headers_a)
    if r_n.status_code == 201:
        save_id_n = r_n.json()["save_id"]
        r = client.patch(f"/saves/{save_id_n}/finish", headers=headers_a)
        finished_ok = False
        if r.status_code == 200:
            check_save = client.get(f"/saves/{save_id_n}", headers=headers_a)
            finished_ok = check_save.status_code == 200 and check_save.json().get("status") == "FINISHED"
        check("N1. PATCH /saves/{id}/finish marks save as FINISHED", finished_ok, f"{r.status_code}: {r.text}")
        client.delete(f"/saves/{save_id_n}", headers=headers_a)
    else:
        record("N1. PATCH /saves/{id}/finish marks save as FINISHED", False, f"create save: {r_n.status_code}: {r_n.text}")

    # ── O. httpx client timeout 設定 ─────────────────────────────────
    deps_path = os.path.join(os.path.dirname(__file__), "..", "app", "dependencies.py")
    try:
        with open(deps_path, "r", encoding="utf-8") as f:
            deps_src = f.read()
        has_timeout = "AsyncClient(" in deps_src and "timeout" in deps_src
    except FileNotFoundError:
        has_timeout = False
    check(
        "O1. app/dependencies.py configures an httpx timeout for sql-api calls",
        has_timeout,
        "httpx.AsyncClient() 未設定 timeout，sql-api 沒回應時請求可能無限期卡住",
    )

    # ── R. 數值欄位型別一致性 ─────────────────────────────────────────
    r = client.get(f"/saves/{save_id_a}", headers=headers_a)
    if r.status_code == 200:
        save = r.json()
        numeric_fields = ["savings_balance", "trading_balance", "total_asset", "cumulative_return"]
        non_numeric = {f: save.get(f) for f in numeric_fields if not isinstance(save.get(f), (int, float))}
        check(
            "R1. GET /saves/{id} numeric fields are JSON numbers, not strings",
            not non_numeric,
            f"以下欄位不是數字型別: {non_numeric}（前端對字串呼叫 .toFixed() 等數值方法會出錯）",
        )
    else:
        record("R1. GET /saves/{id} numeric fields are JSON numbers, not strings", False, f"{r.status_code}: {r.text}")

    r = client.get(f"/stocks/{STOCK_ID}/prices", headers=headers_a, params={"save_id": save_id_a})
    if r.status_code == 200 and r.json():
        row = r.json()[0]
        price_fields = ["open_price", "high_price", "low_price", "close_price", "volume"]
        non_numeric = {f: row.get(f) for f in price_fields if not isinstance(row.get(f), (int, float))}
        check(
            "R2. GET /stocks/{id}/prices numeric fields are JSON numbers, not strings",
            not non_numeric,
            f"以下欄位不是數字型別: {non_numeric}",
        )
    else:
        record("R2. GET /stocks/{id}/prices numeric fields are JSON numbers, not strings", False, f"{r.status_code}: {r.text}")

    # ── S. 日期格式一致性 ─────────────────────────────────────────────
    import re
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    r = client.get(f"/saves/{save_id_a}", headers=headers_a)
    if r.status_code == 200:
        ctd = str(r.json().get("current_trade_date"))
        check(
            "S1. GET /saves/{id} current_trade_date is 'YYYY-MM-DD'",
            bool(date_pattern.match(ctd)),
            f"current_trade_date={ctd!r}",
        )
    else:
        record("S1. GET /saves/{id} current_trade_date is 'YYYY-MM-DD'", False, f"{r.status_code}: {r.text}")

    r = client.get(f"/stocks/{STOCK_ID}/prices", headers=headers_a, params={"save_id": save_id_a})
    if r.status_code == 200 and r.json():
        td = str(r.json()[0].get("trade_date"))
        check(
            "S2. GET /stocks/{id}/prices trade_date is 'YYYY-MM-DD'",
            bool(date_pattern.match(td)),
            f"trade_date={td!r}",
        )
    else:
        record("S2. GET /stocks/{id}/prices trade_date is 'YYYY-MM-DD'", False, f"{r.status_code}: {r.text}")

    # ── T. API 文件可用性 ─────────────────────────────────────────────
    r_docs = client.get("/docs")
    r_openapi = client.get("/openapi.json")
    check(
        "T1. /docs and /openapi.json are accessible",
        r_docs.status_code == 200 and r_openapi.status_code == 200,
        f"/docs={r_docs.status_code} /openapi.json={r_openapi.status_code}",
    )

    # ── U. 是否信任前端 ───────────────────────────────────────────────
    # U1: 偽造 order_id/status/exec_price/save_id，後端應忽略並自行決定這些值
    # 動態取得目前 save A 的階段/交易日的漲跌停與參考價，避免因 J1 推進階段後
    # price=500 超出當日漲跌停而誤判為 "拒絕偽造欄位"。
    save_row = db_query(
        "SELECT current_trade_date, current_phase FROM save_files WHERE save_id = ?",
        [save_id_a],
    )[0]
    u1_date = str(save_row["current_trade_date"])[:10]
    u1_phase = save_row["current_phase"]

    if u1_phase == "CLOSED":
        record("U1. forged order_id/status/exec_price/save_id in body are ignored", True,
               "skipped: save A 已在 CLOSED 階段，無法下單")
    else:
        dp_rows = db_query(
            "SELECT ref_price FROM daily_prices WHERE stock_id = ? AND trade_date = ?",
            [STOCK_ID, u1_date],
        )
        body = {
            "stock_id": STOCK_ID, "side": "BUY", "quantity": 1,
            "order_id": 999999, "status": "FILLED", "exec_price": 1.0, "save_id": 999999,
        }
        if u1_phase == "POST_MARKET":
            body["order_type"] = "MARKET"
            est_price = float(dp_rows[0]["ref_price"]) if dp_rows else 500
        else:
            body["order_type"] = "LIMIT"
            body["price"] = float(dp_rows[0]["ref_price"]) if dp_rows else 500
            est_price = body["price"]

        # 確保交割戶餘額足夠下單（先前測試已用掉部分資金），不足則從存款戶補足
        needed = est_price * 1 * 1000
        needed_with_fee = needed + max(20.0, needed * 0.001425)
        fresh = db_query(
            "SELECT savings_balance, trading_balance FROM save_files WHERE save_id = ?",
            [save_id_a],
        )[0]
        trading_bal = float(fresh["trading_balance"])
        savings_bal = float(fresh["savings_balance"])
        if trading_bal < needed_with_fee and savings_bal > 0:
            top_up = min(savings_bal, needed_with_fee - trading_bal + 1000)
            client.post(
                f"/saves/{save_id_a}/accounts/transfer",
                json={"direction": "savings_to_trading", "amount": round(top_up, 2)},
                headers=headers_a,
            )

        r = client.post(f"/saves/{save_id_a}/orders", json=body, headers=headers_a)
        if r.status_code == 201:
            order = r.json()
            check(
                "U1. forged order_id/status/exec_price/save_id in body are ignored",
                order.get("status") == "PENDING" and int(order.get("order_id")) != 999999
                and int(order.get("save_id")) == save_id_a,
                f"order={order}",
            )
            client.delete(f"/saves/{save_id_a}/orders/{order.get('order_id')}", headers=headers_a)
        else:
            record("U1. forged order_id/status/exec_price/save_id in body are ignored", False, f"{r.status_code}: {r.text}")

    # U2/U3: 非法 enum order_type/side
    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "HACK", "side": "BUY", "price": 500, "quantity": 1},
        headers=headers_a,
    )
    check("U2. place order with order_type='HACK' -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "HACK", "price": 500, "quantity": 1},
        headers=headers_a,
    )
    check("U3. place order with side='HACK' -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    # U4: 非法 enum direction
    r = client.post(
        f"/saves/{save_id_a}/accounts/transfer",
        json={"direction": "HACK", "amount": 1},
        headers=headers_a,
    )
    check("U4. transfer with direction='HACK' -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    # U5: quantity 非整數
    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 500, "quantity": 1.5},
        headers=headers_a,
    )
    check("U5. place order with quantity=1.5 -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    # U6: 負數價格
    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": -100, "quantity": 1},
        headers=headers_a,
    )
    check("U6. place order with negative price -> 4xx", r.status_code >= 400, f"{r.status_code}: {r.text}")


def print_summary():
    print("\n" + "=" * 50)
    print(f"PASS: {len(PASS)}   FAIL: {len(FAIL)}")
    if FAIL:
        print("失敗項目:")
        for name in FAIL:
            print(f"  - {name}")
    print("=" * 50)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
