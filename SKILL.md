---
name: harness-24h
description: A production-grade framework for long-running, autonomous agents based on Harness Engineering principles. Features three-layer self-healing memory, circuit breaker protection, KAIROS dream-mode consolidation, and multi-agent coordination. When a user describes a task idea, Agent automatically initializes the workspace, fills all template files, sets up the cron schedule, and begins execution immediately.
---

# Harness-24h | 24-hour Harness Framework

This skill provides a complete framework for executing long-running, autonomous tasks based on the principles of Harness Engineering.

**Key principle**: The user only describes their task idea. Agent handles everything else — workspace creation, filling all files, setting up the cron schedule, and starting execution.

## Core Concepts

The framework is built around 10 core components of Harness Engineering:

1. **Machine-verifiable contracts**: `mission.md` and `eval_criteria.md`
2. **Knowledge as system of record**: `playbook.md`
3. **Agent senses and effectors**: Configured via `harness_boot.py`
4. **Solving long-term amnesia**: Three-Layer Memory Architecture (see below)
5. **Externalized validation loop**: `harness_eval.py`
6. **Mechanized constraints and entropy control**: `harness_cleanup.py`
7. **Three-Layer Self-Healing Memory**: Pointer index + topic files + grep-only stream
8. **Circuit Breaker Protection**: Auto-block after N consecutive failures
9. **KAIROS Dream Mode**: Offline memory consolidation during idle periods
10. **Multi-Agent Coordination**: File-system IPC for parallel subtask execution

For detailed architecture, read `references/architecture.md`.
For common anti-patterns to avoid, read `references/anti-patterns.md`.

---

## Three-Layer Memory Architecture

| Layer | File(s) | Purpose | Access Pattern |
|-------|---------|---------|----------------|
| L1 | `heartbeat.md` | Compact pointer index (< 2KB) | Always in context |
| L2 | `knowledge/*.md` | Topic-specific knowledge files | On-demand loading |
| L3 | `logs/execution_stream.log` | Append-only raw execution log | Grep-only, never read fully |

**Strict Write Discipline**: Only update L1 pointers AFTER `harness_eval.py` confirms success.

---

## Workflow A: User Describes a New Task (FULLY AUTOMATIC)

When a user describes a task idea, follow ALL steps below without asking the user to fill in any files manually.

### Step A1: Decide Workspace Path

Choose a workspace path based on the task name. Convention:
```
~/.openclaw/workspace/harness/{task-slug}/
```

### Step A2: Initialize Workspace

```bash
python3 {skill_dir}/scripts/harness_boot.py /path/to/workspace --init
```

This copies all template files and creates `knowledge/`, `logs/`, and `output/` directories.

### Step A3: Fill ALL Template Files Yourself

Based on the user's task description, Agent must write the following files completely. Do NOT leave any placeholder text.

**File 1 — `mission.md`**: Write the task contract with machine-checkable completion criteria.

**File 2 — `playbook.md`**: Write the step-by-step execution guide with explicit tools, URLs, and failure handling.

**File 3 — `eval_criteria.md`**: Write the external validation rules with Python code snippets.

**File 4 — `cron_config.md`**: Write the scheduling config with cron expression and prompt template.

**File 5 — `heartbeat.md`**: Write the initial Layer 1 pointer index.
> IMPORTANT: Write to `{workspace}/heartbeat.md` (workspace root).
> Use the three-layer template format with System Status, Execution Pointer, Knowledge Index, and Active Alerts sections.
> Initial state: `idle`, `Step 0`, Circuit Breaker `off`.

**File 6 — `progress.md`**: Write the initial progress log at `{workspace}/progress.md`.

### Step A4: Create Output Directory Structure

```bash
mkdir -p /path/to/workspace/output
mkdir -p /path/to/workspace/knowledge
mkdir -p /path/to/workspace/logs
```

### Step A5: Verify Workspace is Ready

```bash
python3 {skill_dir}/scripts/harness_boot.py /path/to/workspace
```

The output must say "Workspace is ready". If it shows issues, fix them.

### Step A6: Set Up Cron Schedule

```bash
python3 {skill_dir}/scripts/harness_setup_cron.py /path/to/workspace
```

Then use the `schedule` tool with those parameters. Also set up a secondary KAIROS dream schedule:
```bash
# Dream mode: run once daily during off-hours (e.g., 3 AM)
# Add to cron: python3 {skill_dir}/scripts/harness_dream.py /path/to/workspace
```

### Step A7: Execute the First Run Immediately

Do NOT wait for the first cron trigger. Begin executing using Workflow B below.

---

## Workflow B: Executing a Task (Cron Trigger)

### Step B1: Boot and Check Status

```bash
python3 {skill_dir}/scripts/harness_boot.py /path/to/workspace
```

Read the output carefully:
- If `mission_complete` → Stop.
- If `blocked` or Circuit Breaker `tripped` → Stop. Wait for human intervention.
- If stuck detected (status still `running`) → Boot will auto-recover.
- Otherwise → Proceed.

### Step B2: Mark Start

```bash
python3 {skill_dir}/scripts/harness_heartbeat.py /path/to/workspace start
```

### Step B3: Read Context (Cache-Aware Order)

Read in this order to maximize prompt cache hits (static content first):
1. `{workspace}/mission.md` — goal and constraints (rarely changes)
2. `{workspace}/eval_criteria.md` — validation rules (rarely changes)
3. `{workspace}/playbook.md` — execution steps (semi-static)
4. `{workspace}/heartbeat.md` — current state pointer (changes each run)
5. Only load `knowledge/*.md` topic files relevant to the current step

### Step B4: Execute from Breakpoint

Perform the steps defined in `playbook.md`, starting from the step recorded in `heartbeat.md`.

During execution, log events to the execution stream:
```bash
python3 {skill_dir}/scripts/harness_memory.py /path/to/workspace stream \
  --step "Step X" --event "Description of what happened"
```

When discovering reusable knowledge, save it to a topic file:
```bash
python3 {skill_dir}/scripts/harness_memory.py /path/to/workspace learn \
  --topic "topic_name" --insight "What was learned"
```

### Step B5: Mark Completion or Failure

If succeeded:
```bash
python3 {skill_dir}/scripts/harness_heartbeat.py /path/to/workspace done \
  --step "Step X" --summary "Brief summary"
```

If failed:
```bash
python3 {skill_dir}/scripts/harness_heartbeat.py /path/to/workspace fail \
  --step "Step X" --error "Error description"
```

### Step B6: External Validation

```bash
python3 {skill_dir}/scripts/harness_eval.py /path/to/workspace
```

### Step B7: Entropy Control (Every 10 Runs)

```bash
python3 {skill_dir}/scripts/harness_cleanup.py /path/to/workspace
```

### Step B8: Mission Complete Check

If all completion criteria met:
```bash
python3 {skill_dir}/scripts/harness_heartbeat.py /path/to/workspace mission_complete
```

---

## Workflow C: Multi-Agent Parallel Execution (Optional)

For tasks that can be parallelized (e.g., processing multiple independent items):

### Step C1: Initialize Agents

```bash
python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace init --agents 3
```

### Step C2: Dispatch Subtasks

```bash
python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace dispatch \
  --task "Process item X" --step "Step 2.1"
```

### Step C3: Monitor and Collect

```bash
python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace status
python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace collect
```

### Step C4: Cleanup

```bash
python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace cleanup
```

---

## Critical Rules (NEVER Violate)

1. **heartbeat.md and progress.md always live at `{workspace}/` root** — not any subdirectory.
2. **Never leave placeholder text in any file** — overwrite with real content before running.
3. **Never self-certify completion** — always run `harness_eval.py` as the external validator.
4. **Never skip reading heartbeat.md** — always resume from the recorded breakpoint.
5. **Never modify mission.md during execution** — it is the user's constitution, read-only.
6. **Always execute the first run immediately** after setup.
7. **Respect the circuit breaker** — if tripped, do NOT attempt to bypass it.
8. **Log to execution stream** — use `harness_memory.py stream` for all significant events.
9. **Distill, don't dump** — knowledge files should contain insights, not raw logs.
10. **Read static content first** — mission.md and eval_criteria.md before dynamic state files.
