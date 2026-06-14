"""端對端 smoke test（pytest 版本），依照 README / docs/report3 規格驗證 API 行為。

用法:
    1. 另開一個 terminal 啟動 server: uvicorn app.main:app --reload
    2. pytest backend_tests/test_smoke.py -v

設計：`flow` fixture（session-scoped）依序跑完整個流程一次（註冊→登入→建檔→
下單→推進→撮合→查詢→登出），把每一步的 response / 計算結果存進 ctx dict；
之後每個 test_* 函式只針對 ctx 裡對應的部分做斷言。fixture 結束時會清理本次
建立的 save_files 與 users 資料（帳號固定為 smoketest_xxxxxxxx，方便辨識）。
"""

import pytest

from conftest import START_DATE, STOCK_ID, db_query, random_suffix


@pytest.fixture(scope="session")
def flow(client):
    account = f"smoketest_{random_suffix()}"
    password = "test1234"
    ctx = {"account": account, "password": password, "save_id": None}

    # ── 1. 註冊 ───────────────────────────────────────────────────────
    ctx["register"] = client.post("/auth/register", json={"account": account, "password": password})
    ctx["dup_register"] = client.post("/auth/register", json={"account": account, "password": password})

    # ── 2. 登入 ───────────────────────────────────────────────────────
    ctx["wrong_login"] = client.post("/auth/login", json={"account": account, "password": "wrongpass"})
    ctx["login"] = client.post("/auth/login", json={"account": account, "password": password})
    session_id = ctx["login"].json().get("session_id") if ctx["login"].status_code == 200 else None
    ctx["session_id"] = session_id

    if not session_id:
        yield ctx
        db_query("DELETE FROM users WHERE account=?", [account])
        return

    headers = {"X-Session-Id": session_id}
    ctx["headers"] = headers

    # ── 3. 建立存檔 ───────────────────────────────────────────────────
    save_name = account.replace("smoketest_", "smoke_")
    body = {"save_name": save_name, "start_date": START_DATE, "initial_funds": 1000000}
    ctx["create_save"] = client.post("/saves", json=body, headers=headers)
    save = ctx["create_save"].json() if ctx["create_save"].status_code == 201 else {}
    save_id = save.get("save_id")
    ctx["save_id"] = save_id
    ctx["dup_save"] = client.post("/saves", json=body, headers=headers)

    if not save_id:
        yield ctx
        db_query("DELETE FROM users WHERE account=?", [account])
        return

    # ── 4. 列表 / 單一查詢 ────────────────────────────────────────────
    ctx["list_saves"] = client.get("/saves", headers=headers)
    ctx["get_save"] = client.get(f"/saves/{save_id}", headers=headers)

    # ── 5. 轉帳 ───────────────────────────────────────────────────────
    ctx["transfer"] = client.post(
        f"/saves/{save_id}/accounts/transfer",
        json={"direction": "savings_to_trading", "amount": 990000},
        headers=headers,
    )
    ctx["account_history"] = client.get(f"/saves/{save_id}/accounts/history", headers=headers)

    # ── 6. 股票查詢 / K 線 / 時空隔離 ─────────────────────────────────
    ctx["search_stocks"] = client.get("/stocks", params={"q": "台積電"}, headers=headers)
    ctx["stock_detail"] = client.get(f"/stocks/{STOCK_ID}", headers=headers)
    ctx["price_history"] = client.get(f"/stocks/{STOCK_ID}/prices", headers=headers, params={"save_id": save_id})
    ctx["price_history_indicators"] = client.get(
        f"/stocks/{STOCK_ID}/prices",
        headers=headers,
        params={"save_id": save_id, "indicators": "ma5,rsi14,macd"},
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
    ctx["prev_close"] = prev_close
    ctx["today_prices"] = today_prices
    if not today_prices:
        yield ctx
        db_query("DELETE FROM save_files WHERE save_id=?", [save_id])
        db_query("DELETE FROM users WHERE account=?", [account])
        return

    today = today_prices[0]
    open_price = float(today["open_price"])
    ctx["today"] = {
        "open_price": open_price,
        "high_price": float(today["high_price"]),
        "low_price": float(today["low_price"]),
        "close_price": float(today["close_price"]),
        "volume": int(today["volume"]),
        "ref_price": float(today["ref_price"]) if today.get("ref_price") is not None else None,
    }

    # 限價買單：限價 >= 開盤價 才會成交
    buy_price = open_price + 5
    ctx["pre_market_order"] = client.post(
        f"/saves/{save_id}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": buy_price, "quantity": 1},
        headers=headers,
    )
    order_id = ctx["pre_market_order"].json().get("order_id") if ctx["pre_market_order"].status_code == 201 else None
    ctx["order_id"] = order_id

    ctx["list_orders"] = client.get(f"/saves/{save_id}/orders", headers=headers)

    # 升降單位檢查：價格加上一個不符任何升降單位的零頭 -> 400
    bad_price = buy_price + 0.003
    ctx["bad_tick_order"] = client.post(
        f"/saves/{save_id}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": bad_price, "quantity": 1},
        headers=headers,
    )

    # ── 7f-7m. 單檔股票詳細資訊（PRE_MARKET）─────────────────────────
    ctx["pre_market_stock_detail"] = client.get(f"/saves/{save_id}/stocks/{STOCK_ID}", headers=headers)
    ctx["unknown_stock_detail"] = client.get(f"/saves/{save_id}/stocks/0000ZZ", headers=headers)
    ctx["nonexistent_save_detail"] = client.get(f"/saves/999999999/stocks/{STOCK_ID}", headers=headers)

    # ── 8. 推進: 盤前 -> 盤中（結算盤前限價單，成交價=開盤價）──────────
    ctx["advance_to_intraday"] = client.post(f"/saves/{save_id}/advance", headers=headers)

    if order_id:
        ctx["pre_market_order_row"] = db_query("SELECT status FROM stock_orders WHERE order_id=?", [order_id])
        if ctx["pre_market_order_row"] and ctx["pre_market_order_row"][0]["status"] == "FILLED":
            ctx["pre_market_tx_row"] = db_query(
                "SELECT exec_price FROM stock_transactions WHERE order_id=?", [order_id],
            )
            ctx["holding_after_pre_market"] = db_query(
                "SELECT quantity FROM holdings WHERE save_id=? AND stock_id=?", [save_id, STOCK_ID],
            )

    ctx["list_orders_after_intraday"] = client.get(f"/saves/{save_id}/orders", headers=headers)

    # ── 8f-8i. 單檔股票詳細資訊（INTRADAY）───────────────────────────
    ctx["intraday_stock_detail"] = client.get(f"/saves/{save_id}/stocks/{STOCK_ID}", headers=headers)

    # ── 9. 盤中下市價賣單（若有持股）─────────────────────────────────
    holding = db_query("SELECT quantity FROM holdings WHERE save_id=? AND stock_id=?", [save_id, STOCK_ID])
    has_holding = bool(holding) and int(holding[0]["quantity"]) > 0
    ctx["has_holding"] = has_holding

    if has_holding:
        ctx["intraday_sell"] = client.post(
            f"/saves/{save_id}/orders",
            json={"stock_id": STOCK_ID, "order_type": "MARKET", "side": "SELL", "quantity": 1},
            headers=headers,
        )
        sell_order_id = (
            ctx["intraday_sell"].json().get("order_id") if ctx["intraday_sell"].status_code == 201 else None
        )
    else:
        sell_order_id = None
    ctx["sell_order_id"] = sell_order_id

    # ── 10. 推進: 盤中 -> 盤後（結算盤中單，市價成交價=收盤價）────────
    ctx["advance_to_post_market"] = client.post(f"/saves/{save_id}/advance", headers=headers)

    if sell_order_id:
        ctx["sell_order_row"] = db_query("SELECT status FROM stock_orders WHERE order_id=?", [sell_order_id])
        if ctx["sell_order_row"] and ctx["sell_order_row"][0]["status"] == "FILLED":
            ctx["sell_tx_row"] = db_query(
                "SELECT exec_price FROM stock_transactions WHERE order_id=?", [sell_order_id],
            )

    ctx["list_orders_after_post_market"] = client.get(f"/saves/{save_id}/orders", headers=headers)

    # ── 10e-10h. 單檔股票詳細資訊（POST_MARKET）──────────────────────
    ctx["post_market_stock_detail"] = client.get(f"/saves/{save_id}/stocks/{STOCK_ID}", headers=headers)

    # ── 11. 盤後不可下限價/市價單，只能定價交易 ─────────────────────
    ctx["post_market_limit_reject"] = client.post(
        f"/saves/{save_id}/orders",
        json={"stock_id": STOCK_ID, "order_type": "LIMIT", "side": "BUY", "price": open_price, "quantity": 1},
        headers=headers,
    )
    ctx["post_market_order"] = client.post(
        f"/saves/{save_id}/orders",
        json={"stock_id": STOCK_ID, "order_type": "MARKET", "side": "BUY", "quantity": 1},
        headers=headers,
    )
    post_order_id = (
        ctx["post_market_order"].json().get("order_id") if ctx["post_market_order"].status_code == 201 else None
    )
    ctx["post_order_id"] = post_order_id

    # ── 12. 推進: 盤後 -> 收市（結算盤後定價單，成交價=收盤價）──────
    ctx["advance_to_closed"] = client.post(f"/saves/{save_id}/advance", headers=headers)

    # 收市階段鎖定交易
    ctx["closed_order_reject"] = client.post(
        f"/saves/{save_id}/orders",
        json={"stock_id": STOCK_ID, "order_type": "MARKET", "side": "BUY", "quantity": 1},
        headers=headers,
    )

    # ── 12d-12f. 單檔股票詳細資訊（CLOSED）───────────────────────────
    ctx["closed_stock_detail"] = client.get(f"/saves/{save_id}/stocks/{STOCK_ID}", headers=headers)

    # ── 13. 持股 / 成交紀錄 ───────────────────────────────────────────
    ctx["list_holdings"] = client.get(f"/saves/{save_id}/holdings", headers=headers)
    ctx["list_transactions"] = client.get(f"/saves/{save_id}/holdings/transactions", headers=headers)

    # ── 14. 自選股 ────────────────────────────────────────────────────
    ctx["watchlist_add"] = client.post(f"/saves/{save_id}/watchlist", json={"stock_id": STOCK_ID}, headers=headers)
    ctx["watchlist_list"] = client.get(f"/saves/{save_id}/watchlist", headers=headers)
    ctx["watchlist_remove"] = client.delete(f"/saves/{save_id}/watchlist/{STOCK_ID}", headers=headers)

    # ── 15. 推進: 收市 -> 下一交易日盤前 ─────────────────────────────
    ctx["advance_to_next_day"] = client.post(f"/saves/{save_id}/advance", headers=headers)

    if post_order_id:
        ctx["post_market_order_row"] = db_query("SELECT status FROM stock_orders WHERE order_id=?", [post_order_id])

    # ── 16. 登出 / session 失效 ──────────────────────────────────────
    ctx["logout"] = client.post("/auth/logout", headers=headers)
    ctx["old_session_get_save"] = client.get(f"/saves/{save_id}", headers=headers)

    yield ctx

    db_query("DELETE FROM save_files WHERE save_id=?", [save_id])
    db_query("DELETE FROM users WHERE account=?", [account])


# ── 1-2. 帳號註冊 / 登入 ───────────────────────────────────────────────


def test_register(flow):
    assert flow["register"].status_code == 201, flow["register"].text


def test_duplicate_register_rejected(flow):
    assert flow["dup_register"].status_code == 409, flow["dup_register"].text


def test_login(flow):
    assert flow["wrong_login"].status_code == 401, flow["wrong_login"].text
    assert flow["login"].status_code == 200, flow["login"].text
    assert flow["session_id"], flow["login"].text


# ── 3. 建立存檔 ──────────────────────────────────────────────────────


def test_create_save(flow):
    assert flow["create_save"].status_code == 201, flow["create_save"].text
    save = flow["create_save"].json()
    assert float(save.get("savings_balance", -1)) == 1000000, save
    assert float(save.get("trading_balance", -1)) == 0, save
    assert save.get("status") == "ACTIVE", save
    assert save.get("current_phase") == "PRE_MARKET", save
    assert str(save.get("current_trade_date")) == START_DATE, save


def test_duplicate_save_name_rejected(flow):
    assert flow["dup_save"].status_code >= 400, flow["dup_save"].text


# ── 4. 列表 / 單一查詢 ─────────────────────────────────────────────────


def test_list_saves_contains_new_save(flow):
    r = flow["list_saves"]
    assert r.status_code == 200, r.text
    found = next((s for s in r.json() if s.get("save_id") == flow["save_id"]), None)
    assert found is not None, r.text
    assert "total_asset" in found, found
    assert "cumulative_return" in found, found


def test_get_save(flow):
    assert flow["get_save"].status_code == 200, flow["get_save"].text


# ── 5. 轉帳 ──────────────────────────────────────────────────────────


def test_transfer_savings_to_trading(flow):
    r = flow["transfer"]
    assert r.status_code == 200, r.text
    tr = r.json()
    assert float(tr.get("savings_balance", -1)) == 10000, tr
    assert float(tr.get("trading_balance", -1)) == 990000, tr


def test_account_history(flow):
    r = flow["account_history"]
    assert r.status_code == 200, r.text
    assert len(r.json()) >= 4, r.json()  # 2 initial + 2 transfer


# ── 6. 股票查詢 / K 線 / 時空隔離 ───────────────────────────────────────


def test_search_stocks(flow):
    assert flow["search_stocks"].status_code == 200, flow["search_stocks"].text


def test_get_stock_detail(flow):
    assert flow["stock_detail"].status_code == 200, flow["stock_detail"].text


def test_price_history_time_isolation(flow):
    r = flow["price_history"]
    assert r.status_code == 200, r.text
    rows = r.json()
    future_rows = [row for row in rows if str(row["trade_date"]) >= START_DATE]
    assert len(future_rows) == 0, f"找到 {len(future_rows)} 筆 >= {START_DATE} 的資料: {future_rows[:3]}"


def test_price_history_with_indicators(flow):
    r = flow["price_history_indicators"]
    assert r.status_code == 200, r.text
    rows = r.json()
    assert rows, "price history is empty"
    last = rows[-1]
    for key in ("ma5", "rsi14", "macd", "macd_signal", "macd_hist"):
        assert key in last, last


# ── 7. 盤前下單（PRE_MARKET，限價單） ───────────────────────────────────


def test_today_has_price_data(flow):
    assert flow["today_prices"], "找不到 START_DATE 的報價資料，後續測試無法繼續"


def test_pre_market_limit_buy_order(flow):
    r = flow["pre_market_order"]
    assert r.status_code == 201, r.text
    body = r.json()
    assert body.get("status") == "PENDING", body
    assert body.get("phase") == "PRE_MARKET", body


def test_list_orders(flow):
    assert flow["list_orders"].status_code == 200, flow["list_orders"].text


def test_list_orders_pending_fields_null(flow):
    if not flow["order_id"]:
        pytest.skip("沒有成功下單，跳過")
    rows = flow["list_orders"].json()
    order = next((o for o in rows if o["order_id"] == flow["order_id"]), None)
    assert order is not None, rows
    assert order["status"] == "PENDING", order
    for key in ("realized_pnl", "return_rate", "avg_cost", "net_amount"):
        assert order[key] is None, order


def test_list_orders_buy_settlement_fields(flow):
    rows = flow.get("pre_market_order_row")
    if not rows or rows[0]["status"] != "FILLED":
        pytest.skip("委託單未成交，跳過")

    orders = flow["list_orders_after_intraday"].json()
    order = next((o for o in orders if o["order_id"] == flow["order_id"]), None)
    assert order is not None, orders
    assert order["status"] == "FILLED", order

    exec_price = float(flow["pre_market_tx_row"][0]["exec_price"])
    quantity = order["quantity"]
    principal = round(exec_price * quantity * 1000)
    fee = max(20, principal * 1425 // 1000000)

    assert order["avg_cost"] == exec_price, order
    assert order["net_amount"] == principal + fee, order
    assert order["realized_pnl"] is None, order
    assert order["return_rate"] is None, order


def test_list_orders_sell_settlement_fields(flow):
    if not flow["sell_order_id"]:
        pytest.skip("沒有盤中賣單，跳過")
    if flow["sell_order_row"][0]["status"] != "FILLED":
        pytest.skip("委託單未成交，跳過")

    orders = flow["list_orders_after_post_market"].json()
    order = next((o for o in orders if o["order_id"] == flow["sell_order_id"]), None)
    assert order is not None, orders
    assert order["status"] == "FILLED", order

    exec_price = float(flow["sell_tx_row"][0]["exec_price"])
    avg_cost = float(flow["pre_market_tx_row"][0]["exec_price"])
    quantity = order["quantity"]
    principal = round(exec_price * quantity * 1000)
    fee = max(20, principal * 1425 // 1000000)
    tax = principal * 3 // 1000

    expected_net = principal - fee - tax
    cost_basis = avg_cost * quantity * 1000
    expected_pnl = round(expected_net - cost_basis, 2)
    expected_rate = round(expected_pnl / cost_basis * 100, 2) if cost_basis else None

    assert order["avg_cost"] == avg_cost, order
    assert order["net_amount"] == expected_net, order
    assert order["realized_pnl"] == expected_pnl, order
    assert order["return_rate"] == expected_rate, order


def test_invalid_tick_size_rejected(flow):
    assert flow["bad_tick_order"].status_code == 400, flow["bad_tick_order"].text


# ── 7f-7m. 單檔股票詳細資訊（PRE_MARKET） ───────────────────────────────


def test_pre_market_stock_detail(flow):
    r = flow["pre_market_stock_detail"]
    assert r.status_code == 200, r.text
    detail = r.json()
    for key in ("stock_id", "stock_name_zh", "market_type", "sector_name", "is_attention", "is_disposition", "is_full_delivery"):
        assert key in detail, detail

    if flow["prev_close"]:
        assert detail.get("current_price") == float(flow["prev_close"][0]["close_price"]), detail

    assert detail.get("price_change") == 0.0, detail
    assert detail.get("price_change_percent") == 0.0, detail
    assert detail.get("open_price") is None, detail
    assert detail.get("high_price") is None, detail
    assert detail.get("low_price") is None, detail
    assert detail.get("close_price") is None, detail
    assert detail.get("volume") == 0, detail


def test_stock_detail_unknown_stock_id_404(flow):
    assert flow["unknown_stock_detail"].status_code == 404, flow["unknown_stock_detail"].text


def test_stock_detail_nonexistent_save_404(flow):
    assert flow["nonexistent_save_detail"].status_code == 404, flow["nonexistent_save_detail"].text


# ── 8. 推進：盤前 -> 盤中 ───────────────────────────────────────────────


def test_advance_pre_market_to_intraday(flow):
    r = flow["advance_to_intraday"]
    assert r.status_code == 200, r.text
    assert r.json().get("current_phase") == "INTRADAY", r.json()


def test_pre_market_order_settled(flow):
    if not flow["order_id"]:
        pytest.skip("沒有成功下單，跳過")
    rows = flow["pre_market_order_row"]
    assert rows and rows[0]["status"] in ("FILLED", "EXPIRED"), rows


def test_pre_market_order_fill_details(flow):
    rows = flow.get("pre_market_order_row")
    if not rows or rows[0]["status"] != "FILLED":
        pytest.skip("委託單未成交，跳過")
    tx = flow["pre_market_tx_row"]
    open_price = flow["today"]["open_price"]
    assert tx and float(tx[0]["exec_price"]) == open_price, f"tx={tx} open_price={open_price}"
    holding = flow["holding_after_pre_market"]
    assert holding and int(holding[0]["quantity"]) == 1, holding


# ── 8f-8i. 單檔股票詳細資訊（INTRADAY） ─────────────────────────────────


def test_intraday_stock_detail(flow):
    r = flow["intraday_stock_detail"]
    assert r.status_code == 200, r.text
    detail = r.json()
    open_price = flow["today"]["open_price"]
    ref_price = flow["today"]["ref_price"]

    assert detail.get("current_price") == open_price, detail

    if ref_price is not None:
        expected_change = round(open_price - ref_price, 2)
        expected_pct = round(expected_change / ref_price * 100, 2) if ref_price else 0.0
        assert detail.get("price_change") == expected_change, f"detail={detail} ref_price={ref_price}"
        assert detail.get("price_change_percent") == expected_pct, f"detail={detail} ref_price={ref_price}"

    assert detail.get("open_price") == open_price, detail
    assert detail.get("high_price") is None, detail
    assert detail.get("low_price") is None, detail
    assert detail.get("close_price") is None, detail
    assert detail.get("volume") == 0, detail


# ── 9. 盤中下市價賣單（若有持股） ───────────────────────────────────────


def test_intraday_market_sell_order(flow):
    if not flow["has_holding"]:
        pytest.skip("前一步沒有成交持股，跳過")
    assert flow["intraday_sell"].status_code == 201, flow["intraday_sell"].text


# ── 10. 推進：盤中 -> 盤後 ──────────────────────────────────────────────


def test_advance_intraday_to_post_market(flow):
    r = flow["advance_to_post_market"]
    assert r.status_code == 200, r.text
    assert r.json().get("current_phase") == "POST_MARKET", r.json()


def test_intraday_sell_settled(flow):
    if not flow["sell_order_id"]:
        pytest.skip("沒有盤中賣單，跳過")
    rows = flow["sell_order_row"]
    assert rows and rows[0]["status"] in ("FILLED", "EXPIRED"), rows


def test_intraday_sell_fill_price(flow):
    rows = flow.get("sell_order_row")
    if not rows or rows[0]["status"] != "FILLED":
        pytest.skip("賣單未成交，跳過")
    tx = flow["sell_tx_row"]
    close_price = flow["today"]["close_price"]
    assert tx and float(tx[0]["exec_price"]) == close_price, f"tx={tx} close_price={close_price}"


# ── 10e-10h. 單檔股票詳細資訊（POST_MARKET） ────────────────────────────


def test_post_market_stock_detail(flow):
    r = flow["post_market_stock_detail"]
    assert r.status_code == 200, r.text
    detail = r.json()
    today = flow["today"]

    assert detail.get("current_price") == today["close_price"], detail
    assert detail.get("open_price") == today["open_price"], detail
    assert detail.get("high_price") == today["high_price"], detail
    assert detail.get("low_price") == today["low_price"], detail
    assert detail.get("close_price") == today["close_price"], detail
    assert detail.get("volume") == today["volume"], detail

    ref_price = today["ref_price"]
    if ref_price is not None:
        expected_change = round(today["close_price"] - ref_price, 2)
        expected_pct = round(expected_change / ref_price * 100, 2) if ref_price else 0.0
        assert detail.get("price_change") == expected_change, f"detail={detail} ref_price={ref_price}"
        assert detail.get("price_change_percent") == expected_pct, f"detail={detail} ref_price={ref_price}"


# ── 11. 盤後僅限定價交易 ────────────────────────────────────────────────


def test_post_market_rejects_limit_order(flow):
    assert flow["post_market_limit_reject"].status_code >= 400, flow["post_market_limit_reject"].text


def test_post_market_allows_market_order(flow):
    assert flow["post_market_order"].status_code == 201, flow["post_market_order"].text


# ── 12. 推進：盤後 -> 收市 ──────────────────────────────────────────────


def test_advance_post_market_to_closed(flow):
    r = flow["advance_to_closed"]
    assert r.status_code == 200, r.text
    assert r.json().get("current_phase") == "CLOSED", r.json()


def test_closed_phase_rejects_orders(flow):
    assert flow["closed_order_reject"].status_code >= 400, flow["closed_order_reject"].text


# ── 12d-12f. 單檔股票詳細資訊（CLOSED） ─────────────────────────────────


def test_closed_stock_detail(flow):
    r = flow["closed_stock_detail"]
    assert r.status_code == 200, r.text
    detail = r.json()
    today = flow["today"]

    assert detail.get("current_price") == today["close_price"], detail
    assert detail.get("open_price") == today["open_price"], detail
    assert detail.get("high_price") == today["high_price"], detail
    assert detail.get("low_price") == today["low_price"], detail
    assert detail.get("close_price") == today["close_price"], detail
    assert detail.get("volume") == today["volume"], detail


# ── 13. 持股 / 成交紀錄查詢 ─────────────────────────────────────────────


def test_list_holdings(flow):
    assert flow["list_holdings"].status_code == 200, flow["list_holdings"].text


def test_list_transactions(flow):
    assert flow["list_transactions"].status_code == 200, flow["list_transactions"].text


# ── 14. 自選股 ───────────────────────────────────────────────────────


def test_add_to_watchlist(flow):
    assert flow["watchlist_add"].status_code == 201, flow["watchlist_add"].text


def test_watchlist_contains_stock(flow):
    r = flow["watchlist_list"]
    assert r.status_code == 200, r.text
    assert any(w.get("stock_id") == STOCK_ID for w in r.json()), r.text


def test_remove_from_watchlist(flow):
    assert flow["watchlist_remove"].status_code == 204, flow["watchlist_remove"].text


# ── 15. 推進：收市 -> 下一交易日盤前 ─────────────────────────────────────


def test_advance_closed_to_next_day(flow):
    r = flow["advance_to_next_day"]
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("current_phase") == "PRE_MARKET", data
    assert str(data.get("current_trade_date")) > START_DATE, data


def test_post_market_order_settled_after_next_day(flow):
    if not flow["post_order_id"]:
        pytest.skip("沒有盤後定價單，跳過")
    rows = flow["post_market_order_row"]
    assert rows and rows[0]["status"] in ("FILLED", "EXPIRED"), rows


# ── 16. 登出 / session 失效 ─────────────────────────────────────────────


def test_logout(flow):
    assert flow["logout"].status_code == 200, flow["logout"].text


def test_session_rejected_after_logout(flow):
    assert flow["old_session_get_save"].status_code == 401, flow["old_session_get_save"].text
