# Report 4

## 附上 前幾次報告，從系統簡介、ER-diagram 設計、到轉換成SQL relational database create table 的設計。
<!-- 這不須寫，不過我們SQL欄位好像加了不少東西？ -->
## 一、系統安裝說明
### 1.1 系統需求
整體需求概述
|項目|需求|
|--|--|
|Python|3.10 以上|
|Node.js|v20.19.0 或 v22.12.0 以上|
|套件管理|pnpm（前端）、pip（後端）|
|網路|需加入 Tailscale 虛擬私有網路，才能連線至資料庫|
|資料庫|MySQL（透過 HTTP SQL API 存取，地址 sql-api.shiragaserver.lan）|

後端相依套件一覽
|套件|用途|
|--|--|
|fastapi|Web API 框架|
|uvicorn[standard]	|ASGI 伺服器|
httpx	|非同步 HTTP 客戶端（連接 SQL API）
python-dotenv	|載入 .env 環境變數
passlib / bcrypt==4.0.1	|密碼雜湊

前端主要相依套件
|套件	|用途|
|--|--|
vue@3	|UI 框架
vue-router@5|前端路由
klinecharts@9.8.5	|K 線圖繪製（Canvas）
tailwindcss@4	|CSS Utility 框架
vite@8	|開發建置工具
vitest	|單元測試框架
oxlint + eslint	|程式碼 Lint 工具
prettier	|程式碼格式化

### 1.2 後端安裝與啟動（FastAPI）
後端為 FastAPI 應用程式，以 uvicorn 作為 ASGI 伺服器。
```bash
# 1. 複製專案
git clone https://github.com/Eason777777/taiwan-stock-sandbox
cd taiwan-stock-sandbox

# 2. （建議）建立虛擬環境
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# 3. 安裝相依套件
pip install -r requirements.txt

# 4. 設定環境變數（預設已有 .env）
#    若需覆寫 SQL API 位址：
export SQL_API_URL=http://sql-api.shiragaserver.lan

# 5. 啟動開發伺服器
uvicorn app.main:app --reload
docker compose up --build -d # 前後端快速啟動
```
後端預設監聽 http://localhost:8000， 互動式 Swagger 文件位於 http://localhost:8000/docs。
### 1.3 前端安裝與啟動（Vue 3 + Vite）
```bash
cd frontend

# 安裝相依套件（需 pnpm）
pnpm install

# 啟動開發伺服器（http://localhost:5173）
pnpm dev

# 建置正式版
pnpm build
```
Vite 開發伺服器會將 /api/* 代理至後端 http://127.0.0.1:8000， 後端必須同時執行。

### 1.4 驗證連線
```bash
# 測試 Tailscale + SQL API 連線
curl -X POST http://sql-api.shiragaserver.lan/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SHOW DATABASES"}'
```

### 1.5 執行測試
```bash
# 後端單元測試（不需 DB）
pytest tests/unit/

# 後端整合測試（需 Tailscale + 資料庫）
pytest tests/integration/

# 前端單元測試
cd frontend
pnpm test

# 後端 Smoke Test（需先啟動 uvicorn）
pytest backend_tests/test_smoke.py
```
<!-- 希望有人能做好圖文說明 -->

## 二、介面使用說明 系統內容功能詳細敘述
### 2.1 使用者說明
1. **登入 / 註冊：** 前往 `/signup` 建立帳號，再從 `/` 登入。
![image](https://hackmd.io/_uploads/r1xyrEbzzg.png)![image](https://hackmd.io/_uploads/Hygj4EZGMl.png)
2. **建立 / 移除存檔：** 
- 建立存檔：點擊「新增存檔」，填入存檔名稱、初始資金（5 萬至 100 萬元）、歷史起始日（或隨機）。
- 移除存檔：點擊「移除存檔」，會將當前存檔顯示紅色，點擊任意存檔將跳出是否確定移除存檔。
![image](https://hackmd.io/_uploads/B1TBB4Zffg.png)
![image](https://hackmd.io/_uploads/S1vPH4WMMg.png)
![Deleted](https://hackmd.io/_uploads/SkvMJPWMzx.png)
![image](https://hackmd.io/_uploads/HJJXuP-Mfx.png)
3. **研究盤面：** 進入「下單交易」頁或「新增自選股」，搜尋股票，查看 K 線圖（日/週/月線，支援 MA、RSI、MACD 技術指標）。
![image](https://hackmd.io/_uploads/rkaytLZGGg.png)
![image](https://hackmd.io/_uploads/S1EGt8bzfx.png)
4. **資金調撥：** 在「庫存」頁將存款戶資金轉入交割戶，才能下單買股。
![image](https://hackmd.io/_uploads/r11PKUWGMe.png)
![image](https://hackmd.io/_uploads/HJiwKU-fGe.png)
5. **下單：** 依目前交易階段選擇委託類型（限價單 / 市價單 / 定價）並填入股票代號、價格（限價）、張數。
![image](https://hackmd.io/_uploads/SyV-5I-fMl.png)
下單後將建立委託單，等待（下一階段）時是否搓合。
![image](https://hackmd.io/_uploads/B15W4Pbfzg.png)
6. **推進時間：** 點擊頂部導覽列的「進一步」按鈕，系統結算上一階段委託單，時鐘前進至下一階段。
![image](https://hackmd.io/_uploads/BJ0kjL-zGg.png)
7. **檢視結果：** 若有下委託單，點選下一階段時會自動跳出成交結果。若有已購買之股票可以至「資產」查看損益。
![image](https://hackmd.io/_uploads/SJfe2IbfGe.png)
![image](https://hackmd.io/_uploads/HyNfhIWzfe.png)
8. **各項紀錄：** 為方便使用者付盤，在紀錄欄位裡可以找到交易紀錄、轉帳紀錄、存檔紀錄、委託紀錄、資產趨勢供使用者查閱
![image](https://hackmd.io/_uploads/ry1O3LWMMg.png)
9. **Session id 過期提醒：** 基於資安考量，本系統設有 session id，生命週期為兩小時，若有進行任何 API 操作則會重置延長時間，避免影響使用者體驗。過期後會跳出彈窗告知使用者，「長時間未操作，請重新登入」。
![image](https://hackmd.io/_uploads/BJyKjw-Mzg.png)

### 2.2 開發者說明 -- API 測試
得益於 FastAPI，開法者可使用 FastAIP 的 swagger 介面進行 API 呼叫測試
![image](https://hackmd.io/_uploads/SJDOVVWzfx.png)
以 login API 為例，在 Request body 中填入帳號密碼後，點選 Execute 即可在下方的 Response 中看到結果。
![image](https://hackmd.io/_uploads/r1MRbvZffl.png)
![image](https://hackmd.io/_uploads/rJUyzvbzzl.png)
當然，開法者也可以使用下方 `curl` 指令進行測試，但對於前端開發者而言，swagger 可以減少瀏覽器和 Terminal 之間的切換
```bash
curl -X 'POST' \
  'http://localhost:8000/auth/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "account": "alice",
  "password": "mypassword"
}'
```

### 2.3 開發者說明 -- 資料庫管理
本組資料庫部署於本組組員自建之 home server，並採用 Docker 容器化方式進行建置與管理。建置時，先透過 Docker Compose 定義資料庫相關服務，並建立單一 stack；再由 Portainer 匯入並管理該 stack。此 stack 下包含 MySQL 資料庫、Adminer 資料庫管理介面、Node.js API 服務與資料庫自動備份服務等 container，使資料庫相關服務能以同一組設定進行啟動、停止、更新與維護。

在使用上，開發者若需要維護資料庫，需先透過 Tailscale VPN 連入私有網路，再連接至 home server 的相關服務。伺服器端搭配自架 DNS 與 Nginx 進行連線與服務轉發管理，使不同服務能依照設定導向指定的內部服務或管理介面。透過此方式，開發者可在非本地網路環境下進行遠端維護，同時避免將所有管理服務直接暴露於公開網路。

進入管理環境後，若需要確認 container 狀態、重新啟動服務或檢查部署設定，可透過 Portainer 查看 Docker Compose stack 中各 container 的執行狀態與紀錄。若需要檢視資料庫內容，則可使用 Adminer 連接 MySQL，查看資料表、欄位設定、foreign key、index、trigger 與資料內容，作為開發、測試與除錯時的資料庫管理工具。

此外，MySQL 的資料透過 volume 掛載至 home server 的指定目錄，使資料不會因 container 重啟或更新而遺失。本組也於同一個 stack 中設定資料庫自動備份服務，依照設定時間定期備份 MySQL 資料庫，並保留指定數量的備份檔案，以降低資料遺失風險。
圖 2.3-1: Adminer 管理平台
![image](https://hackmd.io/_uploads/HkYQdVWfze.png)
圖 2.3-2: 資料查閱
![image](https://hackmd.io/_uploads/ryf0KPbzGe.png)
圖 2.3-3: 資料編輯
![image](https://hackmd.io/_uploads/S12GoDWGzl.png)
圖 2.3-4: 自架服務 Portainer 管理畫面
![image](https://hackmd.io/_uploads/HJQFedbGMe.png)


<!-- 希望有人能做好圖文說明 -->

## 三、系統功能評估
### 3.1 完成度
已完成功能
- 認證系統（註冊/登入/登出/Session 管理）
- 存檔管理（建立/查詢/刪除/結束）
- 時間推進與四階段交易循環
- 撮合引擎（盤前限價/盤中限價市價/盤後定價）
- 下單系統（限價/市價/升降單位驗證/漲跌停）
- 資金帳戶（存款戶/交割戶/轉帳/帳務紀錄）
- 持股管理（持股清單/未實現損益/歷史成交）
- 股票查詢（搜尋/基本資料/K 線/技術指標）	
- 時空隔離（未來資料不揭露）
- 前端 UI（Vue 3、響應式設計）

已完成安全性策略
- 密碼儲存。使用 bcrypt 雜湊，不儲存明文
- Session 管理。2 小時過期、IP /24 網段綁定、登入覆蓋舊 token
- SQL 注入防護。FastAPI 後端使用參數化查詢（params list）
- 所有權驗證。集中於 save_access.py 的 fetch_save_owned()，跨存檔存取一律 403
- 登入速率限制。同帳號 60 秒內失敗 ≥5 次後 429 Too Many Requests
### 3.2 可擴展改進部份
使用體驗改進
- 進入存檔紀錄介面後無法退回登入介面。因為目前存檔記錄介面是登入介面的子介面（懸浮框）。可以設計取消鍵，取消存檔紀錄懸浮框。
- 階段跳轉的改進。目前階段跳轉須進到自選股介面才能查看，若想一邊進行階段一邊查看資產中股票的損益，則需要一直轉跳介面。之後設計可以設計在 TopBar 中。
- 新聞描述：目前介面僅顯示股價與基本資料，缺乏新聞或公告等輔助資訊。可加入新聞描述區塊(如上方可放跑馬燈)，依股票代號串接相關新聞標題與摘要，協助使用者在交易決策時參考更多面向的資訊。
- 存檔按鈕標示不清晰：目前存檔相關按鈕（如建立存檔、切換存檔）缺乏明確的圖示與文字說明，使用者容易不清楚按鈕實際作用為何。可加入提示文字（tooltip）或更直覺的圖示設計，降低操作疑慮。
- 整體操作邏輯不夠直覺：系統雖已提供新手教學，但操作邏輯（如計算公式、按鈕用途、流程順序等）對使用者而言仍不易理解與記憶，教學結束後缺乏可隨時查閱的說明資源，使用者容易在實際操作中感到困惑。可設計教學按鈕或說明字典，讓使用者隨時查詢操作邏輯與相關公式，降低學習門檻。


技術架構改進
- 前端快取：目前 companyProfileCache 僅快取公司簡介靜態資料。可擴展至快取當日 K 線資料，減少重複 API 呼叫
- 測試覆蓋率：目前的單元測試（撮合邏輯、預算邏輯）+ Smoke Test + Schemathesis。可以增加 E2E 測試（Playwright）覆蓋完整玩家流程
- CI/CD：無自動化流水線。可建立 GitHub Actions：PR 自動跑單元測試 + oxlint + prettier check
- 註冊驗證：目前註冊流程僅檢查帳號是否重複，未驗證 Email 真實性、密碼強度，也無防機器人機制（如 CAPTCHA）。可加入 Email 驗證信流程、密碼強度規則檢查，並導入驗證碼機制，提升帳號安全性與防止濫用註冊。
<!-- 我們還少了哪些功能，有沒有可優化的 -->
<!-- 例如除權息、減資的處理可以加上，還有 T+2 制度可以加上 -->
<!-- 我想到的是回朔與分支存檔功能 -->
## 四、實際工作分配及工作份量比重
<!-- 因為大家都有做一點前端，所以分成三大塊寫？ -->
<!-- 這裡怎麼用表格呈現由大家討論 -->
<!-- 比重要怎麼算阿... -->
<!-- 可能可以 8 6 6 之類的？8 就是你做的最認真那個 --> 
### 前端


| 姓名 | 工作內容 | 份量比重 |
| -------- | -------- | -------- |
| 楊凱臣     | 實現     |      |
|周聖詠|重新登入介面（SessionExpiredModal）![image](https://hackmd.io/_uploads/ByQbkEMfzg.png)<br>刪除存檔確認介面![image](https://hackmd.io/_uploads/SJ6-mIzfzx.png)<br>存檔日期選擇器（新增日曆選擇）![image](https://hackmd.io/_uploads/HkwXVHMfze.png)<br>在 TopBar 加入目前存檔的名稱顯示![image](https://hackmd.io/_uploads/HkFn1Iffzx.png)|10%



### 後端

| 姓名 | 工作內容 | 份量比重 |
| -------- | -------- | -------- |
| 盧人豪    | 後端實作與測試 |      |
| 周聖詠    | 後端實作（FastAPI 框架撰寫、各 API 撰寫）、單元測試、資安測試（[foundry](https://blogs.cisco.com/ai/announcing-foundry-security-spec)、[OWASP CVE Lite CLI](https://cybersecuritynews.com/owasp-cve-lite-cli-tool/amp/)） | 60%     |
 
### 資料庫管理

| 姓名 | 工作內容 | 份量比重 |
| -------- | -------- | -------- |
| 盧人豪    | 伺服器提供，維護與建置伺服器和資料庫、API等 |      |

## 個人心得

楊凱臣
這是我第一次實作出

---

許育綸

這次的資料庫理論專題，我主要負責的是前端的設計與實現。

---

周聖詠
這次專案最值得回味的體驗是團隊合作的品質。雖然之前也有後端開發的經驗，但因為大家對協作流程不熟悉，往往淪為各自為政、單打獨鬥。這次不一樣——我們建立了一套真正有效的開發流程：前後端各自維護獨立的 branch、前端透過 issue 向後端提出功能需求或資料格式的調整、並統一 [commit message 規範](https://ithelp.ithome.com.tw/articles/10228738)，讓任何人都能快速看懂這次改動的意圖。

這些看似瑣碎的流程，實際上大幅降低了溝通成本，也讓每個人能更專注在自己的工作上，而不是花時間猜測別人做了什麼。

除此之外，這次專案也讓我接觸到許多新的技術工具。後端框架方面，以前習慣使用較輕量的 Flask，這次改用 FastAPI，體驗到自動產生 /docs 的 Swagger UI，不需要額外寫文件；async 支援也更原生，適合 I/O 密集的 API（像是這個專案頻繁查資料庫）。外網穿透方面，以前只知道 ngrok，這次透過 Tailscale 才發現原來 VPN mesh network 也能達到類似的效果——而且更穩定、不需要每次重啟都更換網址。



---

盧人豪

在這次資料庫專題中，我主要負責較偏系統整合與後端支援的部分。
除了參與後端功能開發與測試外，也需要處理伺服器環境、資料庫服務、容器化部署與遠端連線等問題。這些工作在成果展示時不一定會直接出現在畫面上，但卻會影響整個系統是否能穩定執行。透過這次專題，我更深刻體會到，一個資料庫系統不只是資料表設計或 SQL 查詢而已，還包含服務如何啟動、資料如何保存、不同模組如何連接，以及系統出問題時要如何追蹤與維護。
在開發過程中，我也花了不少時間自學與整理實際部署所需的技術，並將其運用到專題環境中。從後端邏輯、資料庫連線、API 測試，到少量前端響應式調整，每一部分都讓我更清楚完整系統的運作方式。這次經驗讓我意識到，專案中有些貢獻並不一定是最容易被使用者直接看見的功能，但對系統能否真正運作、能否讓團隊共同測試與後續維護，仍然非常重要。也因此，我在這次專題中學到的並不只是資料庫課程內容，而是如何把課堂上的概念放進一個可以實際運行的系統中。