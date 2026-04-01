# OpenHarness 2026.04.01 Update List

> This release introduces production-grade enhancements inspired by architectural patterns observed in leading commercial AI coding agents during the Claude Code source leak incident of March 2026.

## Core Architecture Updates

### 1. Three-Layer Self-Healing Memory

The original flat `heartbeat.md` + `progress.md` design suffered from linear growth that eventually overwhelmed the LLM context window, causing hallucinations and state corruption. Memory is now split into three distinct layers with strict access discipline.

Layer 1 (`heartbeat.md`) serves as a compact pointer index that is always loaded into context, kept strictly under 2KB. Layer 2 (`knowledge/*.md`) consists of topic-specific knowledge files loaded on demand only when the current task step requires them. Layer 3 (`logs/execution_stream.log`) is an append-only structured execution log that is never read in full — it is accessed exclusively via grep.

A new unified memory manager (`harness_memory.py`) handles all three layers, enforcing the write discipline rule that Layer 1 pointers are only updated after external validation confirms success.

| Change | File | Description |
|--------|------|-------------|
| Added | `scripts/harness_memory.py` | Unified three-layer memory manager |
| Redesigned | `templates/heartbeat.md` | Converted to Layer 1 pointer index format |
| Added | `templates/knowledge/README.md` | Layer 2 topic knowledge directory guide |

### 2. Circuit Breaker and Stuck Detection

Previously, a failing task could enter an infinite retry loop, silently burning API credits. The leaked source of a leading AI coding agent revealed that such runaway loops once caused 250,000 wasted API calls per day in production. This update addresses the problem mechanically.

`harness_boot.py` now includes a circuit breaker that automatically blocks all execution after N consecutive failures (default: 3). It also detects "stuck" sessions where the status remains `running` from a crashed previous run, auto-recovering them to `idle` with a failure counter increment. Successful execution automatically resets the breaker.

| Change | File | Description |
|--------|------|-------------|
| Refactored | `scripts/harness_boot.py` | Added circuit breaker logic and stuck detection |

### 3. KAIROS Dream Mode

The previous `memory_evolution.py` relied on simple regex heuristics to extract patterns from execution logs. This update introduces a proper offline memory consolidation engine inspired by the KAIROS autonomous agent mode found in the leaked source.

The new `harness_dream.py` is designed to run during idle periods (typically via a daily off-hours cron job). It performs four phases: analyzing the execution stream for recurring patterns, consolidating fragmented knowledge topic files by deduplicating and merging entries, pruning stale Layer 1 pointers that reference deleted or empty topic files, and injecting distilled best practices (frequent error warnings, proven recovery strategies) back into `playbook.md`.

| Change | File | Description |
|--------|------|-------------|
| Added | `scripts/harness_dream.py` | KAIROS dream mode: offline memory consolidation engine |

### 4. Multi-Agent Coordinator

The original framework was limited to single-agent sequential execution. This update introduces a file-system-based IPC protocol for parallel subtask execution, inspired by the multi-agent orchestration architecture observed in the leaked source.

A Coordinator process dispatches tasks by writing XML-formatted Markdown files to worker `inbox/` directories. Each worker agent reads its inbox, executes independently, and writes results to its `outbox/` directory. The coordinator then collects, aggregates, and archives results. This design is intentionally simple — file-system IPC is more debuggable and auditable than complex message queues or socket-based protocols.

| Change | File | Description |
|--------|------|-------------|
| Added | `scripts/harness_coordinator.py` | Multi-agent coordinator with file-system IPC |

### 5. Cache-Aware Prompting and Entropy Control

`harness_cleanup.py` has been refactored with an AutoCompact safeguard that prevents compression failures from triggering infinite retry loops. It also now handles execution stream log rotation, automatically archiving logs that exceed a configurable size threshold.

The prompt read order in `SKILL.md` has been optimized to maximize LLM prompt cache hits: static files (`mission.md`, `eval_criteria.md`) are read before dynamic state files (`heartbeat.md`), ensuring the stable prefix of the prompt remains cache-friendly across sessions.

| Change | File | Description |
|--------|------|-------------|
| Refactored | `scripts/harness_cleanup.py` | Added AutoCompact safeguard and stream log rotation |

---

## Complete File Change Summary

### Added Files

| File | Description |
|------|-------------|
| `scripts/harness_memory.py` | Three-layer memory manager |
| `scripts/harness_dream.py` | KAIROS dream mode consolidation engine |
| `scripts/harness_coordinator.py` | Multi-agent coordinator (file-system IPC) |
| `templates/knowledge/README.md` | Layer 2 knowledge directory guide |
| `UPDATE_LIST.md` | This file |

### Refactored Files

| File | Description |
|------|-------------|
| `scripts/harness_boot.py` | Circuit breaker and stuck detection |
| `scripts/harness_heartbeat.py` | Three-layer memory integration and execution stream logging |
| `scripts/harness_cleanup.py` | Stream log rotation and AutoCompact safeguard |
| `templates/heartbeat.md` | Redesigned as Layer 1 pointer index |

### Updated Documentation

| File | Description |
|------|-------------|
| `README.md` | Updated framework structure and added changelog section |
| `SKILL.md` | Updated workflows with cache-aware ordering and multi-agent support |
| `references/architecture.md` | Expanded to ten components with three-layer memory details |
| `references/anti-patterns.md` | Added 7 new anti-patterns for memory layers, circuit breaker, and multi-agent |
