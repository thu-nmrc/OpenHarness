---
name: harness-24h
description: A framework for long-running, autonomous agents based on Harness Engineering principles. When a user describes a task idea, Agent automatically initializes the workspace, fills all template files, sets up the cron schedule, and begins execution immediately. No manual file editing required.
---

# Harness-24h | 24-hour Harness Framework

This skill provides a complete framework for executing long-running, autonomous tasks based on the principles of Harness Engineering. It solves the problems of long-term amnesia, state persistence, external validation, and entropy control.

**Key principle**: The user only describes their task idea. Agent handles everything else — workspace creation, filling all files, setting up the cron schedule, and starting execution.

## Core Concepts

The framework is built around 6 core components of Harness Engineering:
1. **Machine-verifiable contracts**: `mission.md` and `eval_criteria.md`
2. **Knowledge as system of record**: `playbook.md`
3. **Agent senses and effectors**: Configured via `harness_boot.py`
4. **Solving long-term amnesia**: `heartbeat.md` and `progress.md`
5. **Externalized validation loop**: `harness_eval.py`
6. **Mechanized constraints and entropy control**: `harness_cleanup.py`

For detailed architecture, read `references/architecture.md`.
For common anti-patterns to avoid, read `references/anti-patterns.md`.

---

## Workflow A: User Describes a New Task (FULLY AUTOMATIC)

When a user describes a task idea (e.g. "monitor AI news and write 50 deep-dive articles"), follow ALL steps below without asking the user to fill in any files manually.

### Step A1: Decide Workspace Path

Choose a workspace path based on the task name. Convention:
```
/home/ubuntu/{task-slug}/
```
For example, for "AI news deep-dive articles" → `/home/ubuntu/ai-deepdive/`

### Step A2: Initialize Workspace

```bash
python3 /home/ubuntu/skills/harness-24h/scripts/harness_boot.py /path/to/workspace --init
```

This copies all template files into the workspace. Do NOT ask the user to run this.

### Step A3: Fill ALL Template Files Yourself

Based on the user's task description, Agent must write the following files completely. Do NOT leave any placeholder text (`[Fill in here...]`, `[Example:...]`) in any file.

**File 1 — `mission.md`**: Write the task contract. Must include:
- Task name (one sentence)
- Precise, unambiguous goal
- Completion criteria table: each row must be a machine-checkable condition (file exists, count ≥ N, field non-empty, etc.) — NOT subjective judgments
- Allowed and forbidden operations
- Escalation rules (what to do after N consecutive failures)
- Execution cycle (frequency, max duration per run, deadline)
- Output artifact definitions (format, path, naming convention)

**File 2 — `playbook.md`**: Write the step-by-step execution guide. Must include:
- A numbered list of steps (Step 0 through Step N)
- For each step: what to do, which tools to use, completion signal, failure handling
- Tacit knowledge made explicit (URLs, CSS selectors, API endpoints, data formats, file naming rules)
- Reusable code snippets for common operations (file naming, counting, validation)

**File 3 — `eval_criteria.md`**: Write the external validation rules. Must include:
- Per-artifact validation criteria with machine-checkable conditions
- Python code snippets for each check
- Overall task completion validation
- Quality grading (pass / needs-rework / fail)

**File 4 — `cron_config.md`**: Write the scheduling config. Must include:
- Schedule type (`cron`)
- Cron expression matching the task's required frequency
- `repeat: true`
- A complete prompt template that tells Agent exactly what to do on each trigger

**File 5 — `heartbeat.md`**: Write the initial heartbeat state file.
> ⚠️ IMPORTANT PATH RULE: Write `heartbeat.md` to the **workspace root**, i.e., `{workspace}/heartbeat.md`.
> This is the same directory as `mission.md` and `playbook.md`.
> Do NOT write it to the skill's template directory or any subdirectory.

Initial heartbeat state must have:
- `current_status` = `idle`
- `current_step` = `Step 0 (not started)`
- `completed_article_count` or equivalent progress counter = `0 / {target}`
- `total_runs` = `0`
- `consecutive_failures` = `0`
- Task name filled in from mission.md
- All source health status rows filled with `not checked`

**File 6 — `progress.md`**: Write the initial progress log.
> ⚠️ IMPORTANT PATH RULE: Write `progress.md` to the **workspace root**, i.e., `{workspace}/progress.md`.

Initial progress must have:
- Task name filled in
- Completion criteria table populated from mission.md (all rows marked `not met`)
- All counters initialized to `0`

### Step A4: Create Output Directory Structure

Create any output subdirectories required by the task. For example:
```bash
mkdir -p /path/to/workspace/output/articles
mkdir -p /path/to/workspace/output/drafts
```
Also initialize any seed data files (e.g., `echo "[]" > /path/to/workspace/output/topic_pool.json`).

### Step A5: Verify Workspace is Ready

```bash
python3 /home/ubuntu/skills/harness-24h/scripts/harness_boot.py /path/to/workspace
```

The output must say "✅ Workspace ready, execution can begin."
If it shows issues, fix them before proceeding.

### Step A6: Set Up Cron Schedule

Run the setup script to get schedule parameters:
```bash
python3 /home/ubuntu/skills/harness-24h/scripts/harness_setup_cron.py /path/to/workspace
```

Then immediately use the `schedule` tool with those parameters. Do NOT ask the user to do this.

The `prompt` field of the schedule tool must instruct Agent to:
1. Run `harness_boot.py` to check status
2. Read `mission.md`, `heartbeat.md`, `playbook.md`
3. Execute from the breakpoint recorded in `heartbeat.md`
4. Update `heartbeat.md` and `progress.md` after each run
5. Stop if status is `mission_complete` or `blocked`

The `playbook` field of the schedule tool must summarize the harness execution best practices.

### Step A7: Execute the First Run Immediately

Do NOT wait for the first cron trigger. After setting up the schedule, immediately begin executing the task using the same sequence as Workflow B below.

---

## Workflow B: Executing a Task (Cron Trigger)

When triggered by a scheduled cron job, ALWAYS follow this strict sequence:

### Step B1: Boot and Check Status

```bash
python3 /home/ubuntu/skills/harness-24h/scripts/harness_boot.py /path/to/workspace
```

Read the output carefully:
- If status is `mission_complete` → Stop. Task is done.
- If status is `blocked` → Stop. Wait for human intervention.
- If `consecutive_failures >= 3` → Mark `blocked`, stop.
- Otherwise → Proceed.

### Step B2: Mark Start

```bash
python3 /home/ubuntu/skills/harness-24h/scripts/harness_heartbeat.py /path/to/workspace start
```

> ⚠️ heartbeat.md is always at `{workspace}/heartbeat.md` — the same directory as mission.md.

### Step B3: Read Context

In this order:
1. Read `{workspace}/mission.md` — understand goal and constraints
2. Read `{workspace}/heartbeat.md` — find the exact step to resume from
3. Read `{workspace}/playbook.md` — get the execution steps

### Step B4: Execute from Breakpoint

Perform the steps defined in `playbook.md`, starting from the step recorded in `heartbeat.md`.

### Step B5: Mark Completion or Failure

If this round succeeded:
```bash
python3 /home/ubuntu/skills/harness-24h/scripts/harness_heartbeat.py /path/to/workspace done \
  --step "Step X" --summary "Brief summary of what was accomplished"
```

If this round failed:
```bash
python3 /home/ubuntu/skills/harness-24h/scripts/harness_heartbeat.py /path/to/workspace fail \
  --step "Step X" --error "Error description"
```

### Step B6: External Validation

```bash
python3 /home/ubuntu/skills/harness-24h/scripts/harness_eval.py /path/to/workspace
```

If validation fails: decide whether to retry or mark as blocked.

### Step B7: Entropy Control (Every 10 Runs)

```bash
python3 /home/ubuntu/skills/harness-24h/scripts/harness_cleanup.py /path/to/workspace
```

### Step B8: Mission Complete Check

If all completion criteria in `mission.md` are met:
```bash
python3 /home/ubuntu/skills/harness-24h/scripts/harness_heartbeat.py /path/to/workspace mission_complete
```

---

## Critical Rules (NEVER Violate)

1. **heartbeat.md and progress.md always live at `{workspace}/heartbeat.md` and `{workspace}/progress.md`** — the workspace root, not any subdirectory.
2. **Never leave placeholder text in any file** — if you initialized from templates, you must overwrite with real content before running.
3. **Never self-certify completion** — always run `harness_eval.py` as the external validator.
4. **Never skip reading heartbeat.md** — always resume from the recorded breakpoint.
5. **Never modify mission.md during execution** — it is the user's constitution, read-only for Agent.
6. **Always execute the first run immediately** after setup, without waiting for the cron trigger.
