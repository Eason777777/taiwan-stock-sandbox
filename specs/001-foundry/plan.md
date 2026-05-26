# Implementation Plan: Foundry

**Branch**: `main` | **Date**: 2026-05-25 | **Spec**: [spec.md](spec.md)

**Input**: `specs/001-foundry/spec.md` — AI-Assisted Security Evaluation Framework

---

## Summary

Foundry is a fleet of role-specialized LLM agents (Orchestrator, Indexer, Cartographer, Detector, Triager, Validator, Coverage-Guide, Reporter) that runs security evaluations against a target codebase. The operator interacts entirely through a per-command CLI (`foundry`); all fleet state persists in MySQL. Agents run as OS-level sandboxed subprocesses on bare metal/VMs. The LLM backend is Anthropic's API with two model tiers. Detection combines tree-sitter-based structural indexing with LLM rule-sweep and exploratory hunting; findings flow through evidence-gated triage before any human-visible output is produced.

---

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- `anthropic` — Anthropic Python SDK (Claude API, two-tier models, prompt caching)
- `httpx` — async HTTP client (SQL API calls, reuses existing `app/database.py` pattern)
- `typer` — CLI framework (`foundry up`, `down`, `status`, `health`, `ask`, ...)
- `tree-sitter` + `tree-sitter-python` — deterministic code parser for Indexer (FR-020)
- `tomllib` (stdlib, 3.11+) — TOML config parsing
- `tomli-w` — TOML config writing
- `python-prctl` or `ctypes` seccomp — OS-level sandbox enforcement (FR-107)
- `rich` — terminal output for dashboard (FR-120) and status (FR-008)
- `passlib[bcrypt]` — already in requirements; not used here

**Storage**: MySQL at `mysql.shiragaserver.lan`, accessed via HTTP SQL API (`POST http://sql-api.shiragaserver.lan/query`). All substrate state (work queue, finding store, coverage checklist, heartbeats, budget, session logs) stored in dedicated Foundry tables. Atomic claim via `SELECT ... FOR UPDATE` inside MySQL transactions.

**Testing**: `pytest` + `pytest-asyncio`; structural behavior tests run without a live LLM model (NFR-004); integration tests require Tailscale connectivity.

**Target Platform**: Linux (bare metal or VM), Tailscale network for DB access.

**Project Type**: CLI tool (operator-facing) + multi-process agent framework (background subprocesses).

**Performance Goals**: Throughput-oriented, not latency-oriented (A-7). Indexer must not block Orchestrator responsiveness (FR-029). Heartbeat emission must not share execution lane with agent work (FR-101).

**Constraints**:
- Single-tenant (one evaluation at a time)
- OS-level network namespace + seccomp for sandbox (no Docker/container runtime)
- Agent heartbeat on a dedicated thread, not the main event loop
- All persisted writes atomic (Constitution XI, FR-106a)

**Scale/Scope**: Single operator; targets up to ~500k LOC; fleet of 2–10 concurrent agents per evaluation.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-evaluated after Phase 1 design.*

| Principle | Enforcing FRs | Design status | Notes |
|---|---|---|---|
| **I. Evidence Over Assertion** | FR-052, FR-087, FR-088 | PASS | Evidence gate with mechanical citation resolution is a first-class implementation concern |
| **II. Surface Only What Survives** | FR-044, FR-057, FR-079 | PASS | Detector writes to finding store only; Reporter writes to issue tracker only on `true-positive` |
| **III. Liveness By Heartbeat, Never By Clock** | FR-005, FR-100, FR-101 | PASS | `foundry health` releases stale heartbeats; heartbeat thread separated from agent work thread per FR-101 |
| **IV. Claims Are Atomic And Mortal** | FR-095, FR-096 | PASS | `SELECT ... FOR UPDATE` in MySQL transaction; `foundry health` releases claims of dead agents |
| **V. The Provider Is The Rate Arbiter** | FR-105, FR-106 | PASS | Fleet-wide shared backoff state written to MySQL; no internal rate cap |
| **VI. Coverage Before Yield** | FR-071, FR-116 | PASS | Auto-stop gated on `coverage_complete = TRUE` flag in DB |
| **VII. Exploited Means Demonstrated** | FR-061, FR-089 | PASS | `exploited` set only by Validator's clean-room subprocess, never by Triager or Reporter |
| **VIII. Fingerprints Are Stable Under Edit** | FR-090, FR-091 | PASS | Fingerprint = SHA-256(normalize(path) + symbol + vuln_class); no line numbers |
| **IX. Sandbox By Infrastructure, Not By Prompt** | FR-107, FR-108 | PASS | Linux network namespace + iptables allowlist; target source mounted read-only via bind mount |
| **X. The Operator Outranks Every Agent** | FR-047, FR-068, FR-102 | PASS | Per-command CLI naturally enforces operator primacy; peer messages are advisory only |
| **XI. Persist Atomically** | FR-106a, FR-025 | PASS | MySQL transactions used for all multi-step writes; no delete-then-write patterns |

No violations. Proceeding to Phase 0.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-foundry/
├── plan.md              # This file
├── research.md          # Phase 0: resolved decisions
├── data-model.md        # Phase 1: MySQL schema
├── quickstart.md        # Phase 1: setup & run guide
├── contracts/
│   └── cli.md           # Phase 1: CLI command contracts
└── tasks.md             # Phase 2 output (not created here — /speckit-tasks)
```

### Source Code (repository root)

```text
foundry/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py          # typer app entrypoint: foundry up/down/status/health/ask/init
│   └── output.py        # rich-based terminal rendering
├── roles/
│   ├── __init__.py
│   ├── base.py          # BaseAgent: heartbeat thread, tool-use loop, session rotation (FR-118)
│   ├── orchestrator.py  # foundry up/down/health CLI actions
│   ├── indexer.py       # tree-sitter indexing + FR-024 queryable gate
│   ├── cartographer.py  # security map authoring (FR-030–FR-036)
│   ├── detector.py      # rule-sweep + exploratory (FR-037–FR-049)
│   ├── triager.py       # evidence-gated verdict (FR-050–FR-059)
│   ├── validator.py     # clean-room reproduction (FR-060–FR-066)
│   ├── coverage_guide.py# checklist + directed tasks (FR-067–FR-074)
│   └── reporter.py      # issue publication + rollup (FR-075–FR-084)
├── substrate/
│   ├── __init__.py
│   ├── queue.py         # work queue (FR-094–FR-099): claim, release, block
│   ├── store.py         # finding store (FR-085–FR-093): verdicts, fingerprints, evidence
│   ├── budget.py        # budget governor (FR-112–FR-117): spend, yield, auto-stop
│   ├── heartbeat.py     # liveness registry (FR-100, FR-096)
│   └── notes.py         # shared notes (FR-104–FR-104b): size-bounded, lock-protected
├── sandbox/
│   ├── __init__.py
│   └── namespace.py     # Linux network namespace + seccomp wrapper (FR-107–FR-108)
├── index/
│   ├── __init__.py
│   ├── parser.py        # tree-sitter multi-language parser (FR-020, FR-021)
│   ├── query.py         # get-function-body, get-callers, get-callees, find-symbol (FR-022)
│   └── embed.py         # embeddings stub (FR-023 SHOULD; deferred post-MVP)
├── rules/
│   ├── __init__.py
│   ├── loader.py        # YAML rule corpus loader (FR-041)
│   └── corpus/          # built-in detection rules (YAML, one file per class)
├── integrations/
│   ├── __init__.py
│   ├── github.py        # GitHub Issues + VCS permalink (FR-078, FR-084)
│   └── llm.py           # Anthropic two-tier client + fleet-wide backoff (FR-105, FR-106)
├── db.py                # SqlApiClient: reuses app/database.py pattern for Foundry tables
└── config.py            # TOML config loader/validator (FR-001, FR-126–FR-129)

tests/
├── unit/
│   ├── test_fingerprint.py
│   ├── test_evidence_gate.py
│   ├── test_queue_claim.py
│   └── test_budget.py
└── integration/
    ├── test_indexer.py
    └── test_end_to_end.py  # SC-001 seeded-vuln test

evaluation-configs/       # example operator configs (TOML, no secrets)
└── example.toml
```

**Structure Decision**: Single-project layout under `foundry/` at repo root, alongside existing `app/` (taiwan-stock-sandbox). Shared MySQL infrastructure via `foundry/db.py` which mirrors `app/database.py`.

---

## Complexity Tracking

No constitution violations; no complexity justification required.
