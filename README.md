# 錢錢錢市 — 股票模擬系統

以台灣股市真實歷史資料為基礎的虛擬交易模擬器。
玩家可自由選擇歷史時間起點，在「平行宇宙」中逐階段推進虛擬時間，以歷史價格進行無風險的模擬交易，練習投資策略。

系統核心強調 **時空隔離**（玩家無法利用未來資訊套利）與 **邏輯防呆**（在簡化的 MVP 模型下維持金融運作的嚴謹性）。

---

[常用/參考的連結們](./docs/links.md)

完整規則請見 [錢錢錢市 股票模擬系統 規則 V1](./docs/錢錢錢市%20股票模擬系統%20規則%20V1.md)。

---

## 此版本範圍

本版本為 MVP，**不考慮** 以下機制：除權息、減資、T+2 交割、融資融券、選擇權／期貨等複雜金融工具、圈存交易、IOC／FOK 等特殊委託、零股交易、部分成交。

所有規則若與真實市場細節衝突，以規則白皮書之 MVP 規則為準。

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

支援玩家自助註冊：輸入帳號（account）與密碼（password），系統檢查後即註冊成功。

除了 `/auth/register` 與 `/auth/login` 之外，所有 API 都需要在 Header 帶上登入後取得的 session token：

```
X-Session-Id: <your_session_id>
```

**單一登入原則**：同一帳號同一時間僅允許一組有效登入憑證。同一帳號再次登入會覆蓋前一次的憑證，舊 token 立即失效（避免異地登入與異地操作）。

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

#### 測試指令

```sh
# 1. 註冊
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"account": "testuser", "password": "mypassword"}'

# 2. 重複註冊（預期 409）
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"account": "testuser", "password": "mypassword"}'

# 3. 登入
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account": "testuser", "password": "mypassword"}'

# 4. 登入後登出（將上一步拿到的 session_id 帶入）
SESSION_ID="<上一步拿到的 session_id>"
curl -s -X POST http://localhost:8000/auth/logout \
  -H "X-Session-Id: $SESSION_ID"
```

一行完成完整流程：

```sh
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"account": "testuser", "password": "mypassword"}'

SESSION_ID=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account": "testuser", "password": "mypassword"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

echo "session_id: $SESSION_ID"

curl -s -X POST http://localhost:8000/auth/logout \
  -H "X-Session-Id: $SESSION_ID"
```

---

### 模擬存檔 `/saves`

每個存檔是一次獨立的模擬，其資產、庫存、委託單、交易紀錄、自選股皆完全獨立，不得跨存檔存取。

**建檔限制**

- 每位玩家最多 **5** 個「進行中（ACTIVE）」存檔。
- 每位玩家最多保留 **10** 個存檔（含進行中、已破產、已結束）。
- 同一玩家不可建立同名存檔。

**初始日期與資金**

- 起點日期不得早於資料庫最早紀錄、不得晚於最後可用交易日，且必須是有效交易日（無交易日的日期會被拒絕）。
- 可選擇由系統隨機抽取一個有效歷史交易日作為起點。
- 起始資金範圍為 **50,000 ~ 1,000,000** 元，亦可由系統隨機決定。
- 初始資金於建檔時全數配發至 **存款戶**。

**存檔生命週期（status）**

- `ACTIVE`：進行中，可正常推進時間與交易。
- `BANKRUPT`：已破產。無法再交易或推進時間，僅能查詢、刪除或封存。
- `FINISHED`：玩家手動結束並封存，不可再恢復進行。

**存檔列表揭露資訊**：存檔名稱、當前虛擬日期、總資產價值、累積報酬率、存檔狀態。

- 總資產價值 = 存款戶餘額 + 交割戶餘額 + 持股市值
- 累積報酬率 = (目前總資產 − 初始資金) / 初始資金

#### 建立存檔

```sh
curl -X POST http://localhost:8000/saves \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: $SESSION" \
  -d '{
    "save_name": "我的第一次模擬",
    "start_date": "2020-01-02",
    "initial_funds": 1000000
  }'
```

- `save_name`：存檔名稱（同一玩家不可重複）
- `start_date`：模擬起始日（YYYY-MM-DD），需為有效台股交易日
- `initial_funds`：起始資金（元），範圍 50,000 ~ 1,000,000，全數配發至存款戶

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
  "status": "ACTIVE",
  "savings_balance": 1000000,
  "trading_balance": 0,
  "total_asset": 1000000,
  "cumulative_return": 0.0
}
```

#### 推進時間

每次呼叫推進一個階段，順序固定為：**盤前 → 盤中 → 盤後 → 收市 → 下一有效交易日盤前**。
一旦推進時間，不可回到過去日期。

每次推進都會結算「上一階段送出且尚未結算的委託單」（詳見 [撮合邏輯](#撮合邏輯)）。

```sh
curl -X POST http://localhost:8000/saves/1/advance \
  -H "X-Session-Id: $SESSION"
```

#### 刪除存檔

```sh
curl -X DELETE http://localhost:8000/saves/1 \
  -H "X-Session-Id: $SESSION"
```

刪除後該存檔資料自系統移除，並釋放存檔名額。

---

## 虛擬時間與交易階段

| 階段 | 虛擬時間 | 系統行為限制 |
| --- | --- | --- |
| 盤前 | 08:30 – 09:00 | 允許掛**限價單**與撤單，不進行成交 |
| 盤中 | 09:00 – 13:30 | 允許掛**限價單、市價單**與撤單 |
| 盤後 | 14:00 – 14:30 | 僅允許**定價交易**，成交價固定使用收盤價 |
| 收市 | 14:30 以後 | 鎖定所有交易功能，僅供查詢報價、損益與推進時間 |

**當日可見資訊**：任一時間點僅可查詢當前虛擬日期以前已揭露之資訊；尚未經過之盤中、盤後或收市結果不得提前顯示。

---

## 資金與帳戶架構 `/saves/{save_id}/accounts`

每個存檔有兩個帳戶：

- **存款戶（Savings）**：存放暫時不投入交易之資金。
- **交割戶（Trading）**：所有證券買賣的扣款與入帳皆透過此帳戶。

兩帳戶間可即時轉帳，無手續費。買股只會從交割戶扣款，因此需要先將資金轉入交割戶。

**資產估值**：持股市值依當前階段採不同價格估算 ——

- 盤前：以上一有效交易日收盤價估算
- 盤中：以當日開盤價估算
- 盤後／收市：以當日收盤價估算

**交易成本**

- 買進手續費：成交金額 × 0.1425%
- 賣出手續費：成交金額 × 0.1425%
- 賣出證交稅：成交金額 × 0.3%
- 單筆手續費若不足 20 元，以 20 元計

**交割制度**：本版本採 **T+0 瞬間交割**。買入成交立即增加持股並自交割戶扣除成交金額與手續費；賣出成交立即減少持股並將成交金額扣除手續費與證交稅後入帳交割戶。

**餘額原則**：存款戶與交割戶在正常狀態下不得為負；若為負即破產。

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

可交易標的以台股上市、上櫃與資料庫中已定義之標的為限。以下情況不得下單：股票於當前虛擬日期尚未上市、暫停交易，或當前為不允許下單之交易階段。

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

K 線僅顯示**前一交易日以前**的資料；技術指標計算僅能使用當前虛擬日期以前之歷史資料，不得使用未來資料。
支援日線、週線、月線；副圖成交量週期需與主圖一致。

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

下單須在允許的交易階段送出。所有委託皆為當日有效（ROD）、整股交易，且只有「全部成交」或「全部不成交」兩種結果（不支援部分成交）。委託可於對應撮合前主動撤單。

**各階段可下單類型**

| 階段 | 可下單類型 |
| --- | --- |
| 盤前 | 限價單 |
| 盤中 | 限價單、市價單 |
| 盤後 | 定價交易（成交價固定為收盤價） |

**限價單價格限制**：須符合台股升降單位，且不得高於當日漲停價、不得低於當日跌停價。

| 股價範圍 | 升降單位 |
| --- | --- |
| 未滿 10 元 | 0.01 元 |
| 10 ~ 未滿 50 元 | 0.05 元 |
| 50 ~ 未滿 100 元 | 0.1 元 |
| 100 ~ 未滿 500 元 | 0.5 元 |
| 500 ~ 未滿 1000 元 | 1 元 |
| 1000 元以上 | 5 元 |

**賣單檢查**：買單允許下單時不先圈存現金；賣單不允許超額下單。送出賣單時系統檢查可賣持股是否足夠，不足則拒絕。

> 可賣持股數量 = 現有持股數量 − 同階段尚未結算之賣單總量

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

#### 掛市價賣單（盤中）

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

- 市價單不需要填 `price`，成交價依撮合規則決定（盤中市價以當日收盤價成交）

#### 查看所有委託

```sh
curl http://localhost:8000/saves/1/orders \
  -H "X-Session-Id: $SESSION"
```

#### 撤銷委託（僅限 PENDING 狀態）

```sh
curl -X DELETE http://localhost:8000/saves/1/orders/42 \
  -H "X-Session-Id: $SESSION"
```

只要委託單為 `PENDING` 且該階段尚未開始結算即可撤單；一旦該階段開始結算，當階段所有 `PENDING` 委託即不可再撤。

---

## 撮合邏輯

委託於送出時列入「待成交委託」清單（狀態 `PENDING`），並在玩家推進至**下一階段**時結算。各階段委託的撮合條件與成交價如下：

| 委託 | 撮合時機 | 成交條件 | 實際成交價 |
| --- | --- | --- | --- |
| 盤前 限價買 | 推進至盤中 | 限價 ≥ 當日開盤價 | 當日開盤價 |
| 盤前 限價賣 | 推進至盤中 | 限價 ≤ 當日開盤價 | 當日開盤價 |
| 盤中 限價買 | 推進至盤後 | 限價 ≥ 當日最低價 | 玩家指定限價 |
| 盤中 限價賣 | 推進至盤後 | 限價 ≤ 當日最高價 | 玩家指定限價 |
| 盤中 市價買 | 推進至盤後 | 當日有有效價格 | 當日收盤價 |
| 盤中 市價賣 | 推進至盤後 | 當日有有效價格 | 當日收盤價 |
| 盤後 定價買 | 推進至收市 | 當日有有效收盤價 | 當日收盤價 |
| 盤後 定價賣 | 推進至收市 | 當日有有效收盤價 | 當日收盤價 |

- 盤中限價單不提供價格改善（避免玩家藉歷史最低價取得不合理優勢）。
- 市價／定價單若當日無法交易則該委託失效。
- 買單成交後立即扣除成交金額與手續費；若交割戶不足則破產。
- 賣單成交後立即扣除手續費與證交稅，餘額入帳交割戶。

**委託單狀態**

- `PENDING`：待撮合
- `FILLED`：已成交
- `CANCELED`：玩家主動撤單
- `EXPIRED`：階段結束仍未成交，自動失效

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

自選股清單隸屬個別存檔，不跨存檔共享。同一存檔內同一檔股票不得重複加入，每個存檔最多 **100** 筆。

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

## 遊戲核心循環

本遊戲為沙盒模擬，無絕對勝利條件，主要目標為追求更高的累積報酬率並長期存活。
**破產定義**：交割戶不夠錢支付即破產（存檔狀態轉為 `BANKRUPT`）。

```
登入系統
  → 選擇或建立存檔
  → 研究歷史盤面（查看股價與 K 線圖）
  → 做出買賣決策（盤前 / 盤中 / 盤後下單）
  → 點擊推進時光（盤前 → 盤中 → 盤後 → 收市 → 下一交易日）
  → 檢視撮合結果與損益
  → 重複循環
```
