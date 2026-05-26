# Quickstart: Foundry

*Phase 1 output of /speckit-plan, 2026-05-25.*

---

## Prerequisites

- Python 3.11+
- Linux (bare metal or VM); `unshare` available for network sandbox
- Tailscale connected (for MySQL at `mysql.shiragaserver.lan`)
- `ANTHROPIC_API_KEY` and `GITHUB_TOKEN` environment variables set

---

## Installation

```bash
# From repo root
pip install -r foundry/requirements.txt

# Install the CLI
pip install -e foundry/

# Verify
foundry --help
```

---

## First Evaluation

### 1. Write a config file

Copy `evaluation-configs/example.toml` and edit:

```bash
cp evaluation-configs/example.toml my-eval.toml
# Edit: target.github_owner, target.github_repo, target.revision, goals.text
```

### 2. Initialize

```bash
foundry init --config my-eval.toml
# → prints evaluation_id (save this)
export EVAL_ID=<evaluation_id>
```

### 3. Start the fleet

```bash
foundry up --evaluation-id $EVAL_ID
# Indexer starts; rest of fleet spawns once index is queryable
```

### 4. Set up health monitoring

```bash
# Add to crontab (runs every minute):
* * * * * /usr/local/bin/foundry health --evaluation-id $EVAL_ID
```

### 5. Monitor

```bash
# Check status
foundry status --evaluation-id $EVAL_ID

# Ask questions
foundry ask --evaluation-id $EVAL_ID "What has been found so far?"

# See unacked operator messages
foundry status --evaluation-id $EVAL_ID  # blockers shown in OPERATOR MESSAGES section
```

### 6. Stop

```bash
# Graceful shutdown
foundry down --evaluation-id $EVAL_ID --grace-secs 120
```

---

## Running Without Network Sandbox

If `unshare` is unavailable (no `CAP_SYS_ADMIN`):

```bash
foundry up --evaluation-id $EVAL_ID --no-sandbox
# WARNING: agents run without network namespace isolation (FR-107 not enforced)
```

Only use this for development; never against a real target.

---

## Running Tests

```bash
# Unit tests (no live DB or LLM required)
pytest tests/unit/

# Integration tests (requires Tailscale + ANTHROPIC_API_KEY)
pytest tests/integration/ -m "not slow"
```

---

## Directory Reference

| Path | Purpose |
|---|---|
| `foundry/cli/` | CLI entrypoint (`foundry` command) |
| `foundry/roles/` | Agent implementations (one per role) |
| `foundry/substrate/` | Queue, finding store, budget, heartbeat |
| `foundry/sandbox/` | OS namespace wrapper |
| `foundry/index/` | Code indexer (tree-sitter) |
| `foundry/rules/corpus/` | Detection rule YAML files |
| `foundry/integrations/` | GitHub + Anthropic clients |
| `specs/001-foundry/` | Spec, plan, data model, contracts |
| `evaluation-configs/` | Example TOML configs (no secrets) |
