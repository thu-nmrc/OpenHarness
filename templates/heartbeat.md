# Heartbeat | Cross-Session State Index (Layer 1)

> **Three-Layer Memory Architecture — Layer 1: Pointer Index (Always in Context)**
>
> This file is the Agent's compact cross-session memory. It MUST stay small (target: < 2KB).
> It contains ONLY status fields and pointers to knowledge files. NO verbose logs here.
> Detailed knowledge lives in `knowledge/*.md` (Layer 2). Raw logs live in `logs/` (Layer 3, grep-only).
>
> **Strict Write Discipline**: Only update this file AFTER `harness_eval.py` confirms success.

## System Status

| Field | Value |
|-------|-------|
| Task Name | `[Read from mission.md by the framework]` |
| Current Status | `idle` |
| Last Execution Time | `[Not executed]` |
| Last Execution Result | `[Not executed]` |
| Total Executions | `0` |
| Consecutive Failures | `0` |
| Next Scheduled Execution | `[Determined by cron]` |

## Execution Pointer

| Field | Value |
|-------|-------|
| Current Step | `Step 0 (Not started)` |
| Completed Steps | `None` |
| Pending Steps | `All` |
| Blocking Reason | `None` |
| Last Successful Artifact | `None` |

## Knowledge Index

<!-- Each row is a pointer to a Layer 2 topic file. Max 150 chars per row. -->
<!-- Format: Topic Tag -> relative path to knowledge file -->
<!-- Agent reads a topic file ONLY when the current task requires that knowledge. -->

| Topic | Path | Last Updated |
|-------|------|--------------|
| _example_ | `knowledge/example_topic.md` | `[Not created]` |

## Active Alerts

<!-- Circuit breaker and anomaly flags. Checked by harness_boot.py on every startup. -->

| Alert | Status | Since |
|-------|--------|-------|
| Circuit Breaker | `off` | `-` |
| Compaction Failures | `0` | `-` |
| Stuck Detection | `clear` | `-` |

---

> **Status Values**: `idle` | `running` | `completed` | `failed` | `blocked` | `mission_complete`
>
> **Memory Layers**:
> - **Layer 1** (this file): Pointer index, always loaded. Keep under 2KB.
> - **Layer 2** (`knowledge/*.md`): Topic files, loaded on demand via tool calls.
> - **Layer 3** (`logs/execution_stream.log`): Append-only raw log. NEVER read fully — grep only.
