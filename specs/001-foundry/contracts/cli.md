# CLI Contract: `foundry`

*Phase 1 output of /speckit-plan, 2026-05-25.*

The `foundry` CLI is the operator's sole interface (§5.1). Every command is a standalone invocation — no daemon. All state persists in MySQL between invocations.

---

## Global Flags

```
foundry [--config PATH] [--evaluation-id UUID] <command> [args]
```

| Flag | Default | Description |
|---|---|---|
| `--config PATH` | `./foundry.toml` | Path to TOML evaluation config |
| `--evaluation-id UUID` | latest active evaluation | Target a specific evaluation by ID |
| `--verbose` | off | Show SQL queries and API calls |

---

## Commands

### `foundry init`

Validate the config, create a new `fnd_evaluation` row, initialize substrate tables (CREATE TABLE IF NOT EXISTS), return the evaluation ID.

**Input**: TOML config at `--config`
**Output**: `evaluation_id` printed to stdout; validation errors printed to stderr
**Exit codes**: 0 = success; 1 = validation failure (FR-001, FR-129); 2 = DB unreachable

```
$ foundry init --config ./eval.toml
Evaluation initialized: 4a7c9e12-...
```

---

### `foundry up`

Spawn all agent subprocesses for the evaluation. Gates: config valid, `fnd_evaluation.status = 'initializing'` or `'paused'`. Spawns Indexer first; fleet spawn waits for `index_queryable = 1` (FR-003) before spawning remaining roles.

**Input**: `--evaluation-id` (or latest from DB)
**Output**: Table of spawned agents (role, PID, instance index); live updates to stdout until all agents are running
**Side effects**: Inserts rows into `fnd_agent`; updates `fnd_evaluation.status`
**Exit codes**: 0 = fleet running; 1 = error (pre-flight failure, FR-010); 3 = budget cap hit (FR-011)

```
$ foundry up
Starting evaluation 4a7c9e12-...
[✓] Indexer-0 (PID 12345) — indexing...
[✓] Index queryable (48s)
[✓] Cartographer-0 (PID 12401)
[✓] Detector-0, Detector-1, Detector-2 (PIDs 12450–12452)
[✓] Triager-0, Triager-1 (PIDs 12470–12471)
[✓] Validator-0 (PID 12490)
[✓] Coverage-Guide-0 (PID 12500)
[✓] Reporter-0 (PID 12510)
Fleet running. Use `foundry status` to monitor.
```

---

### `foundry status`

Query the current fleet state from MySQL and render a dashboard (FR-008, FR-120).

**Input**: `--evaluation-id`
**Output**: Rich terminal table showing per-agent status, finding counts, coverage, budget, trailing yield; unacknowledged operator messages (blockers highlighted)
**Exit codes**: 0 = success; 2 = DB unreachable

```
$ foundry status
Evaluation: 4a7c9e12-...  Status: running  Runtime: 2h 14m

AGENTS
  Role            Inst  Alive  Claim               Heartbeat
  indexer         0     ✓      (idle)              12s ago
  detector        0     ✓      sweep:auth.py       8s ago
  detector        1     ✓      explore:session     31s ago
  triager         0     ✓      finding:f3a2        5s ago
  ...

FINDINGS
  true-positive: 3  false-positive: 12  needs-review: 2  candidate: 7

COVERAGE   4/11 goals attempted

BUDGET     $12.43 / $50.00 spent  |  Yield: 4.2 pts/$ (threshold: 2.0)

OPERATOR MESSAGES
  [BLOCKER] Detector-1: Testbed unreachable at staging-api.internal (2h ago)
```

---

### `foundry health`

Check heartbeats of all agents; release stale claims (FR-096); respawn dead agents (FR-004); auto-block exhausted work items (FR-097). Intended to be run periodically (cron every 60s).

**Input**: `--evaluation-id`; `--heartbeat-stale-secs` (default: 90)
**Output**: Actions taken (released claims, respawned agents, blocked items); exit silently if nothing to do
**Exit codes**: 0 = success

```
$ foundry health
Agent triager-0 (PID 12471): heartbeat stale (120s). Releasing claim fnd_abc123. Respawning.
Agent triager-0 respawned as PID 12601.
Work item wq_def456: 3 failed claims. Auto-blocking.
```

*Cron example*:
```cron
* * * * * /usr/local/bin/foundry health --evaluation-id 4a7c9e12-...
```

---

### `foundry ask <question>`

Answer a free-form operator question grounded in evaluation state (FR-013). Uses the strong LLM tier with full read access to finding store, coverage state, and session logs.

**Input**: Question string; `--evaluation-id`
**Output**: Answer printed to stdout, with citations to the store records consulted
**Exit codes**: 0 = success; 2 = DB unreachable

```
$ foundry ask "Why was finding f3a2 closed as false-positive?"
Finding f3a2 (SQL injection candidate in auth.py:validate_token) was assigned
false-positive by Triager-0 at 14:32 UTC. Reasoning: the query parameter is
cast to int() before interpolation on line 47, which eliminates the injection
path. Source: fnd_finding.investigation_report, session log agent:triager-0 turn 4.
```

---

### `foundry steer <agent-id> <message>`

Deliver an operator message to a specific agent at its next idle point (non-disruptive, FR-016).

```
$ foundry steer detector-1 "Focus on the payment module, deprioritize auth."
Steer queued for detector-1 (non-disruptive delivery).
```

---

### `foundry steer --interrupt <agent-id> <message>`

Deliver an operator message immediately, interrupting the agent's current turn (disruptive, FR-016).

```
$ foundry steer --interrupt triager-0 "Re-triage finding f5c9 — testbed confirms exploitable."
Interrupt delivered to triager-0.
```

---

### `foundry queue add <description>`

Add a task to the work queue at operator priority (FR-014, FR-098).

```
$ foundry queue add "Investigate function process_payment in billing/checkout.py for IDOR"
Task added: wq_gh7891 (priority: 1 — operator-submitted)
```

---

### `foundry queue list`

List open and blocked work items.

---

### `foundry pause`

Signal all agents to wrap up and release claims (FR-006). Sets `fnd_evaluation.status = 'paused'`.

---

### `foundry resume`

Re-spawn the fleet from paused state. Equivalent to `foundry up` on a paused evaluation.

---

### `foundry down`

Graceful drain: steer all agents to wrap up (FR-006), wait grace period, then terminate. Sets `fnd_evaluation.status = 'done'`.

```
$ foundry down --grace-secs 120
Sent wrap-up steer to 8 agents. Waiting up to 120s...
All agents exited cleanly.
```

---

### `foundry ack <message-id>`

Acknowledge an operator message (removes from unacked view and dedup pool, FR-102c).

```
$ foundry ack msg_abc123
Acknowledged. Sending reply to detector-1: "Testbed should be up now."
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `GITHUB_TOKEN` | Yes | GitHub PAT with `repo` scope |
| `SQL_API_URL` | No | Override SQL API endpoint (default: `http://sql-api.shiragaserver.lan/query`) |
| `FOUNDRY_TESTBED_PASS` | Eval-specific | Testbed credentials (referenced from config, not stored in it) |

---

## Error Model

All commands write structured JSON to stderr on error:
```json
{"error": "validation_failure", "fields": ["budget.spend_cap_usd"], "message": "spend_cap_usd must be > 0"}
```

Human-readable error text is also written to stderr. Exit codes:
- 0: success
- 1: input / validation error
- 2: infrastructure error (DB unreachable, API auth failure)
- 3: evaluation constraint error (budget cap, run already active)
