"""
端對端 smoke test，依照 README / docs/report3 規格驗證 API 行為。

用法:
    1. 另開一個 terminal 啟動 server: uvicorn app.main:app --reload
    2. python backend_tests/smoke_test.py

這個腳本對照的是「規格應該長什麼樣子」，不是現在程式碼的樣子。
在修正過程中，跑這個腳本可以看到目前還有哪些步驟是 FAIL，
逐步把 FAIL 變成 PASS 即可。

腳本會：
    - 透過 API 跑一輪完整流程（註冊→登入→建檔→下單→推進→撮合→查詢）
    - 同時直接打 sql-api 查 DB，驗證帳本/持股/委託單狀態是否正確
    - 無論中途是否出錯，最後都會在 finally 區塊清理測試建立的 save_files 與 users 資料
      （帳號名稱固定為 smoketest_xxxxxxxx，方便辨識）

────────────────────────────────────────────────────────────────────────
測試項目清單（共 50 項檢查，依執行順序）
────────────────────────────────────────────────────────────────────────

【0. 健康檢查】
  0.       GET /              伺服器是否啟動、可連線

【1-2. 帳號註冊 / 登入】
  1.       POST /auth/register                註冊新帳號 -> 201
  1b.      POST /auth/register（同帳號）      重複註冊 -> 409
  2a.      POST /auth/login（錯密碼）         -> 401
  2b.      POST /auth/login（正確密碼）       -> 200
  2c.      檢查回應內含 session_id

【3. 建立存檔（POST /saves）】
  3a.      建立存檔 -> 201
  3b.      savings_balance == initial_funds（1,000,000，全部存入存款戶）
  3c.      trading_balance == 0（交割戶初始為 0）
  3d.      status == ACTIVE
  3e.      current_phase == PRE_MARKET（新存檔從盤前開始）
  3f.      current_trade_date == start_date
  3g.      用同樣的 save_name 再建一次 -> 4xx（同名存檔需被拒絕）

【4. 存檔列表 / 單筆查詢（GET /saves, GET /saves/{id}）】
  4a.      GET /saves -> 200
  4b.      列表中包含剛建立的存檔
  4c.      存檔物件包含 total_asset 欄位（總資產，需即時計算）
  4d.      存檔物件包含 cumulative_return 欄位（累積報酬率）
  4e.      GET /saves/{id} -> 200

【5. 帳戶轉帳（POST /saves/{id}/accounts/transfer, GET .../history）】
  5a.      存款戶 -> 交割戶 轉帳 990,000 -> 200
  5b.      轉帳後 savings_balance == 10,000
  5c.      轉帳後 trading_balance == 990,000
  5d.      GET .../accounts/history -> 200
  5e.      流水帳至少 4 筆（建檔時存款戶+交割戶各 1 筆初始紀錄，加上轉帳的轉出+轉入各 1 筆）

【6. 股票查詢 / K 線 / 時空隔離（GET /stocks, /stocks/{id}, /stocks/{id}/prices）】
  6a.      GET /stocks?q=台積電（中文關鍵字查詢）-> 200
  6b.      GET /stocks/{STOCK_ID} -> 200（股票詳細資料）
  6c.      GET /stocks/{STOCK_ID}/prices?save_id={save_id} -> 200（K 線資料）
  6d.      時空隔離檢查：回傳的 K 線資料不應包含 >= current_trade_date 的日期
           （玩家不該看到「未來」的股價）
  6e.      GET /stocks/{STOCK_ID}/prices?save_id={save_id}&indicators=ma5,rsi14,macd -> 200
           且每筆資料含 ma5/rsi14/macd/macd_signal/macd_hist 欄位（技術指標）

【7. 盤前下單（PRE_MARKET，限價單）】
  7-pre.   確認 START_DATE 當天有報價資料（否則無法繼續後續撮合測試）
  7a.      POST /saves/{id}/orders 下「限價買、價格 = 開盤價+5」-> 201
           （限價 >= 開盤價，預期之後會以開盤價成交）
  7b.      新委託單 status == PENDING（待成交）
  7c.      新委託單 phase == PRE_MARKET（記錄為下單時的階段）
  7d.      GET /saves/{id}/orders -> 200（委託單列表）
  7e.      送出「限價買、價格不符升降單位」-> 400（升降單位檢查）

【7f-7m. 單檔股票詳細資訊（GET /saves/{id}/stocks/{stock_id}，PRE_MARKET）】
  7f.      GET /saves/{id}/stocks/{STOCK_ID} -> 200
  7g.      回應含 stock_id/stock_name_zh/market_type/sector_name
  7h.      current_price == 前一交易日 close_price
  7i.      price_change / price_change_percent == 0
  7j.      open/high/low/close == null，volume == 0（盤前未知今日資料）
  7k.      回應含 is_attention/is_disposition/is_full_delivery
  7l.      不存在的 stock_id -> 404
  7m.      不存在的 save_id -> 404

【8. 推進：盤前 -> 盤中（結算盤前限價單）】
  8a.      POST /saves/{id}/advance -> 200
  8b.      推進後 current_phase == INTRADAY
  8c.      盤前委託單已結算為 FILLED（成交）或 EXPIRED（當日無報價時失效）
  8d.      若 FILLED，成交價 exec_price == 當日開盤價
  8e.      若 FILLED，holdings 表中該股數量 == 1（張）

【8f-8i. 單檔股票詳細資訊（INTRADAY）】
  8f.      GET /saves/{id}/stocks/{STOCK_ID} -> 200
  8g.      current_price == 今日 open_price
  8h.      price_change / price_change_percent == open_price - ref_price
  8i.      open_price 顯示今日開盤價，high/low/close == null，volume == 0

【9. 盤中下市價賣單（INTRADAY，僅在 8 已成交持股時執行）】
  9a.      POST /saves/{id}/orders 下「市價賣出 1 張」-> 201
           （若步驟 8 未成交、沒有持股，此項視為跳過 FAIL，不影響整體流程判斷）

【10. 推進：盤中 -> 盤後（結算盤中單，市價成交價＝收盤價）】
  10a.     POST /saves/{id}/advance -> 200
  10b.     推進後 current_phase == POST_MARKET
  10c.     盤中市價賣單已結算為 FILLED 或 EXPIRED
  10d.     若 FILLED，成交價 exec_price == 當日收盤價

【10e-10h. 單檔股票詳細資訊（POST_MARKET）】
  10e.     GET /saves/{id}/stocks/{STOCK_ID} -> 200
  10f.     current_price == 今日 close_price
  10g.     open/high/low/close/volume 反映今日實際資料
  10h.     price_change / price_change_percent == close_price - ref_price

【11. 盤後僅限定價交易（POST_MARKET）】
  11a.     盤後送出「限價買單」-> 4xx（盤後不可下限價/市價單，僅能定價）
  11b.     盤後送出「定價買單」（MARKET, side=BUY）-> 201

【12. 推進：盤後 -> 收市（結算盤後定價單，成交價＝收盤價）】
  12a.     POST /saves/{id}/advance -> 200
  12b.     推進後 current_phase == CLOSED
  12c.     收市階段送出任何委託單 -> 4xx（收市鎖定交易）

【12d-12f. 單檔股票詳細資訊（CLOSED）】
  12d.     GET /saves/{id}/stocks/{STOCK_ID} -> 200
  12e.     current_price == 今日 close_price
  12f.     open/high/low/close/volume 仍反映今日實際資料（收市後不再隱藏）

【13. 持股 / 成交紀錄查詢】
  13a.     GET /saves/{id}/holdings -> 200（目前持股列表，含市值估算）
  13b.     GET /saves/{id}/holdings/transactions -> 200（歷史成交紀錄）

【14. 自選股（watchlist）】
  14a.     POST /saves/{id}/watchlist -> 201（加入自選股）
  14b.     GET /saves/{id}/watchlist -> 200，且列表中包含剛加入的股票
  14c.     DELETE /saves/{id}/watchlist/{stock_id} -> 204（移除自選股）

【15. 推進：收市 -> 下一交易日盤前（結算盤後定價單 + 換日）】
  15a.     POST /saves/{id}/advance -> 200
  15b.     推進後 current_phase == PRE_MARKET
  15c.     current_trade_date 已往後推進（大於 START_DATE）
  15d.     步驟 11b 的盤後定價單已結算為 FILLED 或 EXPIRED

【16. 登出 / session 失效】
  16a.     POST /auth/logout -> 200
  16b.     登出後用舊 session_id 呼叫 API -> 401（session 已失效）

────────────────────────────────────────────────────────────────────────
"""

import random
import string
import sys

import httpx

BASE_URL = "http://localhost:8000"
SQL_API_URL = "http://sql-api.shiragaserver.lan/query"

STOCK_ID = "2330"
START_DATE = "2023-01-04"  # 2023-01-03 也有資料，可當「前一交易日」

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


def main():
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    account = f"smoketest_{rand}"
    password = "test1234"

    client = httpx.Client(base_url=BASE_URL, timeout=10)
    state = {"save_id": None}

    try:
        run(client, account, password, state)
    except Exception as e:
        record("UNEXPECTED EXCEPTION", False, repr(e))
    finally:
        cleanup(account, state)
        print_summary()


def cleanup(account, state):
    try:
        if state.get("save_id"):
            db_query("DELETE FROM save_files WHERE save_id=?", [state["save_id"]])
        db_query("DELETE FROM users WHERE account=?", [account])
        print("\n(已清理測試資料: save_id=%s, account=%s)" % (state.get("save_id"), account))
    except Exception as e:
        print(f"\n清理測試資料失敗（請手動檢查）: {e}")


def run(client, account, password, state):
    # ── 0. health check ──────────────────────────────────────────────
    try:
        r = client.get("/")
        check("0. health check (/)", r.status_code == 200, r.text)
    except Exception as e:
        record("0. health check (/)", False, str(e))
        print("\nServer 連不上，後面全部跳過。請先啟動 uvicorn app.main:app --reload")
        return

    # ── 1. 註冊 ───────────────────────────────────────────────────────
    r = client.post("/auth/register", json={"account": account, "password": password})
    check("1. register 201", r.status_code == 201, f"{r.status_code}: {r.text}")

    r = client.post("/auth/register", json={"account": account, "password": password})
    check("1b. duplicate register -> 409", r.status_code == 409, f"{r.status_code}: {r.text}")

    # ── 2. 登入 ───────────────────────────────────────────────────────
    r = client.post("/auth/login", json={"account": account, "password": "wrongpass"})
    check("2a. wrong password -> 401", r.status_code == 401, f"{r.status_code}: {r.text}")

    r = client.post("/auth/login", json={"account": account, "password": password})
    check("2b. login 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    session_id = r.json().get("session_id") if r.status_code == 200 else None
    check("2c. login returns session_id", bool(session_id), r.text)

    if not session_id:
        print("\n沒有 session_id，後面全部跳過。")
        return

    headers = {"X-Session-Id": session_id}

    # ── 3. 建立存檔 ───────────────────────────────────────────────────
    save_name = account.replace("smoketest_", "smoke_")
    body = {"save_name": save_name, "start_date": START_DATE, "initial_funds": 1000000}
    r = client.post("/saves", json=body, headers=headers)
    check("3a. create save 201", r.status_code == 201, f"{r.status_code}: {r.text}")
    save = r.json() if r.status_code == 201 else {}
    save_id = save.get("save_id")
    state["save_id"] = save_id

    if save_id:
        check("3b. savings_balance == 1000000", float(save.get("savings_balance", -1)) == 1000000, save)
        check("3c. trading_balance == 0", float(save.get("trading_balance", -1)) == 0, save)
        check("3d. status == ACTIVE", save.get("status") == "ACTIVE", save)
        check("3e. current_phase == PRE_MARKET", save.get("current_phase") == "PRE_MARKET", save)
        check("3f. current_trade_date == start_date", str(save.get("current_trade_date")) == START_DATE, save)

    r = client.post("/saves", json=body, headers=headers)
    check("3g. duplicate save name -> 4xx", r.status_code >= 400, f"{r.status_code}: {r.text}")

    if not save_id:
        print("\n沒有 save_id，後面全部跳過。")
        return

    # ── 4. 列表 / 單一查詢 ────────────────────────────────────────────
    r = client.get("/saves", headers=headers)
    check("4a. list saves 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        found = next((s for s in r.json() if s.get("save_id") == save_id), None)
        check("4b. list saves contains new save", found is not None, r.text)
        if found:
            check("4c. list save has total_asset", "total_asset" in found, found)
            check("4d. list save has cumulative_return", "cumulative_return" in found, found)

    r = client.get(f"/saves/{save_id}", headers=headers)
    check("4e. get save 200", r.status_code == 200, f"{r.status_code}: {r.text}")

    # ── 5. 轉帳 ───────────────────────────────────────────────────────
    r = client.post(
        f"/saves/{save_id}/accounts/transfer",
        json={"direction": "savings_to_trading", "amount": 990000},
        headers=headers,
    )
    check("5a. transfer savings->trading 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        tr = r.json()
        check("5b. savings_balance == 10000", float(tr.get("savings_balance", -1)) == 10000, tr)
        check("5c. trading_balance == 990000", float(tr.get("trading_balance", -1)) == 990000, tr)

    r = client.get(f"/saves/{save_id}/accounts/history", headers=headers)
    check("5d. account history 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        check("5e. account history has >= 4 rows (2 initial + 2 transfer)", len(r.json()) >= 4, r.json())

    # ── 6. 股票查詢 / K 線 / 時空隔離 ─────────────────────────────────
    r = client.get("/stocks", params={"q": "台積電"}, headers=headers)
    check("6a. search stocks 200", r.status_code == 200, f"{r.status_code}: {r.text}")

    r = client.get(f"/stocks/{STOCK_ID}", headers=headers)
    check("6b. get stock detail 200", r.status_code == 200, f"{r.status_code}: {r.text}")

    r = client.get(f"/stocks/{STOCK_ID}/prices", headers=headers, params={"save_id": save_id})
    check("6c. get price history 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        rows = r.json()
        future_rows = [row for row in rows if str(row["trade_date"]) >= START_DATE]
        check(
            "6d. K-line only shows dates before current_trade_date (時空隔離)",
            len(future_rows) == 0,
            f"找到 {len(future_rows)} 筆 >= {START_DATE} 的資料: {future_rows[:3]}",
        )

    r = client.get(
        f"/stocks/{STOCK_ID}/prices",
        headers=headers,
        params={"save_id": save_id, "indicators": "ma5,rsi14,macd"},
    )
    check("6e. get price history with indicators 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        rows = r.json()
        has_fields = bool(rows) and all(
            key in rows[-1] for key in ("ma5", "rsi14", "macd", "macd_signal", "macd_hist")
        )
        check(
            "6e. price rows include ma5/rsi14/macd fields",
            has_fields,
            f"last row keys: {list(rows[-1].keys()) if rows else rows}",
        )

    # ── 7. 盤前下限價買單 ─────────────────────────────────────────────
    # 用前一日收盤價附近的價格掛單，確保開盤價落在合理範圍內能成交
    prev_close = db_query(
        "SELECT close_price FROM daily_prices WHERE stock_id=? AND trade_date < ? ORDER BY trade_date DESC LIMIT 1",
        [STOCK_ID, START_DATE],
    )
    today_prices = db_query(
        "SELECT open_price, high_price, low_price, close_price, volume, ref_price"
        " FROM daily_prices WHERE stock_id=? AND trade_date=?",
        [STOCK_ID, START_DATE],
    )
    check("7-pre. today has price data", bool(today_prices), today_prices)
    if not today_prices:
        return
    today = today_prices[0]
    open_price = float(today["open_price"])
    high_price_today = float(today["high_price"])
    low_price_today = float(today["low_price"])
    close_price_today = float(today["close_price"])
    volume_today = int(today["volume"])
    ref_price_today = float(today["ref_price"]) if today.get("ref_price") is not None else None

    # 限價買單：限價 >= 開盤價 才會成交
    buy_price = open_price + 5
    r = client.post(
        f"/saves/{save_id}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": buy_price, "quantity": 1},
        headers=headers,
    )
    check("7a. place PRE_MARKET LIMIT BUY order 201", r.status_code == 201, f"{r.status_code}: {r.text}")
    order_id = r.json().get("order_id") if r.status_code == 201 else None
    if order_id:
        check("7b. order status == PENDING", r.json().get("status") == "PENDING", r.json())
        check("7c. order phase == PRE_MARKET", r.json().get("phase") == "PRE_MARKET", r.json())

    # POST_MARKET 不可下單測試之前先確認 list works
    r = client.get(f"/saves/{save_id}/orders", headers=headers)
    check("7d. list orders 200", r.status_code == 200, f"{r.status_code}: {r.text}")

    # 升降單位檢查：價格加上一個不符任何升降單位的零頭 -> 400
    bad_price = buy_price + 0.003
    r = client.post(
        f"/saves/{save_id}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": bad_price, "quantity": 1},
        headers=headers,
    )
    check("7e. LIMIT order with invalid tick size -> 400", r.status_code == 400, f"{r.status_code}: {r.text}")

    # ── 7f-7l. 單檔股票詳細資訊（PRE_MARKET）─────────────────────────
    r = client.get(f"/saves/{save_id}/stocks/{STOCK_ID}", headers=headers)
    check("7f. get save-scoped stock detail (PRE_MARKET) 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        detail = r.json()
        check(
            "7g. PRE_MARKET stock detail has basic fields",
            all(k in detail for k in ("stock_id", "stock_name_zh", "market_type", "sector_name")),
            detail,
        )
        if prev_close:
            check(
                "7h. PRE_MARKET current_price == previous day's close_price",
                detail.get("current_price") == float(prev_close[0]["close_price"]),
                f"detail={detail} prev_close={prev_close}",
            )
        check(
            "7i. PRE_MARKET price_change / price_change_percent == 0",
            detail.get("price_change") == 0.0 and detail.get("price_change_percent") == 0.0,
            detail,
        )
        check(
            "7j. PRE_MARKET open/high/low/close == null, volume == 0",
            detail.get("open_price") is None
            and detail.get("high_price") is None
            and detail.get("low_price") is None
            and detail.get("close_price") is None
            and detail.get("volume") == 0,
            detail,
        )
        check(
            "7k. PRE_MARKET response has alert flags",
            all(k in detail for k in ("is_attention", "is_disposition", "is_full_delivery")),
            detail,
        )

    r = client.get(f"/saves/{save_id}/stocks/0000ZZ", headers=headers)
    check("7l. get stock detail for unknown stock_id -> 404", r.status_code == 404, f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/999999999/stocks/{STOCK_ID}", headers=headers)
    check("7m. get stock detail for nonexistent save_id -> 404", r.status_code == 404, f"{r.status_code}: {r.text}")

    # ── 8. 推進: 盤前 -> 盤中（結算盤前限價單，成交價=開盤價）──────────
    r = client.post(f"/saves/{save_id}/advance", headers=headers)
    check("8a. advance PRE_MARKET->INTRADAY 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        check("8b. current_phase == INTRADAY", r.json().get("current_phase") == "INTRADAY", r.json())

    if order_id:
        rows = db_query("SELECT status FROM stock_orders WHERE order_id=?", [order_id])
        check(
            "8c. pre-market order settled (FILLED or EXPIRED)",
            rows and rows[0]["status"] in ("FILLED", "EXPIRED"),
            rows,
        )
        if rows and rows[0]["status"] == "FILLED":
            tx = db_query("SELECT exec_price FROM stock_transactions WHERE order_id=?", [order_id])
            check(
                "8d. exec_price == open_price",
                tx and float(tx[0]["exec_price"]) == open_price,
                f"tx={tx} open_price={open_price}",
            )
            holding = db_query("SELECT quantity FROM holdings WHERE save_id=? AND stock_id=?", [save_id, STOCK_ID])
            check("8e. holding quantity == 1", holding and int(holding[0]["quantity"]) == 1, holding)

    # ── 8f-8i. 單檔股票詳細資訊（INTRADAY）───────────────────────────
    r = client.get(f"/saves/{save_id}/stocks/{STOCK_ID}", headers=headers)
    check("8f. get save-scoped stock detail (INTRADAY) 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        detail = r.json()
        check(
            "8g. INTRADAY current_price == today's open_price",
            detail.get("current_price") == open_price,
            detail,
        )
        if ref_price_today is not None:
            expected_change = round(open_price - ref_price_today, 2)
            expected_pct = round(expected_change / ref_price_today * 100, 2) if ref_price_today else 0.0
            check(
                "8h. INTRADAY price_change/price_change_percent vs ref_price",
                detail.get("price_change") == expected_change and detail.get("price_change_percent") == expected_pct,
                f"detail={detail} ref_price={ref_price_today}",
            )
        check(
            "8i. INTRADAY open_price shown, high/low/close == null, volume == 0",
            detail.get("open_price") == open_price
            and detail.get("high_price") is None
            and detail.get("low_price") is None
            and detail.get("close_price") is None
            and detail.get("volume") == 0,
            detail,
        )

    # ── 9. 盤中下市價賣單（若有持股）─────────────────────────────────
    holding = db_query("SELECT quantity FROM holdings WHERE save_id=? AND stock_id=?", [save_id, STOCK_ID])
    has_holding = bool(holding) and int(holding[0]["quantity"]) > 0

    if has_holding:
        r = client.post(
            f"/saves/{save_id}/orders",
            json={"stock_id": STOCK_ID, "order_type": "MARKET", "side": "SELL", "quantity": 1},
            headers=headers,
        )
        check("9a. place INTRADAY MARKET SELL order 201", r.status_code == 201, f"{r.status_code}: {r.text}")
        sell_order_id = r.json().get("order_id") if r.status_code == 201 else None
    else:
        sell_order_id = None
        record("9a. place INTRADAY MARKET SELL order 201", False, "前一步沒有成交持股，跳過")

    # ── 10. 推進: 盤中 -> 盤後（結算盤中單，市價成交價=收盤價）────────
    r = client.post(f"/saves/{save_id}/advance", headers=headers)
    check("10a. advance INTRADAY->POST_MARKET 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        check("10b. current_phase == POST_MARKET", r.json().get("current_phase") == "POST_MARKET", r.json())

    if sell_order_id:
        close_price = float(today["close_price"])
        tx = db_query("SELECT exec_price FROM stock_transactions WHERE order_id=?", [sell_order_id])
        rows = db_query("SELECT status FROM stock_orders WHERE order_id=?", [sell_order_id])
        check(
            "10c. intraday market sell settled (FILLED or EXPIRED)",
            rows and rows[0]["status"] in ("FILLED", "EXPIRED"),
            rows,
        )
        if rows and rows[0]["status"] == "FILLED":
            check(
                "10d. market sell exec_price == close_price",
                tx and float(tx[0]["exec_price"]) == close_price,
                f"tx={tx} close_price={close_price}",
            )

    # ── 10e-10g. 單檔股票詳細資訊（POST_MARKET）──────────────────────
    r = client.get(f"/saves/{save_id}/stocks/{STOCK_ID}", headers=headers)
    check("10e. get save-scoped stock detail (POST_MARKET) 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        detail = r.json()
        check(
            "10f. POST_MARKET current_price == today's close_price",
            detail.get("current_price") == close_price_today,
            detail,
        )
        check(
            "10g. POST_MARKET open/high/low/close/volume reflect today's data",
            detail.get("open_price") == open_price
            and detail.get("high_price") == high_price_today
            and detail.get("low_price") == low_price_today
            and detail.get("close_price") == close_price_today
            and detail.get("volume") == volume_today,
            detail,
        )
        if ref_price_today is not None:
            expected_change = round(close_price_today - ref_price_today, 2)
            expected_pct = round(expected_change / ref_price_today * 100, 2) if ref_price_today else 0.0
            check(
                "10h. POST_MARKET price_change/price_change_percent vs ref_price",
                detail.get("price_change") == expected_change and detail.get("price_change_percent") == expected_pct,
                f"detail={detail} ref_price={ref_price_today}",
            )

    # ── 11. 盤後不可下限價/市價單，只能定價交易 ─────────────────────
    r = client.post(
        f"/saves/{save_id}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": open_price, "quantity": 1},
        headers=headers,
    )
    check("11a. POST_MARKET rejects LIMIT order -> 4xx", r.status_code >= 400, f"{r.status_code}: {r.text}")

    r = client.post(
        f"/saves/{save_id}/orders",
        json={"stock_id": STOCK_ID, "order_type": "MARKET", "side": "BUY", "quantity": 1},
        headers=headers,
    )
    check("11b. place POST_MARKET (定價) order 201", r.status_code == 201, f"{r.status_code}: {r.text}")
    post_order_id = r.json().get("order_id") if r.status_code == 201 else None

    # ── 12. 推進: 盤後 -> 收市（結算盤後定價單，成交價=收盤價）──────
    r = client.post(f"/saves/{save_id}/advance", headers=headers)
    check("12a. advance POST_MARKET->CLOSED 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        check("12b. current_phase == CLOSED", r.json().get("current_phase") == "CLOSED", r.json())

    # 收市階段鎖定交易
    r = client.post(
        f"/saves/{save_id}/orders",
        json={"stock_id": STOCK_ID, "order_type": "MARKET", "side": "BUY", "quantity": 1},
        headers=headers,
    )
    check("12c. CLOSED phase rejects orders -> 4xx", r.status_code >= 400, f"{r.status_code}: {r.text}")

    # ── 12d-12e. 單檔股票詳細資訊（CLOSED）───────────────────────────
    r = client.get(f"/saves/{save_id}/stocks/{STOCK_ID}", headers=headers)
    check("12d. get save-scoped stock detail (CLOSED) 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        detail = r.json()
        check(
            "12e. CLOSED current_price == today's close_price",
            detail.get("current_price") == close_price_today,
            detail,
        )
        check(
            "12f. CLOSED open/high/low/close/volume still reflect today's data",
            detail.get("open_price") == open_price
            and detail.get("high_price") == high_price_today
            and detail.get("low_price") == low_price_today
            and detail.get("close_price") == close_price_today
            and detail.get("volume") == volume_today,
            detail,
        )

    # ── 13. 持股 / 成交紀錄 ───────────────────────────────────────────
    r = client.get(f"/saves/{save_id}/holdings", headers=headers)
    check("13a. list holdings 200", r.status_code == 200, f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id}/holdings/transactions", headers=headers)
    check("13b. list transactions 200", r.status_code == 200, f"{r.status_code}: {r.text}")

    # ── 14. 自選股 ────────────────────────────────────────────────────
    r = client.post(f"/saves/{save_id}/watchlist", json={"stock_id": STOCK_ID}, headers=headers)
    check("14a. add watchlist 201", r.status_code == 201, f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id}/watchlist", headers=headers)
    check("14b. list watchlist 200 and contains stock", r.status_code == 200 and any(
        w.get("stock_id") == STOCK_ID for w in r.json()
    ), f"{r.status_code}: {r.text}")

    r = client.delete(f"/saves/{save_id}/watchlist/{STOCK_ID}", headers=headers)
    check("14c. remove watchlist 204", r.status_code == 204, f"{r.status_code}: {r.text}")

    # ── 15. 推進: 收市 -> 下一交易日盤前 ─────────────────────────────
    r = client.post(f"/saves/{save_id}/advance", headers=headers)
    check("15a. advance CLOSED->next day PRE_MARKET 200", r.status_code == 200, f"{r.status_code}: {r.text}")
    if r.status_code == 200:
        data = r.json()
        check("15b. current_phase == PRE_MARKET", data.get("current_phase") == "PRE_MARKET", data)
        check("15c. current_trade_date advanced", str(data.get("current_trade_date")) > START_DATE, data)

    if post_order_id:
        close_price = float(today["close_price"])
        rows = db_query("SELECT status FROM stock_orders WHERE order_id=?", [post_order_id])
        check(
            "15d. post-market order settled (FILLED or EXPIRED)",
            rows and rows[0]["status"] in ("FILLED", "EXPIRED"),
            rows,
        )

    # ── 16. 登出 / session 失效 ──────────────────────────────────────
    r = client.post("/auth/logout", headers=headers)
    check("16a. logout 200", r.status_code == 200, f"{r.status_code}: {r.text}")

    r = client.get(f"/saves/{save_id}", headers=headers)
    check("16b. old session rejected after logout -> 401", r.status_code == 401, f"{r.status_code}: {r.text}")


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
