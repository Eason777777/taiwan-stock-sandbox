# Data Model: Foundry

*Phase 1 output of /speckit-plan, 2026-05-25.*

All tables are prefixed `fnd_` to coexist with the existing taiwan-stock-sandbox tables on the same MySQL instance.

---

## Entity Overview

| Table | Purpose |
|---|---|
| `fnd_evaluation` | One row per evaluation run (the central state machine) |
| `fnd_agent` | One row per spawned agent process (liveness registry) |
| `fnd_work_item` | Work queue entries (FR-094–FR-099) |
| `fnd_finding` | Finding store — all findings at every lifecycle stage (FR-085–FR-093) |
| `fnd_coverage_item` | Coverage checklist entries (FR-067–FR-074) |
| `fnd_account_tx` | Budget ledger — one row per LLM call (FR-112–FR-113) |
| `fnd_operator_message` | Async agent→operator messages (FR-102a–FR-102d) |
| `fnd_session_log` | Structured per-agent session turns (FR-122) |
| `fnd_rate_limit` | Fleet-wide LLM backoff state (FR-106) |
| `fnd_shared_notes` | Size-bounded cross-agent notes (FR-104–FR-104b) |

---

## Schema

### `fnd_evaluation`

```sql
CREATE TABLE fnd_evaluation (
  evaluation_id     CHAR(36)       NOT NULL PRIMARY KEY,  -- UUID
  config_toml       MEDIUMTEXT     NOT NULL,               -- full TOML config snapshot
  target_revision   VARCHAR(64)    NOT NULL,               -- pinned git SHA
  status            ENUM('initializing','indexing','running','paused','done','error')
                                   NOT NULL DEFAULT 'initializing',
  index_queryable   TINYINT(1)     NOT NULL DEFAULT 0,     -- FR-024 gate
  coverage_complete TINYINT(1)     NOT NULL DEFAULT 0,     -- FR-071
  created_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at        DATETIME       NULL,
  finished_at       DATETIME       NULL,
  stop_reason       VARCHAR(255)   NULL                    -- 'budget_cap'|'time_cap'|'yield_threshold'|'operator'
);
```

### `fnd_agent`

```sql
CREATE TABLE fnd_agent (
  agent_id          CHAR(36)       NOT NULL PRIMARY KEY,  -- UUID
  evaluation_id     CHAR(36)       NOT NULL,
  role              ENUM('orchestrator','indexer','cartographer','detector',
                         'triager','validator','coverage_guide','reporter')
                                   NOT NULL,
  instance_index    SMALLINT       NOT NULL,
  pid               INT            NULL,                   -- OS PID of subprocess
  status            ENUM('spawning','alive','dead','retired') NOT NULL DEFAULT 'spawning',
  current_claim_id  CHAR(36)       NULL,                   -- FK → fnd_work_item.item_id
  last_heartbeat    DATETIME       NULL,
  restart_count     SMALLINT       NOT NULL DEFAULT 0,
  spawned_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (evaluation_id) REFERENCES fnd_evaluation(evaluation_id)
);
```

### `fnd_work_item`

```sql
CREATE TABLE fnd_work_item (
  item_id           CHAR(36)       NOT NULL PRIMARY KEY,  -- UUID, stable (FR-099)
  evaluation_id     CHAR(36)       NOT NULL,
  queue_name        VARCHAR(64)    NOT NULL DEFAULT 'main', -- named queues (FR-094)
  title             VARCHAR(512)   NOT NULL,
  description       MEDIUMTEXT     NULL,
  priority          INT            NOT NULL DEFAULT 100,   -- lower = higher priority
  status            ENUM('open','claimed','blocked','closed') NOT NULL DEFAULT 'open',
  claimed_by        CHAR(36)       NULL,                   -- FK → fnd_agent.agent_id
  claimed_at        DATETIME       NULL,
  claim_count       SMALLINT       NOT NULL DEFAULT 0,     -- for FR-097 auto-block
  created_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (evaluation_id) REFERENCES fnd_evaluation(evaluation_id)
);
-- Claim query uses: SELECT ... FOR UPDATE SKIP LOCKED WHERE status='open' AND claimed_by IS NULL
```

### `fnd_finding`

```sql
CREATE TABLE fnd_finding (
  finding_id        CHAR(36)       NOT NULL PRIMARY KEY,
  evaluation_id     CHAR(36)       NOT NULL,
  fingerprint       CHAR(64)       NOT NULL,               -- SHA-256(norm_path+symbol+vuln_class), FR-090
  status            ENUM('candidate','triaged','published') NOT NULL DEFAULT 'candidate',
  verdict           ENUM('true-positive','false-positive','needs-review',
                         'not-applicable','code-quality') NULL,
  exploited         TINYINT(1)     NOT NULL DEFAULT 0,
  location_path     VARCHAR(1024)  NOT NULL,               -- normalized file path
  location_symbol   VARCHAR(512)   NOT NULL,               -- function/symbol name
  vuln_class        VARCHAR(128)   NOT NULL,               -- e.g. 'sql-injection'
  cwe_id            VARCHAR(16)    NULL,                   -- e.g. 'CWE-89'
  severity          ENUM('critical','high','medium','low') NULL,
  detection_technique VARCHAR(128) NOT NULL,               -- rule ID or 'exploratory'
  description       MEDIUMTEXT     NOT NULL,               -- Detector's candidate description
  investigation_report MEDIUMTEXT  NULL,                   -- Triager's full reasoning
  evidence_reachability TEXT       NULL,                   -- cited code location (a)
  evidence_trust_boundary TEXT     NULL,                   -- cited code location (b)
  evidence_impact   TEXT           NULL,                   -- cited code location (c)
  poc_artifact      MEDIUMTEXT     NULL,                   -- PoC script (on exploited)
  validator_notes   MEDIUMTEXT     NULL,                   -- Validator's reproduction notes
  github_issue_number INT          NULL,                   -- set when published
  created_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_fingerprint (evaluation_id, fingerprint),
  FOREIGN KEY (evaluation_id) REFERENCES fnd_evaluation(evaluation_id)
);
```

### `fnd_coverage_item`

```sql
CREATE TABLE fnd_coverage_item (
  item_id           CHAR(36)       NOT NULL PRIMARY KEY,
  evaluation_id     CHAR(36)       NOT NULL,
  component         VARCHAR(512)   NOT NULL,               -- from security map
  goal              VARCHAR(512)   NOT NULL,               -- from operator goals
  credible_bar      TEXT           NOT NULL,               -- what "attempted" means
  status            ENUM('open','attempted','closed') NOT NULL DEFAULT 'open',
  evidence_summary  TEXT           NULL,                   -- what was tried
  closed_at         DATETIME       NULL,
  created_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (evaluation_id) REFERENCES fnd_evaluation(evaluation_id)
);
```

### `fnd_account_tx`

```sql
CREATE TABLE fnd_account_tx (
  tx_id             CHAR(36)       NOT NULL PRIMARY KEY,
  evaluation_id     CHAR(36)       NOT NULL,
  agent_id          CHAR(36)       NOT NULL,
  model             VARCHAR(64)    NOT NULL,
  input_tokens      INT            NOT NULL DEFAULT 0,
  output_tokens     INT            NOT NULL DEFAULT 0,
  cache_read_tokens INT            NOT NULL DEFAULT 0,
  cache_write_tokens INT           NOT NULL DEFAULT 0,
  cost_usd          DECIMAL(12,6)  NOT NULL,               -- computed from token counts
  is_estimated      TINYINT(1)     NOT NULL DEFAULT 0,     -- FR-113
  called_at         DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (evaluation_id) REFERENCES fnd_evaluation(evaluation_id)
);
```

### `fnd_operator_message`

```sql
CREATE TABLE fnd_operator_message (
  message_id        CHAR(36)       NOT NULL PRIMARY KEY,
  evaluation_id     CHAR(36)       NOT NULL,
  originating_agent CHAR(36)       NOT NULL,
  kind              ENUM('blocker','request','feedback','info') NOT NULL,
  content           TEXT           NOT NULL,
  dedup_key         CHAR(64)       NOT NULL,               -- SHA-256(kind+content[:256])
  acknowledged      TINYINT(1)     NOT NULL DEFAULT 0,
  reply             TEXT           NULL,
  created_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_dedup (evaluation_id, dedup_key, acknowledged),  -- FR-102b
  FOREIGN KEY (evaluation_id) REFERENCES fnd_evaluation(evaluation_id)
);
```

### `fnd_session_log`

```sql
CREATE TABLE fnd_session_log (
  log_id            CHAR(36)       NOT NULL PRIMARY KEY,
  evaluation_id     CHAR(36)       NOT NULL,
  agent_id          CHAR(36)       NOT NULL,
  turn_number       INT            NOT NULL,
  role_in_turn      ENUM('user','assistant','tool_result') NOT NULL,
  content_json      MEDIUMTEXT     NOT NULL,               -- full message content as JSON
  tool_name         VARCHAR(128)   NULL,                   -- if tool_use
  input_tokens      INT            NULL,
  output_tokens     INT            NULL,
  logged_at         DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (evaluation_id) REFERENCES fnd_evaluation(evaluation_id)
);
```

### `fnd_rate_limit`

```sql
CREATE TABLE fnd_rate_limit (
  provider          VARCHAR(64)    NOT NULL PRIMARY KEY,   -- e.g. 'anthropic'
  backoff_until     DATETIME       NULL,                   -- NULL = no active backoff
  retry_after_secs  INT            NULL,
  updated_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
INSERT INTO fnd_rate_limit (provider) VALUES ('anthropic')
  ON DUPLICATE KEY UPDATE provider = provider;
```

### `fnd_shared_notes`

```sql
CREATE TABLE fnd_shared_notes (
  evaluation_id     CHAR(36)       NOT NULL PRIMARY KEY,
  content           TEXT           NOT NULL DEFAULT '',    -- size-bounded in application
  byte_limit        INT            NOT NULL DEFAULT 16384, -- 16 KB default
  updated_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (evaluation_id) REFERENCES fnd_evaluation(evaluation_id)
);
```

---

## State Transitions

### Finding lifecycle

```
candidate  → triaged    (Triager assigns verdict)
triaged    → published  (Reporter publishes to GitHub Issues, verdict = true-positive only)
```

Verdict is mutable (re-triage replaces); status progression is one-way.

### Work item lifecycle

```
open → claimed   (agent claims via SELECT FOR UPDATE)
claimed → open   (agent releases; also on heartbeat expiry via `foundry health`)
claimed → closed (agent closes on completion)
open/claimed → blocked  (claim_count ≥ N per FR-097, set by `foundry health`)
blocked → open   (operator or Coverage-Guide re-opens with better description)
```

### Evaluation lifecycle

```
initializing → indexing  (Orchestrator validates config, starts Indexer)
indexing → running       (Indexer sets index_queryable=1, Orchestrator spawns full fleet)
running → paused         (operator runs `foundry pause`)
paused → running         (operator runs `foundry resume`)
running → done           (budget governor signals stop)
* → error                (unrecoverable failure)
```

---

## Key Invariants

- `fnd_finding.fingerprint` is unique per evaluation (no duplicate candidates per FR-045)
- `fnd_finding` evidence citations are verified to resolve before verdict = `true-positive` (FR-088)
- `fnd_finding.exploited = 1` requires `verdict = 'true-positive'` and `poc_artifact IS NOT NULL` (FR-061, FR-089)
- `fnd_work_item.claim_count` increments on every claim; auto-blocks at configured N (FR-097)
- `fnd_operator_message.dedup_key` prevents duplicate messages from parallel agents (FR-102b)
- `fnd_account_tx` has one row per LLM API call; never aggregated in place (immutable ledger)
