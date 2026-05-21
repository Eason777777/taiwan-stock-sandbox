# 錢錢錢市 — 股票模擬系統

以台灣股市真實歷史資料為基礎的虛擬交易模擬器。  
使用者可選擇一個歷史起始日期，逐日推進時間，以歷史 OHLC 價格進行無風險的模擬交易。

---

## 啟動 API Server

```sh
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Server 預設跑在 `http://localhost:8000`。  
互動式文件（Swagger UI）：`http://localhost:8000/docs`

> DB 透過 Tailscale 連線至 `mysql.shiragaserver.lan`，必須在 Tailscale 網路中才能正常運作。

---

## 認證

除了 `/auth/register` 與 `/auth/login` 之外，所有 API 都需要在 Header 帶上登入後取得的 session token：

```
X-Session-Id: <your_session_id>
```

同一帳號每次登入都會產生新的 token，舊 token 立即失效（強制單一登入）。

---

## API 說明

以下範例的 Base URL 為 `http://localhost:8000`，  
`SESSION` 代表登入後取得的 `session_id`。

---

### 認證 `/auth`

#### 註冊

```sh
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"account": "alice", "password": "mypassword"}'
```

#### 登入

```sh
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account": "alice", "password": "mypassword"}'
```

回應範例：
```json
{"session_id": "abc123..."}
```

#### 登出

```sh
curl -X POST http://localhost:8000/auth/logout \
  -H "X-Session-Id: $SESSION"
```

---

### 模擬存檔 `/saves`

每個存檔是一次獨立的模擬，擁有各自的時間軸、資金與持股，互不影響。

#### 建立存檔

```sh
curl -X POST http://localhost:8000/saves \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: $SESSION" \
  -d '{
    "save_name": "我的第一次模擬",
    "start_date": "2020-01-02",
    "initial_savings": 1000000,
    "initial_trading": 0
  }'
```

- `start_date`：模擬起始日（YYYY-MM-DD），需為台股交易日
- `initial_savings`：存款戶初始金額（元）
- `initial_trading`：交割戶初始金額（元）

#### 列出所有存檔

```sh
curl http://localhost:8000/saves \
  -H "X-Session-Id: $SESSION"
```

#### 查看單一存檔

```sh
curl http://localhost:8000/saves/1 \
  -H "X-Session-Id: $SESSION"
```

回應範例：
```json
{
  "save_id": 1,
  "save_name": "我的第一次模擬",
  "current_date": "2020-01-02",
  "current_phase": "盤前",
  "status": "進行中",
  "savings_balance": 1000000,
  "trading_balance": 0
}
```

#### 推進時間

每次呼叫推進一個階段，順序為：**盤前 → 盤中 → 盤後 → 下一日盤前**。

盤後結束時，系統自動撮合當日委託，並讓未成交委託失效。

```sh
curl -X POST http://localhost:8000/saves/1/advance \
  -H "X-Session-Id: $SESSION"
```

#### 刪除存檔

```sh
curl -X DELETE http://localhost:8000/saves/1 \
  -H "X-Session-Id: $SESSION"
```

---

### 帳戶與資金 `/saves/{save_id}/accounts`

每個存檔有兩個帳戶：**存款戶**（閒置資金）與**交割戶**（股票買賣專用）。  
買股只會從交割戶扣款，因此需要先將資金轉入交割戶。

#### 轉帳

```sh
# 存款戶 → 交割戶
curl -X POST http://localhost:8000/saves/1/accounts/transfer \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: $SESSION" \
  -d '{"direction": "savings_to_trading", "amount": 500000}'

# 交割戶 → 存款戶
curl -X POST http://localhost:8000/saves/1/accounts/transfer \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: $SESSION" \
  -d '{"direction": "trading_to_savings", "amount": 100000}'
```

#### 查看帳戶異動紀錄

```sh
curl http://localhost:8000/saves/1/accounts/history \
  -H "X-Session-Id: $SESSION"
```

---

### 股票查詢 `/stocks`

#### 搜尋股票

```sh
# 以股票代號或名稱搜尋
curl "http://localhost:8000/stocks?q=台積電" \
  -H "X-Session-Id: $SESSION"

# 以類股篩選
curl "http://localhost:8000/stocks?sector=半導體業" \
  -H "X-Session-Id: $SESSION"
```

#### 查看股票基本資料

```sh
curl http://localhost:8000/stocks/2330 \
  -H "X-Session-Id: $SESSION"
```

#### 查看歷史價格（K 線資料）

```sh
# 不指定日期範圍則回傳全部
curl "http://localhost:8000/stocks/2330/prices?from_date=2020-01-01&to_date=2020-03-31" \
  -H "X-Session-Id: $SESSION"
```

回應範例：
```json
[
  {
    "trade_date": "2020-01-02",
    "open": 330.0,
    "high": 335.0,
    "low": 328.0,
    "close": 333.0,
    "volume": 28451,
    "limit_up": 363.0,
    "limit_down": 297.0
  }
]
```

---

### 委託下單 `/saves/{save_id}/orders`

下單僅在**盤前**或**盤中**階段有效。所有委託為當日有效（ROD），收盤後未成交自動失效。  
委託價格須在當日漲跌停範圍內。買進須有足夠的交割戶餘額，否則拒絕成交。

#### 掛限價買單

```sh
curl -X POST http://localhost:8000/saves/1/orders \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: $SESSION" \
  -d '{
    "stock_id": "2330",
    "order_type": "限價",
    "side": "買",
    "price": 330.0,
    "quantity": 1
  }'
```

- `quantity`：單位為**張**（1 張 = 1,000 股），最小為 1

#### 掛市價賣單

```sh
curl -X POST http://localhost:8000/saves/1/orders \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: $SESSION" \
  -d '{
    "stock_id": "2330",
    "order_type": "市價",
    "side": "賣",
    "quantity": 1
  }'
```

- 市價單不需要填 `price`，系統以當日最高與最低價之間的隨機價格成交

#### 查看所有委託

```sh
curl http://localhost:8000/saves/1/orders \
  -H "X-Session-Id: $SESSION"
```

#### 撤銷委託（僅限待成交狀態）

```sh
curl -X DELETE http://localhost:8000/saves/1/orders/42 \
  -H "X-Session-Id: $SESSION"
```

---

### 持股與損益 `/saves/{save_id}/holdings`

#### 查看目前持股

```sh
curl http://localhost:8000/saves/1/holdings \
  -H "X-Session-Id: $SESSION"
```

回應範例：
```json
[
  {
    "stock_id": "2330",
    "stock_name_zh": "台積電",
    "quantity": 2,
    "avg_cost": 328.5,
    "current_price": 345.0,
    "unrealized_pnl": 33000
  }
]
```

#### 查看歷史成交紀錄

```sh
curl http://localhost:8000/saves/1/holdings/transactions \
  -H "X-Session-Id: $SESSION"
```

---

### 自選股 `/saves/{save_id}/watchlist`

#### 查看自選清單

```sh
curl http://localhost:8000/saves/1/watchlist \
  -H "X-Session-Id: $SESSION"
```

#### 加入自選

```sh
curl -X POST http://localhost:8000/saves/1/watchlist \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: $SESSION" \
  -d '{"stock_id": "2454"}'
```

#### 移除自選

```sh
curl -X DELETE http://localhost:8000/saves/1/watchlist/2454 \
  -H "X-Session-Id: $SESSION"
```

---

## 典型使用流程

```
1. 註冊 / 登入              →  取得 session_id
2. 建立模擬存檔              →  設定起始日期與初始資金
3. 存款戶轉帳至交割戶        →  準備交易資金
4. 搜尋股票 / 查看 K 線      →  選股研究
5. 盤前 / 盤中階段下單       →  掛限價或市價委託
6. POST /advance            →  推進至下一階段
   （重複直到盤後）
7. 盤後自動撮合              →  系統依歷史價格決定成交與否
8. POST /advance            →  進入下一個交易日
9. 查看持股與損益            →  檢視操作成效
```
