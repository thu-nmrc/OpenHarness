# Architecture | Framework Architecture Description

> This document is for Agent to reference when executing the harness framework tasks, to understand the design principles and operating mechanisms of the framework.

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Ten Components Mapping](#ten-components-mapping)
3. [Three-Layer Memory Architecture](#three-layer-memory-architecture)
4. [Operating Process](#operating-process)
5. [File Responsibilities](#file-responsibilities)
6. [State Machine](#state-machine)
7. [Circuit Breaker Pattern](#circuit-breaker-pattern)
8. [KAIROS Dream Mode](#kairos-dream-mode)
9. [Multi-Agent Coordination](#multi-agent-coordination)
10. [Script Usage Quick Reference](#script-usage-quick-reference)

## Design Philosophy

This framework is built on the core concept of Harness Engineering. The core problem that Harness Engineering solves is: how to enable AI to continuously do things right under long-term, complex, rollback-capable, and auditable conditions.

**Core assumption**: Each execution of Agent is a session with a limited duration, but tasks may span multiple sessions. Therefore, a "cross-session memory" mechanism is needed so that each execution can continue from the last breakpoint.

**Design principles**:
- **Context entropy is the enemy**: Memory must be layered — compact pointers always in context, detailed knowledge loaded on demand, raw logs accessible only via grep.
- **Failure cascades must be mechanically prevented**: Circuit breakers, not human judgment, should stop runaway retry loops.
- **Idle time is valuable**: The agent should consolidate its memories during idle periods, not during active task execution.
- **Parallelism through simplicity**: File-system IPC is more debuggable and auditable than complex message queues.

## Ten Components Mapping

| Harness Engineering Component | Framework Implementation |
|-------------------------------|--------------------------|
| Machine-verifiable completion contract | `mission.md` + `eval_criteria.md` |
| Maintainable knowledge as system of record | `playbook.md` + `knowledge/*.md` (Layer 2) |
| Provide Agent with senses and limbs | Tool list defined in `playbook.md` |
| Solve long-term memory loss | Three-Layer Memory: `heartbeat.md` (L1) + `knowledge/` (L2) + `execution_stream.log` (L3) |
| External verification as feedback loop | `eval_criteria.md` + `harness_eval.py` |
| Constraint sandbox and entropy control | `harness_cleanup.py` + stream rotation + knowledge pruning |
| Failure cascade prevention | Circuit Breaker in `harness_boot.py` |
| Offline memory consolidation | KAIROS Dream Mode in `harness_dream.py` |
| Parallel task execution | Multi-Agent Coordinator in `harness_coordinator.py` |
| Prompt cost optimization | Cache-aware read ordering (static before dynamic) |

## Three-Layer Memory Architecture

```
Layer 1: heartbeat.md (Pointer Index)
  - Always loaded into context at session start
  - Target size: < 2KB
  - Contains: System Status, Execution Pointer, Knowledge Index, Active Alerts
  - Write Discipline: Only update AFTER harness_eval.py confirms success

Layer 2: knowledge/*.md (Topic Files)
  - One topic per file, max 500 lines
  - Loaded on demand when the current task requires that knowledge
  - Each file has a pointer row in heartbeat.md's Knowledge Index
  - Created by: harness_memory.py learn
  - Consolidated by: harness_dream.py

Layer 3: logs/execution_stream.log (Raw Execution Log)
  - Append-only structured log
  - NEVER read fully — access via grep only (harness_memory.py search)
  - Auto-rotated by harness_cleanup.py when exceeding size threshold
  - Written by: harness_heartbeat.py (auto) and harness_memory.py stream (manual)
```

## Operating Process

Each time the cron triggers, Agent should execute in the following order:

```
 1. Run harness_boot.py → Check state + Circuit Breaker + Stuck Detection
 2. If blocked/tripped → STOP (do not proceed)
 3. Run harness_heartbeat.py start → Mark start, log to L3
 4. Read mission.md → Understand goals (static, cache-friendly)
 5. Read eval_criteria.md → Understand validation rules (static, cache-friendly)
 6. Read playbook.md → Get execution steps (semi-static)
 7. Read heartbeat.md → Find breakpoint pointer (dynamic)
 8. Load relevant knowledge/*.md topics → On-demand L2 loading
 9. Execute playbook steps from breakpoint
10. Log significant events → harness_memory.py stream
11. On success → harness_heartbeat.py done + harness_memory.py learn
12. On failure → harness_heartbeat.py fail
13. Run harness_eval.py → External verification
14. Run harness_cleanup.py → Entropy control (every 10 runs)
15. If all completed → harness_heartbeat.py mission_complete
```

## File Responsibilities

| File/Directory | Author | Reader | Responsibility |
|----------------|--------|--------|----------------|
| mission.md | User | Agent | Defines "what to do" and "what counts as done" |
| playbook.md | User + Dream | Agent | Defines "how to do" steps + auto-injected insights |
| heartbeat.md | Framework | Agent | Layer 1: Compact pointer index for cross-session recovery |
| knowledge/*.md | Framework | Agent | Layer 2: Topic-specific distilled knowledge |
| logs/execution_stream.log | Framework | grep | Layer 3: Append-only raw execution log |
| logs/dream_journal.md | Dream | Agent/User | Audit trail of KAIROS consolidation cycles |
| progress.md | Framework | Agent/User | Historical execution records (backward compat) |
| eval_criteria.md | User | Agent | Definition of verification criteria |
| cron_config.md | User | Framework | Scheduling parameters |
| agents/*/inbox/ | Coordinator | Worker | Dispatched subtask files |
| agents/*/outbox/ | Worker | Coordinator | Completed result files |

## State Machine

```
idle → running → completed → idle (waiting for next trigger)
                ↘ failed ──→ idle (if consecutive < threshold)
                           ↘ blocked (circuit breaker tripped)
                ↘ blocked (requires manual intervention)
Any state → mission_complete (task ended)

Circuit Breaker:
  off → (consecutive_failures >= N) → tripped → (manual reset) → off
  
Stuck Detection:
  running (from crashed session) → (boot detects) → idle + increment failures
```

## Circuit Breaker Pattern

The circuit breaker prevents runaway API costs from infinite retry loops:

1. `harness_boot.py` checks `Consecutive Failures` on every startup
2. If failures >= threshold (default: 3), it sets `Circuit Breaker` to `tripped`
3. When tripped, ALL execution is blocked until manual reset
4. To reset: set `Circuit Breaker` to `off` and `Consecutive Failures` to `0` in heartbeat.md
5. Successful execution (`harness_heartbeat.py done`) automatically resets the breaker

## KAIROS Dream Mode

The KAIROS Dream Mode (`harness_dream.py`) performs offline memory consolidation:

1. **Phase 1**: Analyze execution stream (L3) for patterns — recurring errors, recovery strategies
2. **Phase 2**: Consolidate fragmented knowledge topic files (L2) — deduplicate, merge entries
3. **Phase 3**: Prune stale Layer 1 pointers — remove references to deleted topic files
4. **Phase 4**: Update playbook with distilled insights — inject recurring error warnings and recovery strategies

Recommended schedule: Run once daily during off-hours via cron.

## Multi-Agent Coordination

The Coordinator (`harness_coordinator.py`) enables parallel subtask execution:

1. **Init**: Create N worker agent directories with inbox/outbox structure
2. **Dispatch**: Write task files to worker inbox in XML-like Markdown format
3. **Execute**: Each worker agent reads its inbox, executes, writes result to outbox
4. **Collect**: Coordinator polls outboxes and aggregates results
5. **Cleanup**: Archive completed tasks and results

Communication protocol: File-system IPC with Markdown-XML message format.

## Script Usage Quick Reference

```bash
# ── Core Lifecycle ──
python3 harness_boot.py /workspace --init              # Initialize workspace
python3 harness_boot.py /workspace                     # Check status + circuit breaker
python3 harness_boot.py /workspace --max-failures 5    # Custom circuit breaker threshold

python3 harness_heartbeat.py /workspace start           # Mark start
python3 harness_heartbeat.py /workspace done --step "Step 2" --summary "Done"
python3 harness_heartbeat.py /workspace fail --step "Step 1" --error "Timeout"
python3 harness_heartbeat.py /workspace blocked --reason "API key needed"
python3 harness_heartbeat.py /workspace mission_complete

python3 harness_eval.py /workspace                      # External validation
python3 harness_cleanup.py /workspace --max-runs 50     # Entropy control
python3 harness_cleanup.py /workspace --max-stream-mb 10  # With stream rotation

# ── Three-Layer Memory ──
python3 harness_memory.py /workspace stream --step "Step 1" --event "Fetched data"
python3 harness_memory.py /workspace learn --topic "api_auth" --insight "Token expires in 3600s"
python3 harness_memory.py /workspace search --query "timeout"
python3 harness_memory.py /workspace topics
python3 harness_memory.py /workspace check

# ── KAIROS Dream Mode ──
python3 harness_dream.py /workspace                     # Full dream cycle
python3 harness_dream.py /workspace --dry-run           # Preview only
python3 harness_dream.py /workspace --skip-playbook     # Skip playbook injection

# ── Multi-Agent Coordinator ──
python3 harness_coordinator.py /workspace init --agents 3
python3 harness_coordinator.py /workspace dispatch --task "Process item X" --step "Step 2"
python3 harness_coordinator.py /workspace status
python3 harness_coordinator.py /workspace collect
python3 harness_coordinator.py /workspace cleanup

# ── Legacy ──
python3 harness_setup_cron.py /workspace                # View cron configuration
python3 harness_linter.py /workspace                    # Architecture linter
python3 memory_evolution.py /workspace                  # Legacy memory evolution
```
