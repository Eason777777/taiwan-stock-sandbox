# 錢錢錢市 後端 API 文件

提供給前端開發人員參考。所有需要登入的 API 皆須在 request header 帶上：

```
X-Session-Id: <login 回傳的 session_id>
```

未帶或無效（包含過期、來源網段不符）回傳 `401 Not authenticated`。

通用錯誤格式：

```json
{ "detail": "錯誤訊息" }
```

---

## 一、Auth（/auth）

### POST /auth/register
建立新帳號。

- Body: `{ "account": "string", "password": "string" }`
- 201: `{ "message": "註冊成功" }`
- 409: 帳號已存在
- 422: 帳號或密碼空白 / 長度超過限制（account ≤ 50, password ≤ 72）

### POST /auth/login
登入，取得 session_id。同一帳號重複登入會覆蓋舊 session（單一登入）。

- Body: `{ "account": "string", "password": "string" }`
- 200: `{ "session_id": "string" }`
- 401: 帳號或密碼錯誤
- 429: 同帳號 60 秒內失敗次數過多（≥5 次），請稍後再試

> session 有效期 2 小時（伺服器端以 DB 時間計算），且綁定登入時的來源 IP（放寬至同一 /24 網段）。從不同網段使用同一個 session_id 會被拒絕（401）。

### POST /auth/logout
登出（需登入），清除 session。

- 200: `{ "message": "已登出" }`

---

## 二、存檔管理（/saves）

存檔物件（save object）共通欄位：

```json
{
  "save_id": 1,
  "user_id": 1,
  "save_name": "string",
  "start_date": "YYYY-MM-DD",
  "current_trade_date": "YYYY-MM-DD",
  "current_phase": "PRE_MARKET | INTRADAY | POST_MARKET | CLOSED",
  "status": "ACTIVE | BANKRUPT | FINISHED",
  "savings_balance": 0,
  "trading_balance": 0,
  "total_asset": 0,
  "cumulative_return": 0
}
```

### GET /saves
列出當前使用者所有存檔（含 total_asset / cumulative_return）。

- 200: `[ save object, ... ]`

### POST /saves
建立新存檔。

- Body:
  ```json
  {
    "save_name": "string",
    "start_date": "YYYY-MM-DD",        // 可省略，省略則隨機抽取有效交易日
    "initial_funds": 100000            // 可省略，省略則隨機 50,000~1,000,000
  }
  ```
- 201: save object
- 400: 起始日期超出資料庫範圍 / 非有效交易日 / 進行中存檔已達上限(5) / 存檔總數已達上限(10)
- 409: 同名存檔已存在
- 422: initial_funds 超出 50,000~1,000,000

### GET /saves/{save_id}
取得單一存檔詳情。

- 200: save object
- 403: 非本人存檔
- 404: 存檔不存在

### PATCH /saves/{save_id}/finish
玩家主動結束存檔（狀態轉為 FINISHED，封存）。

- 200: save object（status 為 FINISHED）
- 400: 存檔已非 ACTIVE，無法再次結束

### DELETE /saves/{save_id}
刪除存檔（連同委託單、交易紀錄、持股、帳務紀錄、自選股一併刪除）。

- 204: 無內容

### POST /saves/{save_id}/advance
推進一個交易階段（會結算上一階段的 PENDING 委託單）。

階段順序：`PRE_MARKET -> INTRADAY -> POST_MARKET -> CLOSED -> 下一交易日 PRE_MARKET`（或 `FINISHED`，若已無下一交易日）。

- 200:
  ```json
  {
    "current_phase": "PRE_MARKET | INTRADAY | POST_MARKET | CLOSED",
    "current_trade_date": "YYYY-MM-DD",
    "status": "ACTIVE | BANKRUPT | FINISHED"
  }
  ```
- 400: 存檔已非 ACTIVE，無法推進

> 若結算後交割戶餘額不足（買單成交但現金不夠），存檔會直接轉為 `BANKRUPT`，且當次未完成的結算會中止。

---

## 三、資金帳戶（/saves/{save_id}/accounts）

### GET /saves/{save_id}/accounts/history
取得帳務紀錄（存款戶/交割戶異動歷史）。

- Query: `limit`(預設100, 1~500), `offset`(預設0)
- 200: `[ { seq, account_type, sim_date, change_type, amount, balance_after, note, ... }, ... ]`

### POST /saves/{save_id}/accounts/transfer
存款戶 <-> 交割戶 即時轉帳（無手續費）。

- Body: `{ "direction": "savings_to_trading" | "trading_to_savings", "amount": 1000 }`
- 200: `{ "savings_balance": 0, "trading_balance": 0 }`
- 400: 餘額不足
- 422: amount <= 0 或 direction 不合法

---

## 四、股票查詢（/stocks）

### GET /stocks
搜尋股票。

- Query:
  - `q`: 關鍵字（比對 stock_id / stock_name_zh / stock_full_name_zh）
  - `sector`: 依產業分類精確比對 sector_name
  - `limit`: 預設 50, 1~500
- 200: `[ { stock_id, stock_name_zh, stock_full_name_zh, market_type, sector_name, listing_date }, ... ]`

### GET /stocks/{stock_id}
取得單一股票基本資料。

- 200: stocks 表完整欄位
- 404: 股票不存在

### GET /stocks/{stock_id}/prices
取得 K 線歷史價格（僅回傳該存檔目前交易日「以前」的資料，符合時空隔離原則）。

- Query:
  - `save_id`（必填）：存檔 ID，用來決定時空隔離的截止日
  - `from_date` / `to_date`：`YYYY-MM-DD`，篩選回傳範圍（在指標計算之後套用，不影響指標回溯資料）
  - `interval`：`day`(預設) | `week` | `month`，K 線週期
  - `indicators`：逗號分隔的技術指標清單，支援：
    - `maN`：N 日移動平均線，如 `ma5`, `ma20`
    - `rsiN`：N 日 RSI（Wilder's smoothing），如 `rsi14`
    - `macd`：MACD（12/26/9 EMA），會附帶 `macd` / `macd_signal` / `macd_hist`
- 200: 每筆資料：
  ```json
  {
    "stock_id": "2330",
    "trade_date": "YYYY-MM-DD",
    "open_price": 0, "high_price": 0, "low_price": 0, "close_price": 0,
    "volume": 0,
    "ref_price": 0, "limit_up": 0, "limit_down": 0,
    "is_attention": 0, "is_disposition": 0, "is_full_delivery": 0,

    "ma5": 0,            // 有指定 indicators 才有；資料不足時為 null
    "rsi14": 0,
    "macd": 0, "macd_signal": 0, "macd_hist": 0
  }
  ```
  > 週/月 K（`interval=week|month`）聚合後的欄位僅含 `stock_id, trade_date, open_price, high_price, low_price, close_price, volume`，不含 `ref_price/limit_up/limit_down/is_*`。
- 403: 該存檔非本人所有
- 404: 股票不存在 / 存檔不存在

---

## 五、委託與成交（/saves/{save_id}/orders）

委託單物件：

```json
{
  "order_id": 1,
  "save_id": 1,
  "stock_id": "2330",
  "sim_date": "YYYY-MM-DD",
  "phase": "PRE_MARKET | INTRADAY | POST_MARKET",
  "order_type": "LIMIT | MARKET",
  "side": "BUY | SELL",
  "price": 0,            // MARKET 為 null
  "quantity": 1,          // 張數
  "status": "PENDING | FILLED | CANCELED | EXPIRED"
}
```

### GET /saves/{save_id}/orders
列出委託單（含已成交/已撤銷/已失效）。

- Query: `limit`(預設100, 1~500), `offset`(預設0)
- 200: `[ 委託單物件, ... ]`（依 order_id 新到舊排序）

### POST /saves/{save_id}/orders
下單。

- Body:
  ```json
  {
    "stock_id": "2330",
    "order_type": "LIMIT | MARKET",
    "side": "BUY | SELL",
    "price": 600,        // LIMIT 必填；MARKET 必須為 null/不傳
    "quantity": 1         // 張數，>= 1
  }
  ```
- 201: 委託單物件（status = PENDING）
- 400:
  - 存檔已結束（非 ACTIVE）
  - 收市階段無法下單；盤前僅限限價單；盤後僅限定價單（MARKET）
  - 股票於當前日期尚未上市 / 處於停牌狀態
  - 當前日期無此股票報價
  - 限價單價格超出當日漲跌停範圍
  - 交割戶餘額不足以支應買單（依限價或當日最高價估算）
  - 持股不足以支應賣單（= 持股 - 同股票同方向尚未成交的賣單張數）
- 403: 該存檔非本人所有
- 404: 存檔不存在 / 股票不存在
- 422:
  - order_type / side 不合法
  - quantity < 1
  - LIMIT 單未指定 price / MARKET 單指定了 price
  - 限價單價格不符合升降單位規則（見下表）

升降單位（限價單）：

| 股價範圍 | 升降單位 |
| --- | --- |
| < 10 | 0.01 |
| 10 ~ < 50 | 0.05 |
| 50 ~ < 100 | 0.1 |
| 100 ~ < 500 | 0.5 |
| 500 ~ < 1000 | 1 |
| >= 1000 | 5 |

### DELETE /saves/{save_id}/orders/{order_id}
撤銷委託單（僅限 PENDING 狀態）。

- 204: 無內容
- 400: 僅能撤銷待成交（PENDING）的委託單
- 404: 委託單不存在

---

## 六、持股與成交紀錄（/saves/{save_id}/holdings）

### GET /saves/{save_id}/holdings
取得目前持股清單（含市值與未實現損益）。市價依目前交易階段取對應基準價（盤前=前日收盤、盤中=當日開盤、盤後/收市=當日收盤）。

- 200:
  ```json
  [
    {
      "stock_id": "2330",
      "stock_name_zh": "台積電",
      "quantity": 1,
      "avg_cost": 0,
      "market_price": 0,        // 無報價時為 null
      "cost_value": 0,
      "market_value": 0,         // 無報價時為 null
      "unrealized_pnl": 0,       // 無報價時為 null
      "unrealized_pnl_pct": 0    // 無報價時為 null
    }
  ]
  ```

### GET /saves/{save_id}/holdings/transactions
取得已成交的買賣紀錄（依交易明細表）。

- Query: `limit`(預設100, 1~500), `offset`(預設0)
- 200: `[ { transaction_id, order_id, stock_id, stock_name_zh, side, order_type, sim_date, exec_price, quantity, fee, tax, avg_cost_at_transact }, ... ]`（依 transaction_id 新到舊排序）

---

## 七、自選股（/saves/{save_id}/watchlist）

### GET /saves/{save_id}/watchlist
取得自選股清單。

- 200: `[ { stock_id, stock_name_zh, market_type, sector_name }, ... ]`

### POST /saves/{save_id}/watchlist
加入自選股（已存在則無動作，不會重複）。

- Body: `{ "stock_id": "2330" }`
- 201: `{ "save_id": 1, "stock_id": "2330" }`
- 400: 自選股已達上限（100）
- 404: 股票不存在

### DELETE /saves/{save_id}/watchlist/{stock_id}
移除自選股。

- 204: 無內容

---

## 備註

- 所有金額單位為「元」；委託 `quantity` 單位為「張」（=1000 股）。
- 所有「目前交易日以前」之資料判定皆以該存檔的 `current_trade_date` 為基準，前端不應另行快取跨存檔資料。
- CORS 已全開（開發環境），前端可直接從瀏覽器呼叫。
