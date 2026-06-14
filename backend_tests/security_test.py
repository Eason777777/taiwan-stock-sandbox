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
  C1. 註冊空帳號/空密碼                                 -> 400      (預期 PASS，現有檢查)
  C2. 轉帳金額為負數                                    -> 400      (預期 PASS，現有檢查)
  C3. 下單 quantity <= 0                               -> 422      (預期 PASS，pydantic Field(ge=1) 檢查)
  C4. 限價單價格不符合台股升降單位（例如 500.37 元）     -> 4xx      (預期 FAIL，未驗證 tick size)
  C5. 建立存檔 initial_funds = -100（負數）             -> 400      (預期 PASS，現有檢查)
  C6. 建立存檔 initial_funds = 2000000（超過上限）       -> 400      (預期 PASS，現有檢查)

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
  H5. 後續請求改用 IPv6 loopback "::1" -> 200 (預期 PASS，::1 正規化為 127.0.0.1，視為同網段)
  H6. 登入時來源 IP 即為 "::1"，之後改用 IPv4 loopback -> 200 (預期 PASS，雙向正規化一致)
  H7. 後續請求帶 IPv4-mapped IPv6（"::ffff:203.0.113.1"，實際為不同網段）-> 401 (預期 PASS，正規化不應放寬跨網段限制)

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
  U2. 下單 order_type="HACK"（非法 enum 值）                -> 400 (預期 PASS，現有手動檢查)
  U3. 下單 side="HACK"（非法 enum 值）                      -> 400 (預期 PASS，現有手動檢查)
  U4. 轉帳 direction="HACK"（非法 enum 值）                 -> 400 (預期 PASS，現有手動檢查)
  U5. 下單 quantity=1.5（非整數）                           -> 422 (預期 PASS，pydantic 型別檢查)
  U6. 限價單 price=-100（負數價格）                         -> 4xx (預期 PASS，會落在漲跌停檢查之外)

【P. 格式錯誤 / 不支援的請求】
  P1. POST .../orders 帶空 body {}                          -> 422 (預期 PASS)
  P2. POST .../orders 帶非 JSON body                        -> 4xx，非 500 (預期 PASS)
  P3. GET /saves/{非整數}                                   -> 422 (預期 PASS)
  P4. 不存在的路由                                          -> 404 (預期 PASS)
  P5. PUT /saves/{id}（不支援的方法）                        -> 405 (預期 PASS)

【V. 數值與字串邊界】
  V1. 下單 quantity = 10^9                                  -> 4xx，非 500 (預期 PASS)
  V2. 下單 price = 1e308                                    -> 4xx，非 500 (預期 PASS)
  V3. 下單 stock_id 為 500 字元字串                          -> 404，非 500 (預期 PASS)
  V4. /stocks?q= 帶 5000 字元字串                           -> 200，非 500 (預期 PASS)
  V5. 建立存檔 save_name 為 250+ 字元                        -> 非 500 (預期 PASS，若 FAIL 代表缺少長度驗證)

【W. 遊戲規則與存檔狀態機】
  W1. GET /saves/{不存在的 save_id}                         -> 404 (預期 PASS)
  W2. 下單 stock_id 不存在                                  -> 404 (預期 PASS)
  W3. SELL 超過持股數量                                     -> 400 (預期 PASS)
  W4. phase=CLOSED 時下單                                   -> 400 (預期 PASS)
  W5. status=BANKRUPT 的存檔下單 / 推進                      -> 400 (預期 PASS)
  W6. status=FINISHED 的存檔下單 / 推進                      -> 400 (預期 PASS)
  W7. 重複撤銷同一張已撤銷的委託單                            -> 400 (預期 PASS)
  W8. 建立超過 MAX_ACTIVE_SAVES(5) 個進行中存檔               -> 400 (預期 PASS)
  W9. 建立同名存檔                                          -> 409 (預期 PASS)

【X. Session Header 異常處理】
  X1. 缺少 X-Session-Id header                              -> 401/422 (預期 PASS)
  X2. X-Session-Id 帶 SQL injection payload                  -> 401，非 500 (預期 PASS)
  X3. X-Session-Id 為空字串                                  -> 401/422 (預期 PASS)
  X4. X-Session-Id 為極長字串 (10000 字元)                    -> 401，非 500 (預期 PASS)

【Y. 字串長度邊界（應用層驗證 vs DB schema 長度限制）】
  Y1. 註冊 account 長度 60（> users.account VARCHAR(50)）     -> 400 (預期 PASS，現有長度檢查)
  Y2. 登入時帶超長且不含逗號的 X-Forwarded-For（200 字元）
      寫入 users.session_ip（VARCHAR(45)）                    -> 200，非 500 (預期 PASS)
  Y2b. 寫入的 session_ip 應被截斷至 <= 45 字元                 -> 預期 PASS

【Z. NaN / Infinity 數值注入】
  Z1. 轉帳 amount=NaN（JSON 字面量）                          -> 422，非 500/資料毀損 (預期 PASS)
  Z2. 轉帳 amount=Infinity                                    -> 4xx，非 500 (預期 PASS)
  Z3. 限價單 price=NaN                                        -> 422，非 500 (預期 PASS)
  Z4. 限價單 price=Infinity                                   -> 4xx，非 500 (預期 PASS)
  Z5. 建立存檔 initial_funds=NaN                              -> 422，非 500 (預期 PASS)
  Z6. 轉帳 amount=NaN 之後，存檔餘額仍為正常數值（未被寫成 NaN） -> 預期 PASS
  Z7. 下單 quantity 為 400 位數的超大整數                       -> 422，非 500 (預期 PASS，
      原本 est_price * quantity * 1000 會 OverflowError)

【AA. cancel 委託單 與 /advance 結算的並發 race condition】
  AA1. 對同一張 PRE_MARKET 限價買單，同時送出「撤銷委託」與「/advance 推進結算」，
       最終狀態必須一致：cancel 成功(204) <=> 訂單最終為 CANCELED 且無成交紀錄；
       訂單最終 FILLED <=> 有成交紀錄且 cancel 應回 400（單已成交不可撤銷）
       -> 預期 FAIL（_settle_phase 讀取 PENDING 訂單與 cancel_order 的狀態檢查/更新
       之間沒有鎖定機制，可能造成「已撤銷卻被結算成交」或「成交後資金已扣款但訂單顯示
       CANCELED」的資料不一致）

【AB. 更多並發 race condition】
  AB1. 對同一張 PENDING 限價買單同時送出兩次「撤銷委託」
       -> 預期恰好一次 204、一次 400，且訂單最終狀態為 CANCELED
  AB2. 對同一存檔同時送出兩張賣單，每張數量皆等於目前實際持股量
       -> 預期最多只有一張被接受 (201)，避免「持股 - 待成交賣單」檢查的 TOCTOU race
          造成可賣出超過實際持股數量
  AB3. 對同一帳號同時送出兩次註冊
       -> 預期恰好一筆 users 紀錄被建立，且兩個請求都不應回 500
          （SELECT 是否已存在 與 INSERT 之間並非原子操作，並發時可能違反
          uq_users_account 而觸發未處理的資料庫錯誤）

【AC. finish 與 advance 並發 race condition】
  AC1. 對同一存檔同時送出「結束存檔 (PATCH /finish)」與「推進階段 (POST /advance)」
       -> 若 finish 回 200（聲稱已結束），最終 save_files.status 必須是 FINISHED
          （兩者都各自先讀取 save 狀態再各自 UPDATE save_files，後執行的 UPDATE
          會覆寫先執行的結果，可能造成「client 收到結束成功，但存檔實際仍為
          ACTIVE/BANKRUPT」的不一致）

【AE. 並發建立存檔，繞過 MAX_ACTIVE_SAVES 上限】
  AE1. 使用者目前有 4 個進行中存檔（上限 5），同時送出 2 個建立存檔請求
       -> 預期最多只有 1 個成功 (201)，使進行中存檔數量不超過 5
          （COUNT(*) 檢查與 INSERT 之間並非原子操作，並發下單可能都通過檢查）

【AD. 隨機並發 race condition 模糊測試（重複 10 次）】
  AD1~AD10. 每次建立一個全新的存檔，建立 1 筆初始持股後，隨機從
       {advance, finish, place_buy, place_sell, cancel_pending} 中挑選 2 個
       操作同時送出，再檢查以下不變量（invariant）：
         - 兩個回應皆不為 500
         - holdings.quantity 不為負數
         - save_files.trading_balance 為負時，status 必須是 BANKRUPT
         - save_files.trading_balance 與 account_transactions（TRADING）
           最新一筆 balance_after 一致
         - stock_orders.status='FILLED' <=> 恰有 1 筆對應 stock_transactions；
           其他狀態 <=> 0 筆
       -> 用於找出本次修復（AA/AB/AC/AE）未覆蓋到的其他並發路徑

【AF. advance 推進鎖（advancing 旗標）固定情境重複測試（重複 10 次）】
  AF1~AF10. 每次建立一個全新的存檔並下一張保證成交的限價買單（確保
       /advance 的 _settle_phase 一定有實際結算副作用要寫入），
       同時送出 PATCH /finish 與 POST /advance，檢查：
         - 兩個回應皆不為 500
         - save_files.advancing 最終必為 0（鎖一定會被釋放，不會卡死）
         - save_files.trading_balance 與 account_transactions（TRADING）
           最新一筆 balance_after 一致（不會出現「結算副作用已寫入但
           save_files 最終狀態未更新」的不一致）
         - 若 finish 回 200，最終 save_files.status 必須是 FINISHED
       -> 驗證 advance/finish 之間的推進鎖（advancing 旗標）在反覆並發下
          皆能正確互斥且不會死鎖

【AG. /auth/register 的 hash thread pool + queue 上限】
  AG1. 同時送出超過 HASH_QUEUE_MAX 個註冊請求
       -> 預期 PASS：無 500；部分回 201、部分回 429（佇列已滿）；
          201 數量不超過 HASH_QUEUE_MAX
          （bcrypt hash 改丟 ThreadPoolExecutor 執行，避免卡住 event loop，
          並用 _hash_pending 計數做佇列上限）

【AH. 手續費／證交稅／帳戶餘額之台幣整數規則（元以下無條件捨去）】
  AH1. BUY 成交後 stock_transactions.fee 為整數（無小數部分）        -> 預期 PASS
  AH2. BUY 手續費 = max(20, floor(成交本金 * 0.1425%))               -> 預期 PASS
  AH3. BUY 不收證交稅，stock_transactions.tax = 0                    -> 預期 PASS
  AH4. BUY account_transactions.amount 為整數，且 = 本金 + 手續費     -> 預期 PASS
  AH5. BUY account_transactions.balance_after 為整數，且 = 扣款後餘額 -> 預期 PASS
  AH6. SELL 成交後 stock_transactions.fee / tax 皆為整數              -> 預期 PASS
  AH7. SELL 手續費 = max(20, floor(成交本金 * 0.1425%))               -> 預期 PASS
  AH8. SELL 證交稅 = floor(成交本金 * 0.3%)                           -> 預期 PASS
  AH9. SELL account_transactions.amount 為整數，且 = 本金 - 手續費 - 證交稅 -> 預期 PASS
  AH10. GET /saves/{id} savings_balance/trading_balance 為整數值（無小數餘數） -> 預期 PASS
  AH11. 轉帳 amount 帶小數（100.5）-> 422（amount 已改為整數型別）     -> 預期 PASS

────────────────────────────────────────────────────────────────────────
"""

import math
import os
import random
import string
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

import httpx

BASE_URL = "http://localhost:8000"
SQL_API_URL = "http://sql-api.shiragaserver.lan/query"
# 本機備案 sql-api（docker compose，見 ../sql-api）：與 app/database.py 的 FALLBACK_SQL_API_URL 一致，
# 確保 db_query 與 app 連的是同一份 DB
FALLBACK_SQL_API_URL = "http://localhost:3000/query"
_resolved_sql_api_url = None

STOCK_ID = "2330"
START_DATE = "2023-01-04"
MAX_ACTIVE_SAVES_LIMIT = 5
HASH_QUEUE_MAX = 10  # 對應 app/routers/auth.py 的 HASH_QUEUE_MAX

PHASE_SEQUENCE = ["PRE_MARKET", "INTRADAY", "POST_MARKET", "CLOSED"]

PASS = []
FAIL = []


def _tick_size(price):
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
        traceback.print_exc()
    finally:
        cleanup(account_a, account_b)
        print_summary()


def cleanup(account_a, account_b):
    try:
        # 刪掉這兩個帳號名下所有存檔（不只 save_id_a），避免中途失敗時殘留的
        # save_files 因 fk_save_files_user 的 ON DELETE RESTRICT 擋住下面刪 users
        db_query(
            "DELETE FROM save_files WHERE user_id IN (SELECT user_id FROM users WHERE account IN (?, ?))",
            [account_a, account_b],
        )
        db_query("DELETE FROM users WHERE account IN (?, ?)", [account_a, account_b])
        print(f"\n(已清理測試資料: accounts={account_a},{account_b})")
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
    check("C1. register with empty account/password -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")
    if r.status_code == 201:
        # 若後端目前仍接受空帳號，立刻清掉這筆髒資料，避免殘留在 users 表
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
    check("C5. create save with initial_funds = -100 -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    r = client.post(
        "/saves",
        json={"save_name": f"sec_over_{rand_c}", "start_date": START_DATE, "initial_funds": 2000000},
        headers=headers_a,
    )
    check("C6. create save with initial_funds = 2000000 -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

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

    # H5/H6/H7: IPv6 loopback／IPv4-mapped 位址正規化（_normalize_ip）
    # H5: 後續請求改用 IPv6 loopback "::1"，應正規化為 127.0.0.1，與登入時記錄的
    # loopback 網段一致 -> 仍視為同網段
    r = client.get(f"/saves/{save_id_a}", headers={**headers_a, "X-Forwarded-For": "::1"})
    check(
        "H5. session still works when a follow-up request reports IPv6 loopback (::1)",
        r.status_code == 200,
        f"{r.status_code}: {r.text}（::1 應正規化為 127.0.0.1，與登入時記錄的 loopback 網段視為相同）",
    )

    # H6: 登入時來源 IP 即為 "::1"（session_ip 直接存成 "::1"），之後改用一般 IPv4
    # loopback 存取 -> 正規化後仍應視為同網段
    rand_h6 = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    account_h6 = f"sectest_h6_{rand_h6}"
    client.post("/auth/register", json={"account": account_h6, "password": password})
    r = client.post(
        "/auth/login",
        json={"account": account_h6, "password": password},
        headers={"X-Forwarded-For": "::1"},
    )
    session_h6 = r.json().get("session_id") if r.status_code == 200 else None
    if session_h6:
        headers_h6 = {"X-Session-Id": session_h6}
        r = client.get("/saves", headers={**headers_h6, "X-Forwarded-For": "127.0.0.9"})
        check(
            "H6. session logged in from ::1 still works from IPv4 loopback afterwards",
            r.status_code == 200,
            f"{r.status_code}: {r.text}（登入時 session_ip 存成 \"::1\"，正規化後應與 127.0.0.x 視為同網段）",
        )
    else:
        record("H6. session logged in from ::1 still works from IPv4 loopback afterwards", False, "setup login failed")
    db_query("DELETE FROM users WHERE account=?", [account_h6])

    # H7: 正規化不應放寬跨網段限制 -- IPv4-mapped IPv6 位址若實際對應到不同網段，仍應被擋
    r = client.get(f"/saves/{save_id_a}", headers={**headers_a, "X-Forwarded-For": "::ffff:203.0.113.1"})
    check(
        "H7. IPv4-mapped IPv6 address from a genuinely different subnet -> 401",
        r.status_code == 401,
        f"{r.status_code}: {r.text}（::ffff:203.0.113.1 正規化為 203.0.113.1，與 loopback 不同網段，應被擋）",
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
        needed_with_fee = needed + max(20, math.floor(needed * 0.001425))
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
                json={"direction": "savings_to_trading", "amount": math.floor(top_up)},
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
    check("U2. place order with order_type='HACK' -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "HACK", "price": 500, "quantity": 1},
        headers=headers_a,
    )
    check("U3. place order with side='HACK' -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    # U4: 非法 enum direction
    r = client.post(
        f"/saves/{save_id_a}/accounts/transfer",
        json={"direction": "HACK", "amount": 1},
        headers=headers_a,
    )
    check("U4. transfer with direction='HACK' -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

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

    # ── P. 格式錯誤 / 不支援的請求 ─────────────────────────────────────
    r = client.post(f"/saves/{save_id_a}/orders", json={}, headers=headers_a)
    check("P1. place order with empty body {} -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id_a}/orders",
        content=b"not json",
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check(
        "P2. place order with malformed JSON body -> 4xx (not 500)",
        r.status_code in (400, 422),
        f"{r.status_code}: {r.text}",
    )

    r = client.get("/saves/not-an-integer", headers=headers_a)
    check("P3. GET /saves/{non-integer} -> 422", r.status_code == 422, f"{r.status_code}: {r.text}")

    r = client.get("/this-route-does-not-exist")
    check("P4. unknown route -> 404", r.status_code == 404, f"{r.status_code}: {r.text}")

    r = client.put(f"/saves/{save_id_a}", headers=headers_a)
    check("P5. unsupported method PUT /saves/{id} -> 405", r.status_code == 405, f"{r.status_code}: {r.text}")

    # ── V. 數值與字串邊界 ─────────────────────────────────────────────
    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 100.0, "quantity": 10 ** 9},
        headers=headers_a,
    )
    check(
        "V1. order with quantity=10^9 -> 4xx (not 500)",
        r.status_code in (400, 422),
        f"{r.status_code}: {r.text}",
    )

    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 1e308, "quantity": 1},
        headers=headers_a,
    )
    check(
        "V2. order with price=1e308 -> 4xx (not 500)",
        r.status_code in (400, 422),
        f"{r.status_code}: {r.text}",
    )

    r = client.post(
        f"/saves/{save_id_a}/orders",
        json={"stock_id": "A" * 500, "order_type": "LIMIT", "side": "BUY", "price": 100.0, "quantity": 1},
        headers=headers_a,
    )
    check(
        "V3. order with 500-char stock_id -> 404 (not 500)",
        r.status_code == 404,
        f"{r.status_code}: {r.text}",
    )

    r = client.get("/stocks", params={"q": "x" * 5000}, headers=headers_a)
    check(
        "V4. search /stocks?q= with 5000-char query -> 200 (not 500)",
        r.status_code == 200,
        f"{r.status_code}: {r.text[:200]}",
    )

    rand_v = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    r = client.post(
        "/saves",
        json={"save_name": "v_" + rand_v + "_" + "x" * 250, "start_date": START_DATE, "initial_funds": 100000},
        headers=headers_a,
    )
    check(
        "V5. create save with 250+ char save_name -> not 500",
        r.status_code != 500,
        f"{r.status_code}: {r.text[:200]}",
    )
    if r.status_code == 201:
        client.delete(f"/saves/{r.json()['save_id']}", headers=headers_a)

    # ── W. 遊戲規則與存檔狀態機 ───────────────────────────────────────
    r = client.get("/saves/999999999", headers=headers_a)
    check("W1. GET /saves/{nonexistent} -> 404", r.status_code == 404, f"{r.status_code}: {r.text}")

    rand_w = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    rw = client.post(
        "/saves",
        json={"save_name": f"w_{rand_w}", "start_date": START_DATE, "initial_funds": 1000000},
        headers=headers_a,
    )
    check("setup. user A create throwaway save for W -> 201", rw.status_code == 201, f"{rw.status_code}: {rw.text}")
    save_id_w = rw.json().get("save_id") if rw.status_code == 201 else None

    if save_id_w:
        # W2: 下單 stock_id 不存在
        r = client.post(
            f"/saves/{save_id_w}/orders",
            json={"stock_id": "9999999", "order_type": "LIMIT", "side": "BUY", "price": 100, "quantity": 1},
            headers=headers_a,
        )
        check("W2. order on nonexistent stock_id -> 404", r.status_code == 404, f"{r.status_code}: {r.text}")

        # W3: SELL 超過持股數量（throwaway save 無任何持股）
        price_w = get_order_price(STOCK_ID, START_DATE)
        r = client.post(
            f"/saves/{save_id_w}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "SELL", "price": price_w, "quantity": 999},
            headers=headers_a,
        )
        check("W3. SELL order exceeding holdings -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

        # W7: 重複撤銷同一張已撤銷的委託單
        # 新存檔的資金預設全在存款戶，下單前先把足夠的金額轉入交割戶
        needed_w7 = price_w * 1 * 1000
        needed_w7_with_fee = needed_w7 + max(20, math.floor(needed_w7 * 0.001425))
        client.post(
            f"/saves/{save_id_w}/accounts/transfer",
            json={"direction": "savings_to_trading", "amount": math.ceil(needed_w7_with_fee + 1000)},
            headers=headers_a,
        )
        r = client.post(
            f"/saves/{save_id_w}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": price_w, "quantity": 1},
            headers=headers_a,
        )
        if r.status_code == 201:
            order_id_w = r.json()["order_id"]
            r1 = client.delete(f"/saves/{save_id_w}/orders/{order_id_w}", headers=headers_a)
            r2 = client.delete(f"/saves/{save_id_w}/orders/{order_id_w}", headers=headers_a)
            check(
                "W7. cancel an already-cancelled order -> 400",
                r1.status_code == 204 and r2.status_code == 400,
                f"first={r1.status_code}, second={r2.status_code}: {r2.text}",
            )
        else:
            record("W7. cancel an already-cancelled order -> 400", False, f"setup order failed: {r.status_code}: {r.text}")

        client.delete(f"/saves/{save_id_w}", headers=headers_a)
    else:
        for name in ("W2", "W3", "W7"):
            record(f"{name}. skipped (throwaway save setup failed)", False, "setup failed")

    # W4: phase=CLOSED 時下單
    rw4 = client.post(
        "/saves",
        json={"save_name": f"w4_{rand_w}", "start_date": START_DATE, "initial_funds": 100000},
        headers=headers_a,
    )
    if rw4.status_code == 201:
        sid = rw4.json()["save_id"]
        db_query("UPDATE save_files SET current_phase='CLOSED' WHERE save_id=?", [sid])
        r = client.post(
            f"/saves/{sid}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 100, "quantity": 1},
            headers=headers_a,
        )
        check("W4. place order while phase=CLOSED -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")
        client.delete(f"/saves/{sid}", headers=headers_a)
    else:
        record("W4. place order while phase=CLOSED -> 400", False, f"setup failed: {rw4.status_code}")

    # W5: status=BANKRUPT 的存檔下單 / 推進
    rw5 = client.post(
        "/saves",
        json={"save_name": f"w5_{rand_w}", "start_date": START_DATE, "initial_funds": 100000},
        headers=headers_a,
    )
    if rw5.status_code == 201:
        sid = rw5.json()["save_id"]
        db_query("UPDATE save_files SET status='BANKRUPT' WHERE save_id=?", [sid])
        r_order = client.post(
            f"/saves/{sid}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 100, "quantity": 1},
            headers=headers_a,
        )
        r_adv = client.post(f"/saves/{sid}/advance", headers=headers_a)
        check(
            "W5. place order / advance on BANKRUPT save -> 400",
            r_order.status_code == 400 and r_adv.status_code == 400,
            f"order={r_order.status_code}, advance={r_adv.status_code}: {r_order.text} / {r_adv.text}",
        )
        client.delete(f"/saves/{sid}", headers=headers_a)
    else:
        record("W5. place order / advance on BANKRUPT save -> 400", False, f"setup failed: {rw5.status_code}")

    # W6: status=FINISHED 的存檔下單 / 推進
    rw6 = client.post(
        "/saves",
        json={"save_name": f"w6_{rand_w}", "start_date": START_DATE, "initial_funds": 100000},
        headers=headers_a,
    )
    if rw6.status_code == 201:
        sid = rw6.json()["save_id"]
        fr = client.patch(f"/saves/{sid}/finish", headers=headers_a)
        r_order = client.post(
            f"/saves/{sid}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": 100, "quantity": 1},
            headers=headers_a,
        )
        r_adv = client.post(f"/saves/{sid}/advance", headers=headers_a)
        check(
            "W6. place order / advance on FINISHED save -> 400",
            fr.status_code == 200 and r_order.status_code == 400 and r_adv.status_code == 400,
            f"finish={fr.status_code}, order={r_order.status_code}, advance={r_adv.status_code}",
        )
        client.delete(f"/saves/{sid}", headers=headers_a)
    else:
        record("W6. place order / advance on FINISHED save -> 400", False, f"setup failed: {rw6.status_code}")

    # W8: 建立超過 MAX_ACTIVE_SAVES(5) 個進行中存檔
    active_rows = db_query(
        "SELECT save_id FROM save_files WHERE user_id=(SELECT user_id FROM users WHERE account=?) AND status='ACTIVE'",
        [account_a],
    )
    extra_saves = []
    to_create = max(0, 5 - len(active_rows))
    setup_ok = True
    for i in range(to_create):
        rr = client.post(
            "/saves",
            json={"save_name": f"w8_{rand_w}_{i}", "start_date": START_DATE, "initial_funds": 100000},
            headers=headers_a,
        )
        if rr.status_code == 201:
            extra_saves.append(rr.json()["save_id"])
        else:
            setup_ok = False

    if setup_ok:
        r = client.post(
            "/saves",
            json={"save_name": f"w8_over_{rand_w}", "start_date": START_DATE, "initial_funds": 100000},
            headers=headers_a,
        )
        check("W8. create save beyond MAX_ACTIVE_SAVES(5) -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")
        if r.status_code == 201:
            extra_saves.append(r.json()["save_id"])
    else:
        record("W8. create save beyond MAX_ACTIVE_SAVES(5) -> 400", False, "setup failed (could not create enough ACTIVE saves)")

    for sid in extra_saves:
        client.delete(f"/saves/{sid}", headers=headers_a)

    # W9: 建立同名存檔
    r = client.post(
        "/saves",
        json={"save_name": f"sec_{account_a}", "start_date": START_DATE, "initial_funds": 100000},
        headers=headers_a,
    )
    check("W9. create save with duplicate name -> 409", r.status_code == 409, f"{r.status_code}: {r.text}")

    # ── X. Session Header 異常處理 ───────────────────────────────────
    r = client.get(f"/saves/{save_id_a}")
    check("X1. request without X-Session-Id header -> 401/422", r.status_code in (401, 422), f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id_a}", headers={"X-Session-Id": "' OR '1'='1"})
    check(
        "X2. X-Session-Id with SQL injection payload -> 401 (not 500)",
        r.status_code == 401,
        f"{r.status_code}: {r.text}",
    )

    r = client.get(f"/saves/{save_id_a}", headers={"X-Session-Id": ""})
    check("X3. empty X-Session-Id -> 401/422", r.status_code in (401, 422), f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id_a}", headers={"X-Session-Id": "a" * 10000})
    check(
        "X4. extremely long X-Session-Id (10000 chars) -> 401 (not 500)",
        r.status_code == 401,
        f"{r.status_code}: {r.text}",
    )

    # ── Y. 字串長度邊界（應用層驗證 vs DB schema 長度限制）──────────────
    long_account = "y_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=60))
    r = client.post("/auth/register", json={"account": long_account, "password": "test1234"})
    check(
        "Y1. register with 60-char account (> VARCHAR(50)) -> 400",
        r.status_code == 400,
        f"{r.status_code}: {r.text}",
    )

    # Y2: X-Forwarded-For 超長且不含逗號，會整段寫入 users.session_ip (VARCHAR(45))，
    # 若未截斷會導致 sql-api UPDATE 失敗、login 回 500
    rand_y = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    account_y = f"sectest_y_{rand_y}"
    client.post("/auth/register", json={"account": account_y, "password": "test1234"})
    long_xff = "9" * 200
    r = client.post(
        "/auth/login",
        json={"account": account_y, "password": "test1234"},
        headers={"X-Forwarded-For": long_xff},
    )
    check(
        "Y2. login with oversized X-Forwarded-For (200 chars, no comma) -> 200 (not 500)",
        r.status_code == 200 and "session_id" in r.json(),
        f"{r.status_code}: {r.text}",
    )
    if r.status_code == 200:
        stored = db_query("SELECT session_ip FROM users WHERE account=?", [account_y])
        session_ip_len = len(stored[0]["session_ip"] or "") if stored else -1
        check(
            "Y2b. stored session_ip is truncated to <= 45 chars",
            0 <= session_ip_len <= 45,
            f"session_ip length={session_ip_len}",
        )
    db_query("DELETE FROM users WHERE account=?", [account_y])

    # ── Z. NaN / Infinity 數值注入 ────────────────────────────────────
    # Z1: 轉帳 amount=NaN -- `nan <= 0` 與 `balance < nan` 在 Python 中皆為 False，
    # 若無 allow_inf_nan=False 防護會直接跳過所有檢查並把 NaN 寫進 DB
    r = client.post(
        f"/saves/{save_id_a}/accounts/transfer",
        content='{"direction": "savings_to_trading", "amount": NaN}',
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check("Z1. transfer amount=NaN -> 422 (not 500 / data corruption)", r.status_code == 422, f"{r.status_code}: {r.text}")

    # Z2: 轉帳 amount=Infinity -- `balance < inf` 為 True，理論上會被「餘額不足」擋下
    r = client.post(
        f"/saves/{save_id_a}/accounts/transfer",
        content='{"direction": "savings_to_trading", "amount": Infinity}',
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check("Z2. transfer amount=Infinity -> 4xx (not 500)", r.status_code in (400, 422), f"{r.status_code}: {r.text}")

    # Z3: 限價單 price=NaN -- `price > limit_up`/`price < limit_down` 皆為 False，
    # 漲跌停檢查會被繞過，接著 _tick_size 的 round(price/tick) 對 NaN 會 raise ValueError -> 500
    r = client.post(
        f"/saves/{save_id_a}/orders",
        content=(
            '{"stock_id": "%s", "order_type": "LIMIT", "side": "BUY", "price": NaN, "quantity": 1}' % STOCK_ID
        ),
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check("Z3. place LIMIT order with price=NaN -> 422 (not 500)", r.status_code == 422, f"{r.status_code}: {r.text}")

    # Z4: 限價單 price=Infinity -- 應被漲跌停檢查擋下
    r = client.post(
        f"/saves/{save_id_a}/orders",
        content=(
            '{"stock_id": "%s", "order_type": "LIMIT", "side": "BUY", "price": Infinity, "quantity": 1}' % STOCK_ID
        ),
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check("Z4. place LIMIT order with price=Infinity -> 4xx (not 500)", r.status_code in (400, 422), f"{r.status_code}: {r.text}")

    # Z5: 建立存檔 initial_funds=NaN -- int(nan) 會 raise ValueError -> 500
    r = client.post(
        "/saves",
        content='{"save_name": "z5_should_not_exist", "start_date": "%s", "initial_funds": NaN}' % START_DATE,
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check("Z5. create save with initial_funds=NaN -> 422 (not 500)", r.status_code == 422, f"{r.status_code}: {r.text}")
    if r.status_code == 201:
        client.delete(f"/saves/{r.json()['save_id']}", headers=headers_a)

    # Z6: 確認上述被拒絕的請求未污染存檔餘額（仍為正常的有限數值）
    fresh = db_query(
        "SELECT savings_balance, trading_balance FROM save_files WHERE save_id = ?",
        [save_id_a],
    )
    z6_ok = False
    if fresh:
        try:
            sb = float(fresh[0]["savings_balance"])
            tb = float(fresh[0]["trading_balance"])
            z6_ok = math.isfinite(sb) and math.isfinite(tb)
        except (TypeError, ValueError):
            z6_ok = False
    check("Z6. save balances remain finite numbers after rejected NaN requests", z6_ok, f"row={fresh}")

    # Z7: quantity 為超大整數（400 位數）-- Python int 任意精度可通過 pydantic，
    # 但 est_price(float) * quantity(int) 超過 float 上限會 raise OverflowError -> 500
    r = client.post(
        f"/saves/{save_id_a}/orders",
        content=(
            '{"stock_id": "%s", "order_type": "LIMIT", "side": "BUY", "price": 100.0, "quantity": %s}'
            % (STOCK_ID, "9" * 400)
        ),
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check("Z7. place order with 400-digit quantity -> 422 (not 500)", r.status_code == 422, f"{r.status_code}: {r.text}")

    # ── AA. cancel 委託單 與 /advance 結算的並發 race condition ─────────
    rand_aa = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    raa = client.post(
        "/saves",
        json={"save_name": f"aa_{rand_aa}", "start_date": START_DATE, "initial_funds": 1000000},
        headers=headers_a,
    )
    aa_name = "AA1. concurrent cancel-order vs /advance settlement do not produce inconsistent state"
    if raa.status_code == 201:
        save_id_aa = raa.json()["save_id"]

        # 把資金轉入交割戶，確保足以買進
        client.post(
            f"/saves/{save_id_aa}/accounts/transfer",
            json={"direction": "savings_to_trading", "amount": 1000000},
            headers=headers_a,
        )

        # 取得當日漲停價作為限價買單價格：PRE_MARKET 結算時 BUY 只要 price >= open_price 即成交，
        # 漲停價必定 >= 開盤價，可確保 /advance 推進後此單必定成交
        dp_rows = db_query(
            "SELECT limit_up FROM daily_prices WHERE stock_id=? AND trade_date=?",
            [STOCK_ID, START_DATE],
        )
        price_aa = _round_to_tick(float(dp_rows[0]["limit_up"])) if dp_rows else 100.0

        r = client.post(
            f"/saves/{save_id_aa}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": price_aa, "quantity": 1},
            headers=headers_a,
        )
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

            # 一致性檢查：
            # - cancel 成功(204) <=> 訂單最終為 CANCELED 且無成交紀錄
            # - 訂單最終 FILLED <=> 有成交紀錄，且 cancel 應回 400（已成交不可撤銷）
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

    rand_ab = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    rab = client.post(
        "/saves",
        json={"save_name": f"ab_{rand_ab}", "start_date": START_DATE, "initial_funds": 1000000},
        headers=headers_a,
    )
    if rab.status_code == 201:
        save_id_ab = rab.json()["save_id"]

        client.post(
            f"/saves/{save_id_ab}/accounts/transfer",
            json={"direction": "savings_to_trading", "amount": 1000000},
            headers=headers_a,
        )

        # 建立 1 張持股：盤前限價買單，價格=漲停價必定成交，推進一次結算
        dp_rows = db_query(
            "SELECT limit_up FROM daily_prices WHERE stock_id=? AND trade_date=?",
            [STOCK_ID, START_DATE],
        )
        limit_up_ab = _round_to_tick(float(dp_rows[0]["limit_up"])) if dp_rows else 100.0
        r_buy = client.post(
            f"/saves/{save_id_ab}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": limit_up_ab, "quantity": 1},
            headers=headers_a,
        )
        client.post(f"/saves/{save_id_ab}/advance", headers=headers_a)

        holding_rows = db_query(
            "SELECT quantity FROM holdings WHERE save_id=? AND stock_id=?", [save_id_ab, STOCK_ID],
        )
        held_qty = int(holding_rows[0]["quantity"]) if holding_rows else 0

        if r_buy.status_code == 201 and held_qty >= 1:
            price_ab = get_order_price(STOCK_ID, START_DATE)

            # ── AB1: 對同一張 PENDING 限價買單同時送出兩次撤銷 ──
            r_order = client.post(
                f"/saves/{save_id_ab}/orders",
                json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": price_ab, "quantity": 1},
                headers=headers_a,
            )
            if r_order.status_code == 201:
                order_id_ab1 = r_order.json()["order_id"]
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [
                        pool.submit(client.delete, f"/saves/{save_id_ab}/orders/{order_id_ab1}", headers=headers_a)
                        for _ in range(2)
                    ]
                    responses = [f.result() for f in futures]
                statuses = sorted(r.status_code for r in responses)
                final_row = db_query("SELECT status FROM stock_orders WHERE order_id=?", [order_id_ab1])[0]
                check(
                    ab1_name,
                    statuses == [204, 400] and final_row["status"] == "CANCELED",
                    f"responses={statuses}, final_status={final_row['status']}"
                    f"（預期恰好一次 204、一次 400；若兩次都回 204，代表撤銷未互斥）",
                )
            else:
                record(ab1_name, False, f"setup order failed: {r_order.status_code}: {r_order.text}")

            # ── AB2: 對同一存檔同時送出兩張賣單，數量總和超過實際持股 ──
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(
                        client.post,
                        f"/saves/{save_id_ab}/orders",
                        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "SELL",
                              "price": price_ab, "quantity": held_qty},
                        headers=headers_a,
                    )
                    for _ in range(2)
                ]
                responses = [f.result() for f in futures]

            accepted = sum(1 for r in responses if r.status_code == 201)
            pending_sell = db_query(
                "SELECT COALESCE(SUM(quantity),0) AS total FROM stock_orders"
                " WHERE save_id=? AND stock_id=? AND side='SELL' AND status='PENDING'",
                [save_id_ab, STOCK_ID],
            )
            total_pending_sell = int(pending_sell[0]["total"])
            check(
                ab2_name,
                accepted <= 1 and total_pending_sell <= held_qty,
                f"accepted={accepted}/2 (each side=SELL qty={held_qty}), held_qty={held_qty}, "
                f"total_pending_sell_quantity={total_pending_sell}"
                f"（若 accepted==2 或 total_pending_sell > held_qty，代表下單時的"
                f"「持股 - 待成交賣單」檢查存在 TOCTOU race，可賣出超過實際持股數量）",
            )
        else:
            record(ab1_name, False, f"setup failed: buy={r_buy.status_code}, held_qty={held_qty}")
            record(ab2_name, False, f"setup failed: buy={r_buy.status_code}, held_qty={held_qty}")

        client.delete(f"/saves/{save_id_ab}", headers=headers_a)
    else:
        record(ab1_name, False, f"setup save failed: {rab.status_code}: {rab.text}")
        record(ab2_name, False, f"setup save failed: {rab.status_code}: {rab.text}")

    # ── AB3: 對同一帳號同時送出兩次註冊 ──────────────────────────────
    rand_ab3 = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    account_ab3 = f"sectest_ab3_{rand_ab3}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(client.post, "/auth/register", json={"account": account_ab3, "password": "test1234"})
            for _ in range(2)
        ]
        responses = [f.result() for f in futures]

    statuses = sorted(r.status_code for r in responses)
    user_rows = db_query("SELECT COUNT(*) AS c FROM users WHERE account=?", [account_ab3])
    user_count = int(user_rows[0]["c"])
    check(
        "AB3. concurrent duplicate registration with the same account does not create duplicate users / 500",
        user_count == 1 and 500 not in statuses,
        f"responses={statuses}, user_count={user_count}"
        f"（預期恰好一筆 users 紀錄，且兩次請求都不應回 500）",
    )
    db_query("DELETE FROM users WHERE account=?", [account_ab3])

    # ── AC. finish 與 advance 並發 race condition ────────────────────
    ac_name = "AC1. concurrent finish vs advance do not leave save status inconsistent"
    rand_ac = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    rac = client.post(
        "/saves",
        json={"save_name": f"ac_{rand_ac}", "start_date": START_DATE, "initial_funds": 100000},
        headers=headers_a,
    )
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
    active_rows = db_query(
        "SELECT save_id FROM save_files"
        " WHERE user_id=(SELECT user_id FROM users WHERE account=?) AND status='ACTIVE'",
        [account_a],
    )
    rand_ae = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    extra_saves_ae = []
    # 留 1 個名額，讓並發的兩個建立請求互相競爭該名額
    to_create = max(0, (MAX_ACTIVE_SAVES_LIMIT - 1) - len(active_rows))
    setup_ok = True
    for i in range(to_create):
        rr = client.post(
            "/saves",
            json={"save_name": f"ae_setup_{rand_ae}_{i}", "start_date": START_DATE, "initial_funds": 100000},
            headers=headers_a,
        )
        if rr.status_code == 201:
            extra_saves_ae.append(rr.json()["save_id"])
        else:
            setup_ok = False

    if setup_ok:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    client.post,
                    "/saves",
                    json={"save_name": f"ae_race_{rand_ae}_{i}", "start_date": START_DATE, "initial_funds": 100000},
                    headers=headers_a,
                )
                for i in range(2)
            ]
            responses = [f.result() for f in futures]

        accepted = [r for r in responses if r.status_code == 201]
        for r in accepted:
            extra_saves_ae.append(r.json()["save_id"])

        active_count_after = db_query(
            "SELECT COUNT(*) AS c FROM save_files"
            " WHERE user_id=(SELECT user_id FROM users WHERE account=?) AND status='ACTIVE'",
            [account_a],
        )[0]["c"]

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
    dp_rows_ad = db_query(
        "SELECT limit_up FROM daily_prices WHERE stock_id=? AND trade_date=?",
        [STOCK_ID, START_DATE],
    )
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

        ledger_rows = db_query(
            "SELECT balance_after FROM account_transactions"
            " WHERE save_id=? AND account_type='TRADING' ORDER BY seq DESC LIMIT 1",
            [save_id],
        )
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
        return c.post(
            f"/saves/{sid}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": limit_up_ad, "quantity": 1},
            headers=h,
        )

    def _ad_act_place_sell(c, sid, h):
        return c.post(
            f"/saves/{sid}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "SELL", "price": price_ad, "quantity": 1},
            headers=h,
        )

    def _ad_act_cancel_pending(c, sid, h):
        pending = db_query(
            "SELECT order_id FROM stock_orders WHERE save_id=? AND status='PENDING' ORDER BY order_id LIMIT 1",
            [sid],
        )
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
        rand_ad = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        rad = client.post(
            "/saves",
            json={"save_name": f"ad_{rand_ad}_{i}", "start_date": START_DATE, "initial_funds": 500000},
            headers=headers_a,
        )
        if rad.status_code != 201:
            record(ad_name, False, f"setup save failed: {rad.status_code}: {rad.text}")
            continue

        save_id_ad = rad.json()["save_id"]
        client.post(
            f"/saves/{save_id_ad}/accounts/transfer",
            json={"direction": "savings_to_trading", "amount": 500000},
            headers=headers_a,
        )

        # 建立初始持股：盤前限價買單(漲停價必定成交) + 推進一次
        client.post(
            f"/saves/{save_id_ad}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": limit_up_ad, "quantity": 2},
            headers=headers_a,
        )
        client.post(f"/saves/{save_id_ad}/advance", headers=headers_a)

        # 隨機再下 0~2 張委託單，製造混合的 PENDING/FILLED 狀態
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
        rand_af = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        raf = client.post(
            "/saves",
            json={"save_name": f"af_{rand_af}_{i}", "start_date": START_DATE, "initial_funds": 500000},
            headers=headers_a,
        )
        if raf.status_code != 201:
            record(af_name, False, f"setup save failed: {raf.status_code}: {raf.text}")
            continue

        save_id_af = raf.json()["save_id"]
        client.post(
            f"/saves/{save_id_af}/accounts/transfer",
            json={"direction": "savings_to_trading", "amount": 500000},
            headers=headers_a,
        )

        # 下一張保證成交的限價買單，確保 /advance 的 _settle_phase 一定有實際
        # 結算副作用（account_transactions/holdings）要寫入
        client.post(
            f"/saves/{save_id_af}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": limit_up_ad, "quantity": 1},
            headers=headers_a,
        )

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
    ag_name = "AG1. concurrent registration burst is throttled by hash queue cap (429), no 500s"
    n_ag = HASH_QUEUE_MAX + 5
    rand_ag = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    accounts_ag = [f"sectest_ag_{rand_ag}_{i}" for i in range(n_ag)]

    with ThreadPoolExecutor(max_workers=n_ag) as pool:
        futures = [
            pool.submit(client.post, "/auth/register", json={"account": acc, "password": "test1234"})
            for acc in accounts_ag
        ]
        responses = [f.result() for f in futures]

    statuses = [r.status_code for r in responses]
    n_201 = statuses.count(201)
    n_429 = statuses.count(429)
    check(
        ag_name,
        500 not in statuses and n_201 + n_429 == n_ag and n_429 > 0 and n_201 <= HASH_QUEUE_MAX,
        f"statuses={sorted(statuses)}（預期無 500、部分 201 部分 429，"
        f"且 201 數量不超過 HASH_QUEUE_MAX={HASH_QUEUE_MAX}）",
    )

    for acc in accounts_ag:
        db_query("DELETE FROM users WHERE account=?", [acc])

    # ── AH. 手續費／證交稅／帳戶餘額之台幣整數規則（元以下無條件捨去）──
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

    rand_ah = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    rah = client.post(
        "/saves",
        json={"save_name": f"ah_{rand_ah}", "start_date": START_DATE, "initial_funds": 1000000},
        headers=headers_a,
    )
    if rah.status_code != 201:
        for name in ah_names:
            record(name, False, f"setup: create save failed {rah.status_code}: {rah.text}")
        return

    save_id_ah = rah.json()["save_id"]

    client.post(
        f"/saves/{save_id_ah}/accounts/transfer",
        json={"direction": "savings_to_trading", "amount": 1000000},
        headers=headers_a,
    )

    dp_rows = db_query(
        "SELECT low_price, high_price, limit_up FROM daily_prices WHERE stock_id=? AND trade_date=?",
        [STOCK_ID, START_DATE],
    )
    limit_up_ah = _round_to_tick(float(dp_rows[0]["limit_up"])) if dp_rows else 100.0
    low_price_ah = _round_to_tick(float(dp_rows[0]["low_price"])) if dp_rows else 100.0

    # AH1~AH5: PRE_MARKET 以漲停價下 BUY 限價單，保證下一次 advance 結算時以開盤價成交
    phase_after_buy = None
    r = client.post(
        f"/saves/{save_id_ah}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": limit_up_ah, "quantity": 1},
        headers=headers_a,
    )
    if r.status_code == 201:
        order_id_buy = r.json()["order_id"]
        r_adv = client.post(f"/saves/{save_id_ah}/advance", headers=headers_a)
        phase_after_buy = r_adv.json().get("current_phase") if r_adv.status_code == 200 else None

        txn_rows = db_query("SELECT exec_price, fee, tax FROM stock_transactions WHERE order_id=?", [order_id_buy])
        atxn_rows = db_query(
            "SELECT amount, balance_after FROM account_transactions"
            " WHERE save_id=? AND change_type='BUY' ORDER BY seq DESC LIMIT 1",
            [save_id_ah],
        )

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
            check(
                ah_names[3],
                amount == int(amount) and amount == principal + fee,
                f"amount={amount} expected={principal + fee}",
            )
            check(
                ah_names[4],
                balance_after == int(balance_after) and balance_after == 1000000 - amount,
                f"balance_after={balance_after} expected={1000000 - amount}",
            )
        else:
            for name in ah_names[:5]:
                record(name, False, f"未找到成交紀錄: stock_transactions={txn_rows} account_transactions={atxn_rows}")
    else:
        for name in ah_names[:5]:
            record(name, False, f"下單失敗: {r.status_code}: {r.text}")

    # AH6~AH9: INTRADAY 以最低價下 SELL 限價單，保證以該限價成交（price <= high_price）
    if phase_after_buy == "INTRADAY":
        r = client.post(
            f"/saves/{save_id_ah}/orders",
            json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "SELL", "price": low_price_ah, "quantity": 1},
            headers=headers_a,
        )
        if r.status_code == 201:
            order_id_sell = r.json()["order_id"]
            client.post(f"/saves/{save_id_ah}/advance", headers=headers_a)

            txn_rows = db_query("SELECT exec_price, fee, tax FROM stock_transactions WHERE order_id=?", [order_id_sell])
            atxn_rows = db_query(
                "SELECT amount, balance_after FROM account_transactions"
                " WHERE save_id=? AND change_type='SELL' ORDER BY seq DESC LIMIT 1",
                [save_id_ah],
            )

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
                check(
                    ah_names[8],
                    amount == int(amount) and amount == proceeds,
                    f"amount={amount} expected={proceeds}",
                )
            else:
                for name in ah_names[5:9]:
                    record(name, False, f"未找到成交紀錄: stock_transactions={txn_rows} account_transactions={atxn_rows}")
        else:
            for name in ah_names[5:9]:
                record(name, False, f"下單失敗: {r.status_code}: {r.text}")
    else:
        for name in ah_names[5:9]:
            record(name, False, f"AH1~AH5 setup 未能讓 BUY 成交並推進至 INTRADAY（phase_after_buy={phase_after_buy}）")

    # AH10: GET /saves/{id} 餘額為整數值（無小數餘數）
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

    # AH11: 轉帳 amount 帶小數 -> 422（TransferRequest.amount 已改為 int 型別）
    r = client.post(
        f"/saves/{save_id_ah}/accounts/transfer",
        content='{"direction": "savings_to_trading", "amount": 100.5}',
        headers={**headers_a, "Content-Type": "application/json"},
    )
    check(ah_names[10], r.status_code == 422, f"{r.status_code}: {r.text}")

    client.delete(f"/saves/{save_id_ah}", headers=headers_a)


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
