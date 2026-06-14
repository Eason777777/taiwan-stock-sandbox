"""
資安與邊界案例測試（pytest 版本）- test_security.py

這份測試對照的是「應該要有的防護/功能」，不是現在程式碼的樣子。
`flow` fixture（session-scoped）依照原 security_test.py run() 的順序執行一次完整序列，
把每一項「預期結果」的 (是否通過, detail) 存進 results dict；下方依字母/數字編號
動態產生對應的 test_<ID> 函式，逐一斷言。

用法:
    1. 另開一個 terminal 啟動 server: uvicorn app.main:app --reload
    2. pytest backend_tests/test_security.py -v

────────────────────────────────────────────────────────────────────────
測試項目清單（依執行順序，詳細說明請見原 security_test.py 開頭註解）
────────────────────────────────────────────────────────────────────────
A1-A7   跨使用者存取控制
B1      session 單一登入原則
C1-C6   輸入驗證邊界
Q1-Q2   SQL Injection 探測
D1      時空隔離是否可被繞過
E1      錯誤訊息是否洩漏內部細節
F1      CORS 設定
G1      sql-api 在 Tailscale 網路內是否仍無認證即可任意查詢
H1-H7   session 過期機制 / 來源 IP 綁定
I1      登入暴力破解防護
J1      advance 並發 race condition
K1      account_transactions seq 並發衝突
L1      分頁機制
M1      K 線週期聚合
N1      手動結束存檔（FINISHED）
O1      SqlApiClient / httpx 是否設定 timeout
R1-R2   數值欄位型別一致性
S1-S2   日期格式一致性
T1      API 文件可用性
U1-U6   是否信任前端（mass-assignment / 偽造欄位 / enum 驗證）
P1-P5   格式錯誤 / 不支援的請求
V1-V5   數值與字串邊界
W1-W9   遊戲規則與存檔狀態機
X1-X4   Session Header 異常處理
Y1,Y2,Y2b 字串長度邊界
Z1-Z7   NaN / Infinity 數值注入
AA1     cancel 與 /advance 結算的並發 race condition
AB1-AB3 更多並發 race condition
AC1     finish 與 advance 並發 race condition
AE1     並發建立存檔，繞過 MAX_ACTIVE_SAVES 上限
AD1-AD10 隨機並發 race condition 模糊測試
AF1-AF10 advance 推進鎖固定情境重複測試
AG1     /auth/register 的 hash thread pool + queue 上限
AH1-AH11 手續費／證交稅／帳戶餘額之台幣整數規則
────────────────────────────────────────────────────────────────────────
"""

import math
import random
import re
import os
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from conftest import (
    HASH_QUEUE_MAX,
    MAX_ACTIVE_SAVES_LIMIT,
    PHASE_SEQUENCE,
    SQL_API_URL,
    START_DATE,
    STOCK_ID,
    _round_to_tick,
    db_query,
    get_order_price,
    random_suffix,
    register_and_login,
)

AG1_NAME = "AG1. concurrent registration burst is throttled by hash queue cap (429), no 500s"


def _run_checks(client, account_a, account_b, password, save_id_a, headers_a, headers_b, check):
    record = check

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
    assert r.status_code == 200, f"old session should still work before re-login: {r.status_code}: {r.text}"

    new_session_a = register_and_login(client, account_a, password)
    assert new_session_a, "user A 重新登入失敗"

    r = client.get(f"/saves/{save_id_a}", headers=headers_a)  # 用「舊」session
    check("B1. old session invalidated after re-login -> 401", r.status_code == 401, f"{r.status_code}: {r.text}")
    headers_a = {"X-Session-Id": new_session_a}  # 之後改用新 session

    # ── C. 輸入驗證邊界 ───────────────────────────────────────────────
    r = client.post("/auth/register", json={"account": "", "password": ""})
    check("C1. register with empty account/password -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")
    if r.status_code == 201:
        db_query("DELETE FROM users WHERE account = ?", [""])

    r = client.post(
        f"/saves/{save_id_a}/accounts/transfer",
        json={"direction": "savings_to_trading", "amount": -100},
        headers=headers_a,
    )
    check("C2. transfer negative amount -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 500, "quantity": 0},
        headers=headers_a,
    )
    check("C3. order quantity <= 0 -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 500.37, "quantity": 1},
        headers=headers_a,
    )
    check("C4. LIMIT price violates tick size -> 4xx", r.status_code >= 400, f"{r.status_code}: {r.text}")

    rand_c = random_suffix()
    r = client.post(
        "/saves",
        json={"save_name": f"sec_neg_{rand_c}", "start_date": START_DATE, "initial_funds": -100},
        headers=headers_a,
    )
    check("C5. create save with initial_funds = -100 -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    r = client.post(
        "/saves",
        json={"save_name": f"sec_over_{rand_c}", "start_date": START_DATE, "initial_funds": 2000000},
        headers=headers_a,
    )
    check("C6. create save with initial_funds = 2000000 -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    # ── Q. SQL Injection 探測 ─────────────────────────────────────────
    r = client.get("/stocks", params={"q": "2330' OR '1'='1"}, headers=headers_a)
    check("Q1. search stocks with SQL injection payload -> 200 (no 500)", r.status_code == 200, f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": "' OR '1'='1", "order_type": "LIMIT", "side": "BUY", "price": 100, "quantity": 1},
        headers=headers_a,
    )
    check("Q2. place order with SQL injection stock_id -> 404 (no 500)", r.status_code == 404, f"{r.status_code}: {r.text}")

    # ── D. 時空隔離是否可被繞過 ──────────────────────────────────────
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
    check("F1. OPTIONS preflight includes Access-Control-Allow-Origin", bool(cors_header), f"{r.status_code}, headers={dict(r.headers)}")

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
    check("H1. users table has a session expiry column", has_expiry_col, f"users 表欄位: {col_names}（無到期欄位 -> session 永久有效，token 外洩風險高）")

    r = client.get(f"/saves/{save_id_a}", headers={**headers_a, "X-Forwarded-For": "203.0.113.1"})
    check("H2. session used from a different source IP -> 401", r.status_code == 401, f"{r.status_code}: {r.text}（session 未綁定來源 IP，token 外洩後可在任何機器上使用）")

    r = client.get(f"/saves/{save_id_a}", headers=headers_a)
    check("H3. session still works from the original source IP", r.status_code == 200, f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id_a}", headers={**headers_a, "X-Forwarded-For": "127.0.0.5"})
    check("H4. session still works from a different IP in the same /24 (DHCP)", r.status_code == 200, f"{r.status_code}: {r.text}（/24 網段比對未生效，DHCP 換 IP 會被誤判為跨機使用）")

    r = client.get(f"/saves/{save_id_a}", headers={**headers_a, "X-Forwarded-For": "::1"})
    check("H5. session still works when a follow-up request reports IPv6 loopback (::1)", r.status_code == 200, f"{r.status_code}: {r.text}（::1 應正規化為 127.0.0.1，與登入時記錄的 loopback 網段視為相同）")

    account_h6 = f"sectest_h6_{random_suffix()}"
    client.post("/auth/register", json={"account": account_h6, "password": password})
    r = client.post("/auth/login", json={"account": account_h6, "password": password}, headers={"X-Forwarded-For": "::1"})
    session_h6 = r.json().get("session_id") if r.status_code == 200 else None
    if session_h6:
        headers_h6 = {"X-Session-Id": session_h6}
        r = client.get("/saves", headers={**headers_h6, "X-Forwarded-For": "127.0.0.9"})
        check("H6. session logged in from ::1 still works from IPv4 loopback afterwards", r.status_code == 200, f"{r.status_code}: {r.text}（登入時 session_ip 存成 \"::1\"，正規化後應與 127.0.0.x 視為同網段）")
    else:
        record("H6. session logged in from ::1 still works from IPv4 loopback afterwards", False, "setup login failed")
    db_query("DELETE FROM users WHERE account=?", [account_h6])

    r = client.get(f"/saves/{save_id_a}", headers={**headers_a, "X-Forwarded-For": "::ffff:203.0.113.1"})
    check("H7. IPv4-mapped IPv6 address from a genuinely different subnet -> 401", r.status_code == 401, f"{r.status_code}: {r.text}（::ffff:203.0.113.1 正規化為 203.0.113.1，與 loopback 不同網段，應被擋）")

    # ── I. 登入暴力破解防護 ───────────────────────────────────────────
    rate_limited = False
    for _ in range(10):
        r = client.post("/auth/login", json={"account": account_a, "password": "wrongpass"})
        if r.status_code == 429:
            rate_limited = True
            break
    check("I1. repeated failed logins trigger rate limiting (429)", rate_limited, "連續 10 次錯誤密碼登入皆未被擋下（無暴力破解防護）")

    # ── J. advance 並發 race condition ───────────────────────────────
    before = client.get(f"/saves/{save_id_a}", headers=headers_a).json()
    phase_before = before.get("current_phase")

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, f"/saves/{save_id_a}/advance", headers=headers_a) for _ in range(2)]
        responses = [f.result() for f in futures]

    after = client.get(f"/saves/{save_id_a}", headers=headers_a).json()
    phase_after = after.get("current_phase")

    try:
        idx_before = PHASE_SEQUENCE.index(phase_before)
        idx_after = PHASE_SEQUENCE.index(phase_after)
        advanced_steps = idx_after - idx_before
    except ValueError:
        advanced_steps = None

    check(
        "J1. concurrent /advance calls only advance phase once",
        advanced_steps == 1,
        f"phase_before={phase_before} phase_after={phase_after} "
        f"responses=[{responses[0].status_code}, {responses[1].status_code}] "
        f"（若 advanced_steps==2 代表兩個並發請求都各自完整結算了一次，沒有鎖定機制防止重複結算）",
    )

    # ── K. account_transactions seq 並發衝突 ─────────────────────────
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(client.post, f"/saves/{save_id_a}/accounts/transfer", json={"direction": "savings_to_trading", "amount": 1}, headers=headers_a)
            for _ in range(2)
        ]
        responses = [f.result() for f in futures]

    seq_rows = db_query("SELECT seq, COUNT(*) AS c FROM account_transactions WHERE save_id=? GROUP BY seq HAVING c > 1", [save_id_a])
    check(
        "K1. concurrent transfers do not produce duplicate account_transactions.seq",
        len(seq_rows) == 0,
        f"重複的 seq: {seq_rows}（MAX(seq)+1 在並發下沒有鎖定，可能造成主鍵衝突或帳務錯亂）" if seq_rows else "",
    )

    # ── L. 分頁機制 ───────────────────────────────────────────────────
    r = client.get(f"/saves/{save_id_a}/accounts/history", headers=headers_a)
    total_history = len(r.json()) if r.status_code == 200 else 0

    r = client.get(f"/saves/{save_id_a}/accounts/history", headers=headers_a, params={"limit": 1})
    limited_history = r.json() if r.status_code == 200 else []
    check(
        "L1. GET /accounts/history?limit=1 returns at most 1 row",
        len(limited_history) <= 1,
        f"limit=1 但實際回傳 {len(limited_history)} 筆（共有 {total_history} 筆），代表 orders / accounts/history / holdings/transactions 等列表皆無分頁機制",
    )

    # ── M. K 線週期聚合 ───────────────────────────────────────────────
    r_daily = client.get(f"/stocks/{STOCK_ID}/prices", headers=headers_a, params={"save_id": save_id_a})
    r_weekly = client.get(f"/stocks/{STOCK_ID}/prices", headers=headers_a, params={"save_id": save_id_a, "interval": "week"})
    if r_daily.status_code == 200 and r_weekly.status_code == 200:
        daily_rows = r_daily.json()
        weekly_rows = r_weekly.json()
        is_aggregated_shape = bool(weekly_rows) and "ref_price" not in weekly_rows[0]
        check(
            "M1. /stocks/{id}/prices?interval=week returns aggregated weekly data",
            len(weekly_rows) > 0 and len(weekly_rows) <= len(daily_rows) and is_aggregated_shape,
            f"daily={len(daily_rows)} rows, weekly={len(weekly_rows)} rows, weekly_shape_ok={is_aggregated_shape}"
            + ("（interval 參數被忽略，未實作週/月線聚合）" if not is_aggregated_shape else ""),
        )
    else:
        record("M1. /stocks/{id}/prices?interval=week returns aggregated weekly data", False, f"daily={r_daily.status_code} weekly={r_weekly.status_code}")

    # ── N. 手動結束存檔（FINISHED）────────────────────────────────────
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
    check("O1. app/dependencies.py configures an httpx timeout for sql-api calls", has_timeout, "httpx.AsyncClient() 未設定 timeout，sql-api 沒回應時請求可能無限期卡住")

    # ── R. 數值欄位型別一致性 ─────────────────────────────────────────
    r = client.get(f"/saves/{save_id_a}", headers=headers_a)
    if r.status_code == 200:
        save = r.json()
        numeric_fields = ["savings_balance", "trading_balance", "total_asset", "cumulative_return"]
        non_numeric = {f: save.get(f) for f in numeric_fields if not isinstance(save.get(f), (int, float))}
        check("R1. GET /saves/{id} numeric fields are JSON numbers, not strings", not non_numeric, f"以下欄位不是數字型別: {non_numeric}（前端對字串呼叫 .toFixed() 等數值方法會出錯）")
    else:
        record("R1. GET /saves/{id} numeric fields are JSON numbers, not strings", False, f"{r.status_code}: {r.text}")

    r = client.get(f"/stocks/{STOCK_ID}/prices", headers=headers_a, params={"save_id": save_id_a})
    if r.status_code == 200 and r.json():
        row = r.json()[0]
        price_fields = ["open_price", "high_price", "low_price", "close_price", "volume"]
        non_numeric = {f: row.get(f) for f in price_fields if not isinstance(row.get(f), (int, float))}
        check("R2. GET /stocks/{id}/prices numeric fields are JSON numbers, not strings", not non_numeric, f"以下欄位不是數字型別: {non_numeric}")
    else:
        record("R2. GET /stocks/{id}/prices numeric fields are JSON numbers, not strings", False, f"{r.status_code}: {r.text}")

    # ── S. 日期格式一致性 ─────────────────────────────────────────────
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    r = client.get(f"/saves/{save_id_a}", headers=headers_a)
    if r.status_code == 200:
        ctd = str(r.json().get("current_trade_date"))
        check("S1. GET /saves/{id} current_trade_date is 'YYYY-MM-DD'", bool(date_pattern.match(ctd)), f"current_trade_date={ctd!r}")
    else:
        record("S1. GET /saves/{id} current_trade_date is 'YYYY-MM-DD'", False, f"{r.status_code}: {r.text}")

    r = client.get(f"/stocks/{STOCK_ID}/prices", headers=headers_a, params={"save_id": save_id_a})
    if r.status_code == 200 and r.json():
        td = str(r.json()[0].get("trade_date"))
        check("S2. GET /stocks/{id}/prices trade_date is 'YYYY-MM-DD'", bool(date_pattern.match(td)), f"trade_date={td!r}")
    else:
        record("S2. GET /stocks/{id}/prices trade_date is 'YYYY-MM-DD'", False, f"{r.status_code}: {r.text}")

    # ── T. API 文件可用性 ─────────────────────────────────────────────
    r_docs = client.get("/docs")
    r_openapi = client.get("/openapi.json")
    check("T1. /docs and /openapi.json are accessible", r_docs.status_code == 200 and r_openapi.status_code == 200, f"/docs={r_docs.status_code} /openapi.json={r_openapi.status_code}")

    # ── U. 是否信任前端 ───────────────────────────────────────────────
    save_row = db_query("SELECT current_trade_date, current_phase FROM save_files WHERE save_id = ?", [save_id_a])[0]
    u1_date = str(save_row["current_trade_date"])[:10]
    u1_phase = save_row["current_phase"]

    if u1_phase == "CLOSED":
        record("U1. forged order_id/status/exec_price/save_id in body are ignored", True, "skipped: save A 已在 CLOSED 階段，無法下單")
    else:
        dp_rows = db_query("SELECT ref_price FROM daily_prices WHERE stock_id = ? AND trade_date = ?", [STOCK_ID, u1_date])
        body = {"stock_id": STOCK_ID, "side": "BUY", "quantity": 1, "order_id": 999999, "status": "FILLED", "exec_price": 1.0, "save_id": 999999}
        if u1_phase == "POST_MARKET":
            body["order_type"] = "MARKET"
            est_price = float(dp_rows[0]["ref_price"]) if dp_rows else 500
        else:
            body["order_type"] = "LIMIT"
            body["price"] = float(dp_rows[0]["ref_price"]) if dp_rows else 500
            est_price = body["price"]

        needed = est_price * 1 * 1000
        needed_with_fee = needed + max(20, math.floor(needed * 0.001425))
        fresh = db_query("SELECT savings_balance, trading_balance FROM save_files WHERE save_id = ?", [save_id_a])[0]
        trading_bal = float(fresh["trading_balance"])
        savings_bal = float(fresh["savings_balance"])
        if trading_bal < needed_with_fee and savings_bal > 0:
            top_up = min(savings_bal, needed_with_fee - trading_bal + 1000)
            client.post(f"/saves/{save_id_a}/accounts/transfer", json={"direction": "savings_to_trading", "amount": math.floor(top_up)}, headers=headers_a)

        r = client.post(f"/saves/{save_id_a}/orders", json=body, headers=headers_a)
        if r.status_code == 201:
            order = r.json()
            check(
                "U1. forged order_id/status/exec_price/save_id in body are ignored",
                order.get("status") == "PENDING" and int(order.get("order_id")) != 999999 and int(order.get("save_id")) == save_id_a,
                f"order={order}",
            )
            client.delete(f"/saves/{save_id_a}/orders/{order.get('order_id')}", headers=headers_a)
        else:
            record("U1. forged order_id/status/exec_price/save_id in body are ignored", False, f"{r.status_code}: {r.text}")

    r = client.post(f"/saves/{save_id_a}/orders", json={"stock_id": STOCK_ID, "order_type": "HACK", "side": "BUY", "price": 500, "quantity": 1}, headers=headers_a)
    check("U2. place order with order_type='HACK' -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    r = client.post(f"/saves/{save_id_a}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "HACK", "price": 500, "quantity": 1}, headers=headers_a)
    check("U3. place order with side='HACK' -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    r = client.post(f"/saves/{save_id_a}/accounts/transfer", json={"direction": "HACK", "amount": 1}, headers=headers_a)
    check("U4. transfer with direction='HACK' -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    r = client.post(f"/saves/{save_id_a}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 500, "quantity": 1.5}, headers=headers_a)
    check("U5. place order with quantity=1.5 -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.post(f"/saves/{save_id_a}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": -100, "quantity": 1}, headers=headers_a)
    check("U6. place order with negative price -> 4xx", r.status_code >= 400, f"{r.status_code}: {r.text}")

    # ── P. 格式錯誤 / 不支援的請求 ─────────────────────────────────────
    r = client.post(f"/saves/{save_id_a}/orders", json={}, headers=headers_a)
    check("P1. place order with empty body {} -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.post(f"/saves/{save_id_a}/orders", content=b"not json", headers={**headers_a, "Content-Type": "application/json"})
    check("P2. place order with malformed JSON body -> 4xx (not 500)", r.status_code in (400, 422), f"{r.status_code}: {r.text}")

    r = client.get("/saves/not-an-integer", headers=headers_a)
    check("P3. GET /saves/{non-integer} -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.get("/this-route-does-not-exist")
    check("P4. unknown route -> 404", r.status_code == 404, f"{r.status_code}: {r.text}")

    r = client.put(f"/saves/{save_id_a}", headers=headers_a)
    check("P5. unsupported method PUT /saves/{id} -> 405", r.status_code == 405, f"{r.status_code}: {r.text}")

    # ── V. 數值與字串邊界 ─────────────────────────────────────────────
    r = client.post(f"/saves/{save_id_a}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 100.0, "quantity": 10 ** 9}, headers=headers_a)
    check("V1. order with quantity=10^9 -> 4xx (not 500)", r.status_code in (400, 422), f"{r.status_code}: {r.text}")

    r = client.post(f"/saves/{save_id_a}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 1e308, "quantity": 1}, headers=headers_a)
    check("V2. order with price=1e308 -> 4xx (not 500)", r.status_code in (400, 422), f"{r.status_code}: {r.text}")

    r = client.post(f"/saves/{save_id_a}/orders", json={"stock_id": "A" * 500, "order_type": "LIMIT", "side": "BUY", "price": 100.0, "quantity": 1}, headers=headers_a)
    check("V3. order with 500-char stock_id -> 404 (not 500)", r.status_code == 404, f"{r.status_code}: {r.text}")

    r = client.get("/stocks", params={"q": "x" * 5000}, headers=headers_a)
    check("V4. search /stocks?q= with 5000-char query -> 200 (not 500)", r.status_code == 200, f"{r.status_code}: {r.text[:200]}")

    rand_v = random_suffix()
    r = client.post("/saves", json={"save_name": "v_" + rand_v + "_" + "x" * 250, "start_date": START_DATE, "initial_funds": 100000}, headers=headers_a)
    check("V5. create save with 250+ char save_name -> not 500", r.status_code != 500, f"{r.status_code}: {r.text[:200]}")
    if r.status_code == 201:
        client.delete(f"/saves/{r.json()['save_id']}", headers=headers_a)

    # ── W. 遊戲規則與存檔狀態機 ───────────────────────────────────────
    r = client.get("/saves/999999999", headers=headers_a)
    check("W1. GET /saves/{nonexistent} -> 404", r.status_code == 404, f"{r.status_code}: {r.text}")

    rand_w = random_suffix()
    rw = client.post("/saves", json={"save_name": f"w_{rand_w}", "start_date": START_DATE, "initial_funds": 1000000}, headers=headers_a)
    save_id_w = rw.json().get("save_id") if rw.status_code == 201 else None

    if save_id_w:
        r = client.post(f"/saves/{save_id_w}/orders", json={"stock_id": "9999999", "order_type": "LIMIT", "side": "BUY", "price": 100, "quantity": 1}, headers=headers_a)
        check("W2. order on nonexistent stock_id -> 404", r.status_code == 404, f"{r.status_code}: {r.text}")

        price_w = get_order_price(STOCK_ID, START_DATE)
        r = client.post(f"/saves/{save_id_w}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "SELL", "price": price_w, "quantity": 999}, headers=headers_a)
        check("W3. SELL order exceeding holdings -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

        needed_w7 = price_w * 1 * 1000
        needed_w7_with_fee = needed_w7 + max(20, math.floor(needed_w7 * 0.001425))
        client.post(f"/saves/{save_id_w}/accounts/transfer", json={"direction": "savings_to_trading", "amount": math.ceil(needed_w7_with_fee + 1000)}, headers=headers_a)
        r = client.post(f"/saves/{save_id_w}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": price_w, "quantity": 1}, headers=headers_a)
        if r.status_code == 201:
            order_id_w = r.json()["order_id"]
            r1 = client.delete(f"/saves/{save_id_w}/orders/{order_id_w}", headers=headers_a)
            r2 = client.delete(f"/saves/{save_id_w}/orders/{order_id_w}", headers=headers_a)
            check("W7. cancel an already-cancelled order -> 400", r1.status_code == 204 and r2.status_code == 400, f"first={r1.status_code}, second={r2.status_code}: {r2.text}")
        else:
            record("W7. cancel an already-cancelled order -> 400", False, f"setup order failed: {r.status_code}: {r.text}")

        client.delete(f"/saves/{save_id_w}", headers=headers_a)
    else:
        record("W2. order on nonexistent stock_id -> 404", False, "setup failed (throwaway save for W2/W3/W7)")
        record("W3. SELL order exceeding holdings -> 400", False, "setup failed (throwaway save for W2/W3/W7)")
        record("W7. cancel an already-cancelled order -> 400", False, "setup failed (throwaway save for W2/W3/W7)")

    rw4 = client.post("/saves", json={"save_name": f"w4_{rand_w}", "start_date": START_DATE, "initial_funds": 100000}, headers=headers_a)
    if rw4.status_code == 201:
        sid = rw4.json()["save_id"]
        db_query("UPDATE save_files SET current_phase='CLOSED' WHERE save_id=?", [sid])
        r = client.post(f"/saves/{sid}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 100, "quantity": 1}, headers=headers_a)
        check("W4. place order while phase=CLOSED -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")
        client.delete(f"/saves/{sid}", headers=headers_a)
    else:
        record("W4. place order while phase=CLOSED -> 400", False, f"setup failed: {rw4.status_code}")

    rw5 = client.post("/saves", json={"save_name": f"w5_{rand_w}", "start_date": START_DATE, "initial_funds": 100000}, headers=headers_a)
    if rw5.status_code == 201:
        sid = rw5.json()["save_id"]
        db_query("UPDATE save_files SET status='BANKRUPT' WHERE save_id=?", [sid])
        r_order = client.post(f"/saves/{sid}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 100, "quantity": 1}, headers=headers_a)
        r_adv = client.post(f"/saves/{sid}/advance", headers=headers_a)
        check("W5. place order / advance on BANKRUPT save -> 400", r_order.status_code == 400 and r_adv.status_code == 400, f"order={r_order.status_code}, advance={r_adv.status_code}: {r_order.text} / {r_adv.text}")
        client.delete(f"/saves/{sid}", headers=headers_a)
    else:
        record("W5. place order / advance on BANKRUPT save -> 400", False, f"setup failed: {rw5.status_code}")

    rw6 = client.post("/saves", json={"save_name": f"w6_{rand_w}", "start_date": START_DATE, "initial_funds": 100000}, headers=headers_a)
    if rw6.status_code == 201:
        sid = rw6.json()["save_id"]
        fr = client.patch(f"/saves/{sid}/finish", headers=headers_a)
        r_order = client.post(f"/saves/{sid}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 100, "quantity": 1}, headers=headers_a)
        r_adv = client.post(f"/saves/{sid}/advance", headers=headers_a)
        check("W6. place order / advance on FINISHED save -> 400", fr.status_code == 200 and r_order.status_code == 400 and r_adv.status_code == 400, f"finish={fr.status_code}, order={r_order.status_code}, advance={r_adv.status_code}")
        client.delete(f"/saves/{sid}", headers=headers_a)
    else:
        record("W6. place order / advance on FINISHED save -> 400", False, f"setup failed: {rw6.status_code}")

    active_rows = db_query("SELECT save_id FROM save_files WHERE user_id=(SELECT user_id FROM users WHERE account=?) AND status='ACTIVE'", [account_a])
    extra_saves = []
    to_create = max(0, 5 - len(active_rows))
    setup_ok = True
    for i in range(to_create):
        rr = client.post("/saves", json={"save_name": f"w8_{rand_w}_{i}", "start_date": START_DATE, "initial_funds": 100000}, headers=headers_a)
        if rr.status_code == 201:
            extra_saves.append(rr.json()["save_id"])
        else:
            setup_ok = False

    if setup_ok:
        r = client.post("/saves", json={"save_name": f"w8_over_{rand_w}", "start_date": START_DATE, "initial_funds": 100000}, headers=headers_a)
        check("W8. create save beyond MAX_ACTIVE_SAVES(5) -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")
        if r.status_code == 201:
            extra_saves.append(r.json()["save_id"])
    else:
        record("W8. create save beyond MAX_ACTIVE_SAVES(5) -> 400", False, "setup failed (could not create enough ACTIVE saves)")

    for sid in extra_saves:
        client.delete(f"/saves/{sid}", headers=headers_a)

    r = client.post("/saves", json={"save_name": f"sec_{account_a}", "start_date": START_DATE, "initial_funds": 100000}, headers=headers_a)
    check("W9. create save with duplicate name -> 409", r.status_code == 409, f"{r.status_code}: {r.text}")

    # ── X. Session Header 異常處理 ───────────────────────────────────
    r = client.get(f"/saves/{save_id_a}")
    check("X1. request without X-Session-Id header -> 401/422", r.status_code in (401, 422), f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id_a}", headers={"X-Session-Id": "' OR '1'='1"})
    check("X2. X-Session-Id with SQL injection payload -> 401 (not 500)", r.status_code == 401, f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id_a}", headers={"X-Session-Id": ""})
    check("X3. empty X-Session-Id -> 401/422", r.status_code in (401, 422), f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id_a}", headers={"X-Session-Id": "a" * 10000})
    check("X4. extremely long X-Session-Id (10000 chars) -> 401 (not 500)", r.status_code == 401, f"{r.status_code}: {r.text}")

    # ── Y. 字串長度邊界 ──────────────────────────────────────────────
    long_account = "y_" + random_suffix(60)
    r = client.post("/auth/register", json={"account": long_account, "password": "test1234"})
    check("Y1. register with 60-char account (> VARCHAR(50)) -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    account_y = f"sectest_y_{random_suffix()}"
    client.post("/auth/register", json={"account": account_y, "password": "test1234"})
    long_xff = "9" * 200
    r = client.post("/auth/login", json={"account": account_y, "password": "test1234"}, headers={"X-Forwarded-For": long_xff})
    check("Y2. login with oversized X-Forwarded-For (200 chars, no comma) -> 200 (not 500)", r.status_code == 200 and "session_id" in r.json(), f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        stored = db_query("SELECT session_ip FROM users WHERE account=?", [account_y])
        session_ip_len = len(stored[0]["session_ip"] or "") if stored else -1
        check("Y2b. stored session_ip is truncated to <= 45 chars", 0 <= session_ip_len <= 45, f"session_ip length={session_ip_len}")
    else:
        record("Y2b. stored session_ip is truncated to <= 45 chars", False, "setup login failed (Y2)")
    db_query("DELETE FROM users WHERE account=?", [account_y])

    # ── Z. NaN / Infinity 數值注入 ────────────────────────────────────
    r = client.post(f"/saves/{save_id_a}/accounts/transfer", content='{"direction": "savings_to_trading", "amount": NaN}', headers={**headers_a, "Content-Type": "application/json"})
    check("Z1. transfer amount=NaN -> 422 (not 500 / data corruption)", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.post(f"/saves/{save_id_a}/accounts/transfer", content='{"direction": "savings_to_trading", "amount": Infinity}', headers={**headers_a, "Content-Type": "application/json"})
    check("Z2. transfer amount=Infinity -> 4xx (not 500)", r.status_code in (400, 422), f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        content='{"stock_id": "%s", "order_type": "LIMIT", "side": "BUY", "price": NaN, "quantity": 1}' % STOCK_ID,
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check("Z3. place LIMIT order with price=NaN -> 422 (not 500)", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        content='{"stock_id": "%s", "order_type": "LIMIT", "side": "BUY", "price": Infinity, "quantity": 1}' % STOCK_ID,
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check("Z4. place LIMIT order with price=Infinity -> 4xx (not 500)", r.status_code in (400, 422), f"{r.status_code}: {r.text}")

    r = client.post(
        "/saves",
        content='{"save_name": "z5_should_not_exist", "start_date": "%s", "initial_funds": NaN}' % START_DATE,
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check("Z5. create save with initial_funds=NaN -> 422 (not 500)", r.status_code == 422, f"{r.status_code}: {r.text}")
    if r.status_code == 201:
        client.delete(f"/saves/{r.json()['save_id']}", headers=headers_a)

    fresh = db_query("SELECT savings_balance, trading_balance FROM save_files WHERE save_id = ?", [save_id_a])
    z6_ok = False
    if fresh:
        try:
            sb = float(fresh[0]["savings_balance"])
            tb = float(fresh[0]["trading_balance"])
            z6_ok = math.isfinite(sb) and math.isfinite(tb)
        except (TypeError, ValueError):
            z6_ok = False
    check("Z6. save balances remain finite numbers after rejected NaN requests", z6_ok, f"row={fresh}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        content='{"stock_id": "%s", "order_type": "LIMIT", "side": "BUY", "price": 100.0, "quantity": %s}' % (STOCK_ID, "9" * 400),
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check("Z7. place order with 400-digit quantity -> 422 (not 500)", r.status_code == 422, f"{r.status_code}: {r.text}")

    # ── AA. cancel 與 /advance 結算的並發 race condition ─────────────
    aa_name = "AA1. concurrent cancel-order vs /advance settlement do not produce inconsistent state"
    rand_aa = random_suffix()
    raa = client.post("/saves", json={"save_name": f"aa_{rand_aa}", "start_date": START_DATE, "initial_funds": 1000000}, headers=headers_a)
    if raa.status_code == 201:
        save_id_aa = raa.json()["save_id"]
        client.post(f"/saves/{save_id_aa}/accounts/transfer", json={"direction": "savings_to_trading", "amount": 1000000}, headers=headers_a)

        dp_rows = db_query("SELECT limit_up FROM daily_prices WHERE stock_id=? AND trade_date=?", [STOCK_ID, START_DATE])
        price_aa = _round_to_tick(float(dp_rows[0]["limit_up"])) if dp_rows else 100.0

        r = client.post(f"/saves/{save_id_aa}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": price_aa, "quantity": 1}, headers=headers_a)
        if r.status_code == 201:
            order_id_aa = r.json()["order_id"]

            with ThreadPoolExecutor(max_workers=2) as pool:
                f_cancel = pool.submit(client.delete, f"/saves/{save_id_aa}/orders/{order_id_aa}", headers=headers_a)
                f_advance = pool.submit(client.post, f"/saves/{save_id_aa}/advance", headers=headers_a)
                r_cancel = f_cancel.result()
                r_advance = f_advance.result()

            order_row = db_query("SELECT status FROM stock_orders WHERE order_id=?", [order_id_aa])[0]
            txn_rows = db_query("SELECT * FROM stock_transactions WHERE order_id=?", [order_id_aa])
            final_status = order_row["status"]
            has_txn = len(txn_rows) > 0

            if r_cancel.status_code == 204:
                consistent = final_status == "CANCELED" and not has_txn
            elif final_status == "FILLED":
                consistent = has_txn and r_cancel.status_code == 400
            else:
                consistent = False

            check(
                aa_name,
                consistent,
                f"cancel={r_cancel.status_code}, advance={r_advance.status_code}, "
                f"final_order_status={final_status}, has_stock_transaction={has_txn}"
                f"（若 cancel 成功(204)卻仍被結算成交，或訂單已成交但 cancel 未回 400，"
                f"代表 cancel 與 /advance 結算之間沒有鎖定機制，造成資料不一致）",
            )
        else:
            record(aa_name, False, f"setup order failed: {r.status_code}: {r.text}")

        client.delete(f"/saves/{save_id_aa}", headers=headers_a)
    else:
        record(aa_name, False, f"setup save failed: {raa.status_code}: {raa.text}")

    # ── AB. 更多並發 race condition 測試 ─────────────────────────────
    ab1_name = "AB1. concurrent double-cancel of the same PENDING order -> exactly one success"
    ab2_name = "AB2. concurrent SELL orders do not bypass holdings check (oversell race)"

    rand_ab = random_suffix()
    rab = client.post("/saves", json={"save_name": f"ab_{rand_ab}", "start_date": START_DATE, "initial_funds": 1000000}, headers=headers_a)
    if rab.status_code == 201:
        save_id_ab = rab.json()["save_id"]
        client.post(f"/saves/{save_id_ab}/accounts/transfer", json={"direction": "savings_to_trading", "amount": 1000000}, headers=headers_a)

        dp_rows = db_query("SELECT limit_up FROM daily_prices WHERE stock_id=? AND trade_date=?", [STOCK_ID, START_DATE])
        limit_up_ab = _round_to_tick(float(dp_rows[0]["limit_up"])) if dp_rows else 100.0
        r_buy = client.post(f"/saves/{save_id_ab}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": limit_up_ab, "quantity": 1}, headers=headers_a)
        client.post(f"/saves/{save_id_ab}/advance", headers=headers_a)

        holding_rows = db_query("SELECT quantity FROM holdings WHERE save_id=? AND stock_id=?", [save_id_ab, STOCK_ID])
        held_qty = int(holding_rows[0]["quantity"]) if holding_rows else 0

        if r_buy.status_code == 201 and held_qty >= 1:
            price_ab = get_order_price(STOCK_ID, START_DATE)

            r_order = client.post(f"/saves/{save_id_ab}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": price_ab, "quantity": 1}, headers=headers_a)
            if r_order.status_code == 201:
                order_id_ab1 = r_order.json()["order_id"]
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(client.delete, f"/saves/{save_id_ab}/orders/{order_id_ab1}", headers=headers_a) for _ in range(2)]
                    responses = [f.result() for f in futures]
                statuses = sorted(r.status_code for r in responses)
                final_row = db_query("SELECT status FROM stock_orders WHERE order_id=?", [order_id_ab1])[0]
                check(
                    ab1_name,
                    statuses == [204, 400] and final_row["status"] == "CANCELED",
                    f"responses={statuses}, final_status={final_row['status']}（預期恰好一次 204、一次 400；若兩次都回 204，代表撤銷未互斥）",
                )
            else:
                record(ab1_name, False, f"setup order failed: {r_order.status_code}: {r_order.text}")

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(client.post, f"/saves/{save_id_ab}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "SELL", "price": price_ab, "quantity": held_qty}, headers=headers_a)
                    for _ in range(2)
                ]
                responses = [f.result() for f in futures]

            accepted = sum(1 for r in responses if r.status_code == 201)
            pending_sell = db_query("SELECT COALESCE(SUM(quantity),0) AS total FROM stock_orders WHERE save_id=? AND stock_id=? AND side='SELL' AND status='PENDING'", [save_id_ab, STOCK_ID])
            total_pending_sell = int(pending_sell[0]["total"])
            check(
                ab2_name,
                accepted <= 1 and total_pending_sell <= held_qty,
                f"accepted={accepted}/2 (each side=SELL qty={held_qty}), held_qty={held_qty}, "
                f"total_pending_sell_quantity={total_pending_sell}"
                f"（若 accepted==2 或 total_pending_sell > held_qty，代表下單時的「持股 - 待成交賣單」檢查存在 TOCTOU race，可賣出超過實際持股數量）",
            )
        else:
            record(ab1_name, False, f"setup failed: buy={r_buy.status_code}, held_qty={held_qty}")
            record(ab2_name, False, f"setup failed: buy={r_buy.status_code}, held_qty={held_qty}")

        client.delete(f"/saves/{save_id_ab}", headers=headers_a)
    else:
        record(ab1_name, False, f"setup save failed: {rab.status_code}: {rab.text}")
        record(ab2_name, False, f"setup save failed: {rab.status_code}: {rab.text}")

    account_ab3 = f"sectest_ab3_{random_suffix()}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(client.post, "/auth/register", json={"account": account_ab3, "password": "test1234"}) for _ in range(2)]
        responses = [f.result() for f in futures]

    statuses = sorted(r.status_code for r in responses)
    user_rows = db_query("SELECT COUNT(*) AS c FROM users WHERE account=?", [account_ab3])
    user_count = int(user_rows[0]["c"])
    check(
        "AB3. concurrent duplicate registration with the same account does not create duplicate users / 500",
        user_count == 1 and 500 not in statuses,
        f"responses={statuses}, user_count={user_count}（預期恰好一筆 users 紀錄，且兩次請求都不應回 500）",
    )
    db_query("DELETE FROM users WHERE account=?", [account_ab3])

    # ── AC. finish 與 advance 並發 race condition ────────────────────
    ac_name = "AC1. concurrent finish vs advance do not leave save status inconsistent"
    rand_ac = random_suffix()
    rac = client.post("/saves", json={"save_name": f"ac_{rand_ac}", "start_date": START_DATE, "initial_funds": 100000}, headers=headers_a)
    if rac.status_code == 201:
        save_id_ac = rac.json()["save_id"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            f_finish = pool.submit(client.patch, f"/saves/{save_id_ac}/finish", headers=headers_a)
            f_advance = pool.submit(client.post, f"/saves/{save_id_ac}/advance", headers=headers_a)
            r_finish = f_finish.result()
            r_advance = f_advance.result()

        final_row = db_query("SELECT status FROM save_files WHERE save_id=?", [save_id_ac])[0]
        final_status = final_row["status"]

        check(
            ac_name,
            not (r_finish.status_code == 200 and final_status != "FINISHED"),
            f"finish={r_finish.status_code}, advance={r_advance.status_code}, final_status={final_status}"
            f"（若 finish 回 200（聲稱已結束）但最終 save_files.status != FINISHED，"
            f"代表 finish 與 /advance 對 save_files 的 UPDATE 互相覆寫，造成狀態不一致）",
        )

        client.delete(f"/saves/{save_id_ac}", headers=headers_a)
    else:
        record(ac_name, False, f"setup save failed: {rac.status_code}: {rac.text}")

    # ── AE. 並發建立存檔，繞過 MAX_ACTIVE_SAVES 上限 ─────────────────
    ae_name = "AE1. concurrent create-save requests do not bypass MAX_ACTIVE_SAVES limit"
    active_rows = db_query("SELECT save_id FROM save_files WHERE user_id=(SELECT user_id FROM users WHERE account=?) AND status='ACTIVE'", [account_a])
    rand_ae = random_suffix()
    extra_saves_ae = []
    to_create = max(0, (MAX_ACTIVE_SAVES_LIMIT - 1) - len(active_rows))
    setup_ok = True
    for i in range(to_create):
        rr = client.post("/saves", json={"save_name": f"ae_setup_{rand_ae}_{i}", "start_date": START_DATE, "initial_funds": 100000}, headers=headers_a)
        if rr.status_code == 201:
            extra_saves_ae.append(rr.json()["save_id"])
        else:
            setup_ok = False

    if setup_ok:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(client.post, "/saves", json={"save_name": f"ae_race_{rand_ae}_{i}", "start_date": START_DATE, "initial_funds": 100000}, headers=headers_a)
                for i in range(2)
            ]
            responses = [f.result() for f in futures]

        accepted = [r for r in responses if r.status_code == 201]
        for r in accepted:
            extra_saves_ae.append(r.json()["save_id"])

        active_count_after = db_query("SELECT COUNT(*) AS c FROM save_files WHERE user_id=(SELECT user_id FROM users WHERE account=?) AND status='ACTIVE'", [account_a])[0]["c"]

        check(
            ae_name,
            int(active_count_after) <= MAX_ACTIVE_SAVES_LIMIT,
            f"accepted={len(accepted)}/2, active_count_after={active_count_after}"
            f"（預期最多只有 1 個請求成功，使進行中存檔數量不超過 {MAX_ACTIVE_SAVES_LIMIT}；"
            f"若兩個都成功，代表 COUNT(*) 檢查與 INSERT 之間存在 TOCTOU race）",
        )
    else:
        record(ae_name, False, "setup failed (could not create enough ACTIVE saves)")

    for sid in extra_saves_ae:
        client.delete(f"/saves/{sid}", headers=headers_a)

    # ── AD. 隨機並發 race condition 模糊測試（重複 10 次）────────────
    dp_rows_ad = db_query("SELECT limit_up FROM daily_prices WHERE stock_id=? AND trade_date=?", [STOCK_ID, START_DATE])
    limit_up_ad = _round_to_tick(float(dp_rows_ad[0]["limit_up"])) if dp_rows_ad else 100.0
    price_ad = get_order_price(STOCK_ID, START_DATE)

    def _ad_invariants(save_id):
        save_row = db_query("SELECT trading_balance, status FROM save_files WHERE save_id=?", [save_id])[0]
        balance = float(save_row["trading_balance"])
        status = save_row["status"]
        if balance < 0 and status != "BANKRUPT":
            return False, f"trading_balance={balance} < 0 但 status={status}（應為 BANKRUPT）"

        for h in db_query("SELECT stock_id, quantity FROM holdings WHERE save_id=?", [save_id]):
            if int(h["quantity"]) < 0:
                return False, f"holdings.quantity={h['quantity']} < 0 (stock_id={h['stock_id']})"

        ledger_rows = db_query("SELECT balance_after FROM account_transactions WHERE save_id=? AND account_type='TRADING' ORDER BY seq DESC LIMIT 1", [save_id])
        if ledger_rows:
            ledger_balance = float(ledger_rows[0]["balance_after"])
            if abs(ledger_balance - balance) > 0.01:
                return False, f"trading_balance={balance} 與帳本最新 balance_after={ledger_balance} 不一致"

        for o in db_query("SELECT order_id, status FROM stock_orders WHERE save_id=?", [save_id]):
            txn_count = len(db_query("SELECT 1 FROM stock_transactions WHERE order_id=?", [o["order_id"]]))
            if o["status"] == "FILLED" and txn_count != 1:
                return False, f"order_id={o['order_id']} status=FILLED 但 stock_transactions 筆數={txn_count}（應為 1）"
            if o["status"] != "FILLED" and txn_count != 0:
                return False, f"order_id={o['order_id']} status={o['status']} 但 stock_transactions 筆數={txn_count}（應為 0）"

        return True, "ok"

    def _ad_act_advance(c, sid, h):
        return c.post(f"/saves/{sid}/advance", headers=h)

    def _ad_act_finish(c, sid, h):
        return c.patch(f"/saves/{sid}/finish", headers=h)

    def _ad_act_place_buy(c, sid, h):
        return c.post(f"/saves/{sid}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": limit_up_ad, "quantity": 1}, headers=h)

    def _ad_act_place_sell(c, sid, h):
        return c.post(f"/saves/{sid}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "SELL", "price": price_ad, "quantity": 1}, headers=h)

    def _ad_act_cancel_pending(c, sid, h):
        pending = db_query("SELECT order_id FROM stock_orders WHERE save_id=? AND status='PENDING' ORDER BY order_id LIMIT 1", [sid])
        if not pending:
            return None
        return c.delete(f"/saves/{sid}/orders/{pending[0]['order_id']}", headers=h)

    AD_ACTIONS = {
        "advance": _ad_act_advance,
        "finish": _ad_act_finish,
        "place_buy": _ad_act_place_buy,
        "place_sell": _ad_act_place_sell,
        "cancel_pending": _ad_act_cancel_pending,
    }

    for i in range(10):
        ad_name = f"AD{i + 1}. random concurrent actions do not break invariants"
        rand_ad = random_suffix()
        rad = client.post("/saves", json={"save_name": f"ad_{rand_ad}_{i}", "start_date": START_DATE, "initial_funds": 500000}, headers=headers_a)
        if rad.status_code != 201:
            record(ad_name, False, f"setup save failed: {rad.status_code}: {rad.text}")
            continue

        save_id_ad = rad.json()["save_id"]
        client.post(f"/saves/{save_id_ad}/accounts/transfer", json={"direction": "savings_to_trading", "amount": 500000}, headers=headers_a)

        client.post(f"/saves/{save_id_ad}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": limit_up_ad, "quantity": 2}, headers=headers_a)
        client.post(f"/saves/{save_id_ad}/advance", headers=headers_a)

        for _ in range(random.randint(0, 2)):
            random.choice([_ad_act_place_buy, _ad_act_place_sell])(client, save_id_ad, headers_a)

        action_names = [random.choice(list(AD_ACTIONS)) for _ in range(2)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(AD_ACTIONS[name], client, save_id_ad, headers_a) for name in action_names]
            responses = [f.result() for f in futures]

        statuses = [r.status_code if r is not None else None for r in responses]
        has_500 = any(s == 500 for s in statuses)
        bodies_500 = [r.text[:500] for r in responses if r is not None and r.status_code == 500]

        ok, detail = _ad_invariants(save_id_ad)
        check(
            ad_name,
            ok and not has_500,
            f"actions={action_names}, responses={statuses}, invariant_check={detail}"
            + (f", 500_body={bodies_500}" if bodies_500 else "")
            + "（隨機挑選 2 個並發操作，檢查是否出現 500 或資料不一致）",
        )

        client.delete(f"/saves/{save_id_ad}", headers=headers_a)

    # ── AF. advance 推進鎖（advancing 旗標）固定情境重複測試（重複 10 次）──
    for i in range(10):
        af_name = f"AF{i + 1}. concurrent finish vs advance (advancing lock) do not break invariants"
        rand_af = random_suffix()
        raf = client.post("/saves", json={"save_name": f"af_{rand_af}_{i}", "start_date": START_DATE, "initial_funds": 500000}, headers=headers_a)
        if raf.status_code != 201:
            record(af_name, False, f"setup save failed: {raf.status_code}: {raf.text}")
            continue

        save_id_af = raf.json()["save_id"]
        client.post(f"/saves/{save_id_af}/accounts/transfer", json={"direction": "savings_to_trading", "amount": 500000}, headers=headers_a)

        client.post(f"/saves/{save_id_af}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": limit_up_ad, "quantity": 1}, headers=headers_a)

        with ThreadPoolExecutor(max_workers=2) as pool:
            f_finish = pool.submit(client.patch, f"/saves/{save_id_af}/finish", headers=headers_a)
            f_advance = pool.submit(client.post, f"/saves/{save_id_af}/advance", headers=headers_a)
            r_finish = f_finish.result()
            r_advance = f_advance.result()

        statuses = [r_finish.status_code, r_advance.status_code]
        has_500 = any(s == 500 for s in statuses)
        bodies_500 = [r.text[:500] for r in (r_finish, r_advance) if r.status_code == 500]

        ok, detail = _ad_invariants(save_id_af)

        lock_row = db_query("SELECT advancing, status FROM save_files WHERE save_id=?", [save_id_af])[0]
        lock_released = int(lock_row["advancing"]) == 0
        final_status = lock_row["status"]

        finish_consistent = not (r_finish.status_code == 200 and final_status != "FINISHED")

        check(
            af_name,
            ok and not has_500 and lock_released and finish_consistent,
            f"finish={r_finish.status_code}, advance={r_advance.status_code}, final_status={final_status}, "
            f"advancing={lock_row['advancing']}, invariant_check={detail}"
            + (f", 500_body={bodies_500}" if bodies_500 else "")
            + "（finish 與 advance 並發：檢查無 500、推進鎖最終釋放、"
              "trading_balance 與帳本一致、且 finish 回 200 時最終狀態必為 FINISHED）",
        )

        client.delete(f"/saves/{save_id_af}", headers=headers_a)

    # ── AG1: /auth/register 同時送出超過 HASH_QUEUE_MAX 個請求 ────────
    n_ag = HASH_QUEUE_MAX + 5
    rand_ag = random_suffix()
    accounts_ag = [f"sectest_ag_{rand_ag}_{i}" for i in range(n_ag)]

    with ThreadPoolExecutor(max_workers=n_ag) as pool:
        futures = [pool.submit(client.post, "/auth/register", json={"account": acc, "password": "test1234"}) for acc in accounts_ag]
        responses = [f.result() for f in futures]

    statuses = [r.status_code for r in responses]
    n_201 = statuses.count(201)
    n_429 = statuses.count(429)
    check(
        AG1_NAME,
        500 not in statuses and n_201 + n_429 == n_ag and n_429 > 0 and n_201 <= HASH_QUEUE_MAX,
        f"statuses={sorted(statuses)}（預期無 500、部分 201 部分 429，且 201 數量不超過 HASH_QUEUE_MAX={HASH_QUEUE_MAX}）",
    )

    for acc in accounts_ag:
        db_query("DELETE FROM users WHERE account=?", [acc])

    # ── AH. 手續費／證交稅／帳戶餘額之台幣整數規則 ────────────────────
    ah_names = [
        "AH1. BUY stock_transactions.fee 為整數（無小數部分）",
        "AH2. BUY 手續費計算正確（floor(本金*0.1425%)，最低 20 元）",
        "AH3. BUY 不收證交稅，stock_transactions.tax = 0",
        "AH4. BUY account_transactions.amount 為整數，且 = 本金 + 手續費",
        "AH5. BUY account_transactions.balance_after 為整數，且 = 扣款後餘額",
        "AH6. SELL stock_transactions.fee / tax 皆為整數",
        "AH7. SELL 手續費計算正確（floor(本金*0.1425%)，最低 20 元）",
        "AH8. SELL 證交稅計算正確（floor(本金*0.3%)）",
        "AH9. SELL account_transactions.amount 為整數，且 = 本金 - 手續費 - 證交稅",
        "AH10. GET /saves/{id} savings_balance/trading_balance 為整數值（無小數餘數）",
        "AH11. 轉帳 amount 帶小數（100.5）-> 422",
    ]

    rand_ah = random_suffix()
    rah = client.post("/saves", json={"save_name": f"ah_{rand_ah}", "start_date": START_DATE, "initial_funds": 1000000}, headers=headers_a)
    if rah.status_code != 201:
        for name in ah_names:
            record(name, False, f"setup: create save failed {rah.status_code}: {rah.text}")
        return

    save_id_ah = rah.json()["save_id"]
    client.post(f"/saves/{save_id_ah}/accounts/transfer", json={"direction": "savings_to_trading", "amount": 1000000}, headers=headers_a)

    dp_rows = db_query("SELECT low_price, high_price, limit_up FROM daily_prices WHERE stock_id=? AND trade_date=?", [STOCK_ID, START_DATE])
    limit_up_ah = _round_to_tick(float(dp_rows[0]["limit_up"])) if dp_rows else 100.0
    low_price_ah = _round_to_tick(float(dp_rows[0]["low_price"])) if dp_rows else 100.0

    phase_after_buy = None
    r = client.post(f"/saves/{save_id_ah}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": limit_up_ah, "quantity": 1}, headers=headers_a)
    if r.status_code == 201:
        order_id_buy = r.json()["order_id"]
        r_adv = client.post(f"/saves/{save_id_ah}/advance", headers=headers_a)
        phase_after_buy = r_adv.json().get("current_phase") if r_adv.status_code == 200 else None

        txn_rows = db_query("SELECT exec_price, fee, tax FROM stock_transactions WHERE order_id=?", [order_id_buy])
        atxn_rows = db_query("SELECT amount, balance_after FROM account_transactions WHERE save_id=? AND change_type='BUY' ORDER BY seq DESC LIMIT 1", [save_id_ah])

        if txn_rows and atxn_rows:
            exec_price = float(txn_rows[0]["exec_price"])
            fee = float(txn_rows[0]["fee"])
            tax = float(txn_rows[0]["tax"])
            amount = float(atxn_rows[0]["amount"])
            balance_after = float(atxn_rows[0]["balance_after"])

            principal = round(exec_price * 1 * 1000)
            expected_fee = max(20, math.floor(principal * 0.001425))

            check(ah_names[0], fee == int(fee), f"fee={fee}")
            check(ah_names[1], fee == expected_fee, f"fee={fee} expected={expected_fee} principal={principal}")
            check(ah_names[2], tax == 0, f"tax={tax}")
            check(ah_names[3], amount == int(amount) and amount == principal + fee, f"amount={amount} expected={principal + fee}")
            check(ah_names[4], balance_after == int(balance_after) and balance_after == 1000000 - amount, f"balance_after={balance_after} expected={1000000 - amount}")
        else:
            for name in ah_names[:5]:
                record(name, False, f"未找到成交紀錄: stock_transactions={txn_rows} account_transactions={atxn_rows}")
    else:
        for name in ah_names[:5]:
            record(name, False, f"下單失敗: {r.status_code}: {r.text}")

    if phase_after_buy == "INTRADAY":
        r = client.post(f"/saves/{save_id_ah}/orders", json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "SELL", "price": low_price_ah, "quantity": 1}, headers=headers_a)
        if r.status_code == 201:
            order_id_sell = r.json()["order_id"]
            client.post(f"/saves/{save_id_ah}/advance", headers=headers_a)

            txn_rows = db_query("SELECT exec_price, fee, tax FROM stock_transactions WHERE order_id=?", [order_id_sell])
            atxn_rows = db_query("SELECT amount, balance_after FROM account_transactions WHERE save_id=? AND change_type='SELL' ORDER BY seq DESC LIMIT 1", [save_id_ah])

            if txn_rows and atxn_rows:
                exec_price = float(txn_rows[0]["exec_price"])
                fee = float(txn_rows[0]["fee"])
                tax = float(txn_rows[0]["tax"])
                amount = float(atxn_rows[0]["amount"])

                principal = round(exec_price * 1 * 1000)
                expected_fee = max(20, math.floor(principal * 0.001425))
                expected_tax = math.floor(principal * 0.003)
                proceeds = principal - fee - tax

                check(ah_names[5], fee == int(fee) and tax == int(tax), f"fee={fee} tax={tax}")
                check(ah_names[6], fee == expected_fee, f"fee={fee} expected={expected_fee} principal={principal}")
                check(ah_names[7], tax == expected_tax, f"tax={tax} expected={expected_tax} principal={principal}")
                check(ah_names[8], amount == int(amount) and amount == proceeds, f"amount={amount} expected={proceeds}")
            else:
                for name in ah_names[5:9]:
                    record(name, False, f"未找到成交紀錄: stock_transactions={txn_rows} account_transactions={atxn_rows}")
        else:
            for name in ah_names[5:9]:
                record(name, False, f"下單失敗: {r.status_code}: {r.text}")
    else:
        for name in ah_names[5:9]:
            record(name, False, f"AH1~AH5 setup 未能讓 BUY 成交並推進至 INTRADAY（phase_after_buy={phase_after_buy}）")

    r = client.get(f"/saves/{save_id_ah}", headers=headers_a)
    if r.status_code == 200:
        body = r.json()
        sb = body.get("savings_balance")
        tb = body.get("trading_balance")
        check(
            ah_names[9],
            isinstance(sb, (int, float)) and isinstance(tb, (int, float)) and sb == int(sb) and tb == int(tb),
            f"savings_balance={sb} trading_balance={tb}",
        )
    else:
        record(ah_names[9], False, f"{r.status_code}: {r.text}")

    r = client.post(f"/saves/{save_id_ah}/accounts/transfer", content='{"direction": "savings_to_trading", "amount": 100.5}', headers={**headers_a, "Content-Type": "application/json"})
    check(ah_names[10], r.status_code == 422, f"{r.status_code}: {r.text}")

    client.delete(f"/saves/{save_id_ah}", headers=headers_a)


@pytest.fixture(scope="session")
def flow(client):
    results = {}

    def check(name, cond, detail=""):
        results[name] = (bool(cond), detail)

    account_a = f"sectest_{random_suffix()}"
    account_b = f"sectest_{random_suffix()}"
    password = "test1234"

    session_a = register_and_login(client, account_a, password)
    session_b = register_and_login(client, account_b, password)
    assert session_a, "無法登入 user A"
    assert session_b, "無法登入 user B"

    headers_a = {"X-Session-Id": session_a}
    headers_b = {"X-Session-Id": session_b}

    r = client.post("/saves", json={"save_name": f"sec_{account_a}", "start_date": START_DATE, "initial_funds": 1000000}, headers=headers_a)
    assert r.status_code == 201, f"user A create save failed: {r.status_code}: {r.text}"
    save_id_a = r.json()["save_id"]

    try:
        _run_checks(client, account_a, account_b, password, save_id_a, headers_a, headers_b, check)
    finally:
        db_query("DELETE FROM save_files WHERE user_id IN (SELECT user_id FROM users WHERE account IN (?, ?))", [account_a, account_b])
        db_query("DELETE FROM users WHERE account IN (?, ?)", [account_a, account_b])

    yield results


# ── 動態產生 test_<ID> 函式 ──────────────────────────────────────────

_AH_NAMES = [
    "AH1. BUY stock_transactions.fee 為整數（無小數部分）",
    "AH2. BUY 手續費計算正確（floor(本金*0.1425%)，最低 20 元）",
    "AH3. BUY 不收證交稅，stock_transactions.tax = 0",
    "AH4. BUY account_transactions.amount 為整數，且 = 本金 + 手續費",
    "AH5. BUY account_transactions.balance_after 為整數，且 = 扣款後餘額",
    "AH6. SELL stock_transactions.fee / tax 皆為整數",
    "AH7. SELL 手續費計算正確（floor(本金*0.1425%)，最低 20 元）",
    "AH8. SELL 證交稅計算正確（floor(本金*0.3%)）",
    "AH9. SELL account_transactions.amount 為整數，且 = 本金 - 手續費 - 證交稅",
    "AH10. GET /saves/{id} savings_balance/trading_balance 為整數值（無小數餘數）",
    "AH11. 轉帳 amount 帶小數（100.5）-> 422",
]

_CHECK_NAMES = [
    "A1. user B GET user A's save -> 403/404",
    "A2. user B place order on user A's save -> 403/404",
    "A3. user B DELETE user A's save -> 403/404",
    "A4. user B GET user A's holdings -> 403/404",
    "A5. user B GET user A's watchlist -> 403/404",
    "A6. user B GET user A's orders -> 403/404",
    "A7. user B DELETE user A's order -> 403/404",
    "B1. old session invalidated after re-login -> 401",
    "C1. register with empty account/password -> 400",
    "C2. transfer negative amount -> 400",
    "C3. order quantity <= 0 -> 422",
    "C4. LIMIT price violates tick size -> 4xx",
    "C5. create save with initial_funds = -100 -> 400",
    "C6. create save with initial_funds = 2000000 -> 400",
    "Q1. search stocks with SQL injection payload -> 200 (no 500)",
    "Q2. place order with SQL injection stock_id -> 404 (no 500)",
    "D1. /stocks/{id}/prices without save_id is rejected (cannot bypass temporal isolation)",
    "E1. 404 error body does not leak SQL/schema details",
    "F1. OPTIONS preflight includes Access-Control-Allow-Origin",
    "G1. sql-api /query requires authentication",
    "H1. users table has a session expiry column",
    "H2. session used from a different source IP -> 401",
    "H3. session still works from the original source IP",
    "H4. session still works from a different IP in the same /24 (DHCP)",
    "H5. session still works when a follow-up request reports IPv6 loopback (::1)",
    "H6. session logged in from ::1 still works from IPv4 loopback afterwards",
    "H7. IPv4-mapped IPv6 address from a genuinely different subnet -> 401",
    "I1. repeated failed logins trigger rate limiting (429)",
    "J1. concurrent /advance calls only advance phase once",
    "K1. concurrent transfers do not produce duplicate account_transactions.seq",
    "L1. GET /accounts/history?limit=1 returns at most 1 row",
    "M1. /stocks/{id}/prices?interval=week returns aggregated weekly data",
    "N1. PATCH /saves/{id}/finish marks save as FINISHED",
    "O1. app/dependencies.py configures an httpx timeout for sql-api calls",
    "R1. GET /saves/{id} numeric fields are JSON numbers, not strings",
    "R2. GET /stocks/{id}/prices numeric fields are JSON numbers, not strings",
    "S1. GET /saves/{id} current_trade_date is 'YYYY-MM-DD'",
    "S2. GET /stocks/{id}/prices trade_date is 'YYYY-MM-DD'",
    "T1. /docs and /openapi.json are accessible",
    "U1. forged order_id/status/exec_price/save_id in body are ignored",
    "U2. place order with order_type='HACK' -> 400",
    "U3. place order with side='HACK' -> 400",
    "U4. transfer with direction='HACK' -> 400",
    "U5. place order with quantity=1.5 -> 422",
    "U6. place order with negative price -> 4xx",
    "P1. place order with empty body {} -> 422",
    "P2. place order with malformed JSON body -> 4xx (not 500)",
    "P3. GET /saves/{non-integer} -> 422",
    "P4. unknown route -> 404",
    "P5. unsupported method PUT /saves/{id} -> 405",
    "V1. order with quantity=10^9 -> 4xx (not 500)",
    "V2. order with price=1e308 -> 4xx (not 500)",
    "V3. order with 500-char stock_id -> 404 (not 500)",
    "V4. search /stocks?q= with 5000-char query -> 200 (not 500)",
    "V5. create save with 250+ char save_name -> not 500",
    "W1. GET /saves/{nonexistent} -> 404",
    "W2. order on nonexistent stock_id -> 404",
    "W3. SELL order exceeding holdings -> 400",
    "W4. place order while phase=CLOSED -> 400",
    "W5. place order / advance on BANKRUPT save -> 400",
    "W6. place order / advance on FINISHED save -> 400",
    "W7. cancel an already-cancelled order -> 400",
    "W8. create save beyond MAX_ACTIVE_SAVES(5) -> 400",
    "W9. create save with duplicate name -> 409",
    "X1. request without X-Session-Id header -> 401/422",
    "X2. X-Session-Id with SQL injection payload -> 401 (not 500)",
    "X3. empty X-Session-Id -> 401/422",
    "X4. extremely long X-Session-Id (10000 chars) -> 401 (not 500)",
    "Y1. register with 60-char account (> VARCHAR(50)) -> 400",
    "Y2. login with oversized X-Forwarded-For (200 chars, no comma) -> 200 (not 500)",
    "Y2b. stored session_ip is truncated to <= 45 chars",
    "Z1. transfer amount=NaN -> 422 (not 500 / data corruption)",
    "Z2. transfer amount=Infinity -> 4xx (not 500)",
    "Z3. place LIMIT order with price=NaN -> 422 (not 500)",
    "Z4. place LIMIT order with price=Infinity -> 4xx (not 500)",
    "Z5. create save with initial_funds=NaN -> 422 (not 500)",
    "Z6. save balances remain finite numbers after rejected NaN requests",
    "Z7. place order with 400-digit quantity -> 422 (not 500)",
    "AA1. concurrent cancel-order vs /advance settlement do not produce inconsistent state",
    "AB1. concurrent double-cancel of the same PENDING order -> exactly one success",
    "AB2. concurrent SELL orders do not bypass holdings check (oversell race)",
    "AB3. concurrent duplicate registration with the same account does not create duplicate users / 500",
    "AC1. concurrent finish vs advance do not leave save status inconsistent",
    "AE1. concurrent create-save requests do not bypass MAX_ACTIVE_SAVES limit",
] + [
    f"AD{i + 1}. random concurrent actions do not break invariants" for i in range(10)
] + [
    f"AF{i + 1}. concurrent finish vs advance (advancing lock) do not break invariants" for i in range(10)
] + [
    AG1_NAME,
] + _AH_NAMES


def _make_check_test(name):
    def _test(flow):
        ok, detail = flow[name]
        assert ok, detail
    _test.__name__ = "test_" + re.sub(r"\W", "_", name.split(".", 1)[0])
    return _test


for _name in _CHECK_NAMES:
    _fn = _make_check_test(_name)
    globals()[_fn.__name__] = _fn
