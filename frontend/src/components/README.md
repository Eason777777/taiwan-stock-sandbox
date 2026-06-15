# Frontend Components 目錄與元件說明文件

本文件旨在整理並分類說明 `frontend/src/components` 資料夾內的所有 Vue 元件，以便於後續維護、開發與架構優化。

---

## 📂 元件分類總覽

目前元件共分為 7 大類，主要遵循自然風格（Nature Theme）的 UI 設計規範。

### 1. 💾 遊戲存檔管理 (Save Management)
管理玩家帳號底下的存檔，提供存檔建立、選擇及移除。

| 元件名稱 | 功能說明 |
| :--- | :--- |
| **[AddSave.vue](./AddSave.vue)** | **新增存檔彈窗**：輸入存檔名稱、初始金額、開始日期等欄位並呼叫 API 建立新存檔。 |
| **[RemoveSave.vue](./RemoveSave.vue)** | **刪除存檔確認彈窗**：提供列表顯示當前所有存檔與統計數據，並可進行存檔的物理刪除。 |
| **[SaveRecords.vue](./SaveRecords.vue)** | **存檔卡片**：玩家登入後，用來選擇、建立或管理存檔的主要卡片元件。 |
| **[SavefileRecords.vue](./SavefileRecords.vue)** | **存檔歷史統計紀錄**：用於紀錄頁面中，以表格展示各存檔的資產、報酬率等基本概況。 |

---

### 2. 📈 下單與交易控制面板 (Stock Trading Panel)
提供股票搜尋、委託價格與張數設定、K線圖繪製以及個人委託單管理。

| 元件名稱 | 功能說明 |
| :--- | :--- |
| **[OrderCard.vue](./OrderCard.vue)** | **交易核心卡片**：整合股票搜尋、K線圖、下單操作與當前委託單列表的大型容器卡片。 |
| **[BuySellSlider.vue](./BuySellSlider.vue)** | **買進/賣出切換滑桿**：精美的左右滑動控制鈕，用於切換交易方向。 |
| **[OrderTypeSlider.vue](./OrderTypeSlider.vue)** | **委託類型切換滑桿**：切換市價單 (MARKET)、限價單 (LIMIT) 及 盤後定價單 (POST_MARKET)。 |
| **[StockInput.vue](./StockInput.vue)** | **股票輸入框**：具備輸入自動補全、列表選取及顯示股票中文簡稱與即時價格的功能。 |
| **[CandlestickChart.vue](./CandlestickChart.vue)** | **K線圖畫布組件**：基於 `klinecharts` Canvas 繪圖庫，處理股票歷史價量走勢的呈現。 |
| **[OrderHistory.vue](./OrderHistory.vue)** | **當前委託紀錄清單**：嵌入在下單卡片底部，展示當前存檔的委託單，支援互斥篩選及撤單操作。 |

---

### 3. 💼 帳戶資產與持股明細 (Assets & Holdings)
展示個人資產分佈、交割戶／存款帳戶餘額以及目前的股票持股明細。

| 元件名稱 | 功能說明 |
| :--- | :--- |
| **[InventoryCard.vue](./InventoryCard.vue)** | **庫存卡片容器**：整合帳戶資金 (`AccountInfo`) 與持股明細明細表 (`HoldingInfo`) 的外層包裝。 |
| **[AccountInfo.vue](./AccountInfo.vue)** | **帳戶資金概況**：展示證券交割帳戶、銀行存款帳戶之餘額，並包含轉帳功能按鈕。 |
| **[HoldingInfo.vue](./HoldingInfo.vue)** | **持股明細明細表**：以表格顯示持有個股、股數、平均成本、即時現價、未實現損益與報酬率。 |

---

### 4. ⭐ 自選股管理 (Watchlist)
提供自選股票的管理與行情即時監控。

| 元件名稱 | 功能說明 |
| :--- | :--- |
| **[WatchlistCard.vue](./WatchlistCard.vue)** | **自選股卡片**：展示玩家追蹤的自選股即時股價、漲跌幅，並提供快捷按鈕一鍵前往下單。 |
| **[AddWatchlist.vue](./AddWatchlist.vue)** | **新增自選股彈窗**：提供依「產業別分類」篩選與複選框，讓玩家批量將個股加入自選清單。 |

---

### 5. 🏢 公司與個股詳細資訊 (Company & Stock Info)
提供個股五檔報價以及公司基本面與財務歷史數據。

| 元件名稱 | 功能說明 |
| :--- | :--- |
| **[StockInfo.vue](./StockInfo.vue)** | **即時個股資訊**：顯示當日開高低收、成交量能，以及買賣委託五檔排隊狀態。 |
| **[CompanyInfo.vue](./CompanyInfo.vue)** | **公司基本面彈窗**：展示公司簡介、產業別、前十大股東明細以及歷年股利分派歷史紀錄。 |

---

### 6. 📜 歷史紀錄查詢 (History Records)
供玩家追溯過去所有已結算成交的歷史交易及轉帳紀錄。

| 元件名稱 | 功能說明 |
| :--- | :--- |
| **[OrderRecords.vue](./OrderRecords.vue)** | **歷史成交交易紀錄**：在「紀錄」分頁展示所有已成交的歷史買賣紀錄，並加總已實現損益。 |
| **[TransactRecords.vue](./TransactRecords.vue)** | **帳戶轉帳紀錄**：以明細方式記錄交割帳戶與存款帳戶間歷次轉入、轉出與結餘的變化。 |
| **[RecordSelect.vue](./RecordSelect.vue)** | **紀錄分頁切換鈕**：用於紀錄頁面頂部，供玩家點擊展開選單。 |
| **[RecordSelectBox.vue](./RecordSelectBox.vue)** | **下拉紀錄選單項目**：在下拉清單中渲染單個選單按鈕（如：交易紀錄、轉帳紀錄、存檔紀錄）。 |

---

### 7. 🛠️ 全域通用與彈窗通知 (Global Utilities & Modals)
控制主時間推進、錯誤攔截、交易結算提示與全域通用組件。

| 元件名稱 | 功能說明 |
| :--- | :--- |
| **[TopBar.vue](./TopBar.vue)** | **頂部導覽列**：展示當前遊戲日期、交易階段 (Phase)，並包含「進一步」時空推進鈕與登出按鈕。 |
| **[Toast.vue](./Toast.vue)** | **全域 Toast 提示**：自訂的全域浮動通知元件，取代瀏覽器預設 `alert()`，提供 info, success, warning, error 四種狀態。 |
| **[ConfirmModal.vue](./ConfirmModal.vue)** | **自訂確認對話框**：統一的 Nature 風格二選一對話框，用於取代瀏覽器原生 `confirm()`。 |
| **[TransferOverlap.vue](./TransferOverlap.vue)** | **資金互轉彈窗**：存款戶與交割戶之間轉帳的操作界面，支援防呆金額檢查。 |
| **[TradeSettlementModal.vue](./TradeSettlementModal.vue)** | **時空推進結算彈窗**：時間前進後，用以彙整並通知玩家本次有多少委託單成功撮合成交，以及增減金額。 |
| **[SessionExpiredModal.vue](./SessionExpiredModal.vue)** | **憑證過期通知**：監聽到 API 401 錯誤時，彈出強制的重新登入對話框。 |
| **[Input.vue](./Input.vue)** | **基礎文字輸入框**：專案統一封裝的 Label / Input 輸入框元件。 |
