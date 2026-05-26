# Security Manual — Foundry 安全審查工具包

> 本手冊說明如何利用 Foundry 的偵測規則與分析工具，透過 AI Agent (下方以 claude code 為例) 對程式碼進行安全審查。
> 不需要 API key，只需要 Claude Code、Codex 或任意 AI Agent。

---

## 概覽

Foundry 包含兩個層次：

| 層次 | 檔案 | 需要 API key？ |
|---|---|---|
| **偵測規則** | `foundry/rules/corpus/*.yaml` | 否 — 這是你的掃描 checklist |
| **程式碼解析器** | `foundry/index/parser.py` | 否 — 純 Python，tree-sitter |
| **單元測試** | `tests/unit/` | 否 — 可直接跑 |
| **完整自動化代理人** | `foundry/roles/`, `foundry/cli/` | 是 — 需要 Anthropic API |

**本手冊的使用方式**：你把程式碼交給 Claude Code，Claude Code 對照偵測規則進行分析，找出安全漏洞。

---

## 快速開始

### 1. 安裝（選用，用於程式碼解析）

```bash
# 僅需要用到 parser 時才需要安裝
conda activate sqlproject
pip install tree-sitter tree-sitter-python pyyaml pytest
```

### 2. 跑單元測試確認環境正常

```bash
pytest tests/unit/ -v
# 預期：34 passed
```

### 3. 請 Claude Code 進行安全審查

打開 Claude Code（`claude` 指令或 IDE 插件），輸入：

```
請對照 foundry/rules/corpus/ 裡的偵測規則，
掃描 app/routers/ 目錄下所有 Python 檔案的安全問題。
```

或更具體地：

```
請幫我找 app/routers/orders.py 裡的 SQL injection，
參考 foundry/rules/corpus/sql-injection.yaml 的判斷條件。
```

---

## 偵測規則說明

所有規則位於 `foundry/rules/corpus/`，格式為 YAML。每個規則描述一類漏洞的判斷條件。

### 規則一覽

| 檔案 | 規則 ID | 漏洞類型 | 嚴重性 |
|---|---|---|---|
| `sql-injection.yaml` | SQL-001 | SQL Injection | High |
| `command-injection.yaml` | CMD-001 | Command Injection | Critical |
| `path-traversal.yaml` | PATH-001 | Path Traversal | High |
| `idor.yaml` | IDOR-001 | Insecure Direct Object Reference | High |
| `hardcoded-credentials.yaml` | CRED-001 | Hardcoded Credentials | Critical |
| `insecure-deserialization.yaml` | DESER-001 | Insecure Deserialization | Critical |
| `ssrf.yaml` | SSRF-001 | Server-Side Request Forgery | High |
| `template-injection.yaml` | TMPL-001 | Template Injection / XSS | High |
| `missing-auth-check.yaml` | AUTH-001 | Missing Authentication Check | Critical |
| `xxe.yaml` | XXE-001 | XML External Entity | High |
| `open-redirect.yaml` | REDIR-001 | Open Redirect | Medium |
| `mass-assignment.yaml` | MASS-001 | Mass Assignment | High |
| `insecure-random.yaml` | RAND-001 | Insecure Randomness | Medium |
| `timing-side-channel.yaml` | TIMING-001 | Timing Side Channel | Medium |
| `sensitive-data-in-log.yaml` | LOG-001 | Sensitive Data in Log | Medium |

### 規則結構

每個 YAML 規則包含以下欄位：

```yaml
id: SQL-001                    # 唯一識別碼
name: SQL Injection             # 漏洞名稱
vulnerability_class: SQL Injection
cwe: CWE-89                    # CWE 分類
severity_hint: high            # 嚴重性（critical/high/medium/low）
applicable_languages: [python] # 適用語言
scope: function                # 分析粒度（function 層級）
prompt_template: |             # 判斷條件說明
  ...
```

`prompt_template` 是最重要的欄位，它精確描述了「什麼情況才算是真正的漏洞」。可以直接閱讀它來理解判斷標準。

---

## 如何請 Claude Code 進行審查

### 全面掃描

```
請閱讀 foundry/rules/corpus/ 下的所有規則，
然後對 app/ 目錄進行全面的安全審查。
對每個發現的問題，請說明：
1. 位置（檔案名稱和函式名稱）
2. 漏洞類型（對應哪個規則）
3. 為什麼這是真正的問題（不是誤報）
4. 攻擊者如何利用它
5. 修復建議
```

### 針對特定漏洞類型

```
請參考 foundry/rules/corpus/sql-injection.yaml 的判斷條件，
掃描 app/routers/ 下所有和資料庫互動的函式。
只回報確定有問題的，不要回報「可能有問題」的。
```

### 針對特定檔案

```
請審查 app/routers/auth.py，重點檢查：
- 認證繞過（missing-auth-check.yaml）
- 硬編碼密碼（hardcoded-credentials.yaml）
- Timing side channel（timing-side-channel.yaml）
```

### 深度調查單一函式

```
請仔細分析 app/routers/orders.py 中的 create_order 函式。
追蹤 user_id 參數從 HTTP 請求進來到資料庫查詢的完整路徑，
確認是否有 IDOR 漏洞（參考 foundry/rules/corpus/idor.yaml）。
```

---

## 三段式證據標準

Foundry 要求每個真正的漏洞必須有三段論證，Claude Code 的回報也應遵循這個標準：

```
漏洞：SQL Injection in get_order()

1. Reachability（可達性）
   攻擊者如何控制輸入：
   POST /orders → order_id 參數 → 直接傳入 get_order(order_id)
   → 未經驗證，攻擊者可控

2. Trust Boundary（信任邊界）
   不受信任的資料在哪裡進入受信任的處理：
   app/routers/orders.py:get_order() 第 23 行
   → 直接把 HTTP 參數拼接進 SQL 字串，沒有 parameterization

3. Impact（影響）
   具體的安全後果：
   攻擊者可讀取任意 order 資料（UNION SELECT）
   或執行任意 SQL（DROP TABLE、資料外洩）
```

如果三段論證有任何一段缺失，就不能確定是真正的漏洞。

---

## 程式碼解析器（進階）

`foundry/index/parser.py` 提供函式層級的程式碼索引，可以獨立使用：

```python
from foundry.index.parser import index_file, file_hash

# 解析一個 Python 檔案，取得所有函式的位置和內容
records = index_file("app/routers/auth.py")
for rec in records:
    print(f"{rec.symbol_name}: 第 {rec.start_line}–{rec.end_line} 行")
    print(rec.body[:200])
    print()
```

**依賴：** `pip install tree-sitter tree-sitter-python`

---

## 新增自訂規則

如果你的專案有特定的安全模式，可以新增規則：

```yaml
# foundry/rules/corpus/my-rule.yaml
id: MY-001
name: My Custom Vulnerability
vulnerability_class: My Vuln
cwe: CWE-XX
severity_hint: high
applicable_languages: [python]
scope: function
prompt_template: |
  分析以下函式是否有 [漏洞描述]。
  需要同時滿足：
  1. [條件 A]
  2. [條件 B]
  3. [沒有 [防護措施]]

  函式：
  {{function_body}}

  只在三個條件都成立時才回報漏洞。
```

新增後，告訴 Claude Code：

```
請用 foundry/rules/corpus/my-rule.yaml 的條件，掃描 app/ 目錄。
```

---

## 目錄結構

```
foundry/
├── rules/
│   ├── corpus/          ← 偵測規則（核心，15 個 YAML）
│   │   ├── sql-injection.yaml
│   │   ├── command-injection.yaml
│   │   └── ... (共 15 個)
│   └── loader.py        ← 規則載入器（Python）
└── index/
    └── parser.py        ← 程式碼解析器（tree-sitter）

specs/001-foundry/
├── spec.md              ← 完整功能規格
├── plan.md              ← 技術架構
├── data-model.md        ← 資料庫 schema
└── research.md          ← 技術決策紀錄

tests/unit/              ← 不需 API 可直接跑的測試
evaluation-configs/
└── example.toml         ← 設定檔範本（未來完整版用）
```

---

## 常見問題

**Q: 和一般的 linter 或 SAST 工具有什麼不同？**

一般工具找的是「有這個 pattern」，Foundry 的規則要求三段論證：資料必須來自攻擊者可控的輸入、必須跨越信任邊界、必須有具體的安全影響。誤報率低很多。

**Q: Claude Code 可以掃多大的 codebase？**

視 context window 大小而定。對於大型 repo，建議分目錄、分函式進行，而不是一次貼所有程式碼。

**Q: 如何確保回報的問題不是誤報？**

要求 Claude Code 提供三段論證（reachability、trust boundary、impact），缺任何一段就要求補充說明或排除。
