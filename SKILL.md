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

### Step A6: Set Up Cron Schedules

**Primary Schedule (Main Task Execution)**:

```bash
python3 {skill_dir}/scripts/harness_setup_cron.py /path/to/workspace
```

Read the output and use the `schedule` tool with those parameters.

**Secondary Schedule (KAIROS Dream Mode — REQUIRED)**:

Dream mode MUST be scheduled separately to run during off-hours (e.g., 3 AM daily). This is NOT optional — it prevents memory bloat and knowledge fragmentation.

Use the `schedule` tool with these parameters:
```
name: {task-name}-dream
type: cron
cron: 0 0 3 * * *  (daily at 3 AM, adjust timezone as needed)
repeat: true
prompt: |
  Run KAIROS dream mode memory consolidation for the harness task at /path/to/workspace.
  
  Execute:
  python3 {skill_dir}/scripts/harness_dream.py /path/to/workspace
  
  This consolidates fragmented knowledge/*.md files, prunes stale Layer 1 pointers,
  extracts patterns from logs/execution_stream.log, and updates playbook.md with
  distilled best practices. Only runs when the main task is idle.
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

**How to find relevant knowledge topics**:
```bash
# List all registered topics
python3 {skill_dir}/scripts/harness_memory.py /path/to/workspace topics

# Search execution stream for keywords
python3 {skill_dir}/scripts/harness_memory.py /path/to/workspace search --query "timeout"
```

Then read only the `knowledge/{topic}.md` files mentioned in `heartbeat.md`'s Knowledge Index section.

### Step B4: Execute from Breakpoint

Perform the steps defined in `playbook.md`, starting from the step recorded in `heartbeat.md`.

**During execution, actively use the memory system**:

**Log significant events** (use liberally — this feeds KAIROS dream mode):
```bash
python3 {skill_dir}/scripts/harness_memory.py /path/to/workspace stream \
  --step "Step 2.3" --event "Fetched 50 articles from API, took 12s"

python3 {skill_dir}/scripts/harness_memory.py /path/to/workspace stream \
  --step "Step 3.1" --event "Rate limit hit, waiting 60s" --level WARN

python3 {skill_dir}/scripts/harness_memory.py /path/to/workspace stream \
  --step "Step 4" --event "Validation failed: missing required field 'author'" --level ERROR
```

**Save reusable knowledge** (when you discover a pattern or workaround):
```bash
python3 {skill_dir}/scripts/harness_memory.py /path/to/workspace learn \
  --topic "api_rate_limits" \
  --insight "GitHub API returns 403 after 5000 requests/hour. Wait 60s and retry with exponential backoff."

python3 {skill_dir}/scripts/harness_memory.py /path/to/workspace learn \
  --topic "data_validation" \
  --insight "Articles from source X often missing 'author' field. Use 'Unknown' as default and log warning."
```

This creates/updates `knowledge/api_rate_limits.md` and registers the pointer in `heartbeat.md`.

### Step B5: Mark Completion or Failure

If succeeded:
```bash
python3 {skill_dir}/scripts/harness_heartbeat.py /path/to/workspace done \
  --step "Step 4" --summary "Processed 50 articles, 3 validation warnings"
```

If failed:
```bash
python3 {skill_dir}/scripts/harness_heartbeat.py /path/to/workspace fail \
  --step "Step 3" --error "API timeout after 3 retries"
```

### Step B6: External Validation

```bash
python3 {skill_dir}/scripts/harness_eval.py /path/to/workspace
```

### Step B7: Entropy Control (Every 10 Runs)

```bash
python3 {skill_dir}/scripts/harness_cleanup.py /path/to/workspace
```

This auto-compacts `progress.md` if it exceeds 2000 lines, archives old execution stream logs, and checks memory integrity.

### Step B8: Mission Complete Check

If all completion criteria met:
```bash
python3 {skill_dir}/scripts/harness_heartbeat.py /path/to/workspace mission_complete
```

---

## Workflow C: KAIROS Dream Mode (Scheduled Off-Hours)

**When to run**: Automatically via the secondary cron schedule set up in Step A6. Typically runs once daily at 3 AM.

**What it does**:
1. Reads `logs/execution_stream.log` from the last 24 hours
2. Extracts recurring patterns (errors, successes, warnings)
3. Consolidates fragmented `knowledge/*.md` files
4. Prunes stale Layer 1 pointers from `heartbeat.md`
5. Updates `playbook.md` with distilled best practices
6. Writes a human-readable journal to `logs/dream_journal.md`

**Manual invocation** (for testing or immediate consolidation):
```bash
# Full dream cycle
python3 {skill_dir}/scripts/harness_dream.py /path/to/workspace

# Dry run (show what would be done without making changes)
python3 {skill_dir}/scripts/harness_dream.py /path/to/workspace --dry-run

# Only consolidate knowledge, skip playbook update
python3 {skill_dir}/scripts/harness_dream.py /path/to/workspace --skip-playbook
```

**CRITICAL**: Dream mode should ONLY run when the main task is idle (status != `running`). The scheduled prompt in Step A6 handles this check automatically.

---

## Workflow D: Multi-Agent Parallel Execution (Optional)

**When to use**: When a single step in `playbook.md` involves processing multiple independent items (e.g., "Scrape 100 product pages", "Analyze 50 PDF documents").

**When NOT to use**: For sequential steps or when items depend on each other.

### Step D1: Initialize Agents

```bash
python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace init --agents 3
```

This creates `agents/worker-1/`, `agents/worker-2/`, `agents/worker-3/`, each with `inbox/`, `outbox/`, and `manifest.json`.

### Step D2: Dispatch Subtasks

For each independent item, dispatch a subtask:

```bash
python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace dispatch \
  --task "Scrape product page: https://example.com/product/123" \
  --step "Step 2.1"

python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace dispatch \
  --task "Scrape product page: https://example.com/product/456" \
  --step "Step 2.1"

python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace dispatch \
  --task "Scrape product page: https://example.com/product/789" \
  --step "Step 2.1"
```

Each task is written as an XML-like Markdown file to an available worker's `inbox/`.

### Step D3: Execute Worker Tasks

**Important**: The coordinator does NOT auto-execute. You must manually process each worker's inbox.

For each worker (1, 2, 3):
```bash
# Check if worker has tasks
ls /path/to/workspace/agents/worker-1/inbox/

# Read the task file
cat /path/to/workspace/agents/worker-1/inbox/task_abc123.md

# Execute the task according to its instructions
# ... (your actual scraping/processing logic here)

# Write result to outbox
cat > /path/to/workspace/agents/worker-1/outbox/result_abc123.md << 'EOF'
## Result: task_abc123

**Status**: success

**Output**:
Product title: Example Product
Price: $29.99
Stock: In stock
EOF
```

### Step D4: Monitor and Collect

Check status:
```bash
python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace status
```

Collect all results from worker outboxes:
```bash
python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace collect
```

This reads all `outbox/result_*.md` files, updates worker manifests back to idle, and prints a summary.

### Step D5: Cleanup

Archive all inbox/outbox files to `logs/agent_archive/`:
```bash
python3 {skill_dir}/scripts/harness_coordinator.py /path/to/workspace cleanup
```

---

## When to Use What

| Scenario | Tool | Timing |
|----------|------|--------|
| Log a significant event during execution | `harness_memory.py stream` | Every time something notable happens |
| Discover a reusable pattern or workaround | `harness_memory.py learn` | When you solve a problem that might recur |
| Search past execution logs for debugging | `harness_memory.py search` | When investigating errors or stuck states |
| Consolidate fragmented knowledge | `harness_dream.py` | Scheduled off-hours (e.g., 3 AM daily) |
| Process multiple independent items | `harness_coordinator.py` | Only when parallelization is beneficial |
| Check memory integrity | `harness_memory.py check` | After manual edits to knowledge files |

---

## Critical Rules (NEVER Violate)

1. **heartbeat.md and progress.md always live at `{workspace}/` root** — not any subdirectory.
2. **Never leave placeholder text in any file** — overwrite with real content before running.
3. **Never self-certify completion** — always run `harness_eval.py` as the external validator.
4. **Never skip reading heartbeat.md** — always resume from the recorded breakpoint.
5. **Never modify mission.md during execution** — it is the user's constitution, read-only.
6. **Always execute the first run immediately** after setup.
7. **Respect the circuit breaker** — if tripped, do NOT attempt to bypass it.
8. **Log to execution stream liberally** — use `harness_memory.py stream` for all significant events.
9. **Distill, don't dump** — knowledge files should contain insights, not raw logs.
10. **Read static content first** — mission.md and eval_criteria.md before dynamic state files.
11. **Always schedule KAIROS dream mode** — it is NOT optional, memory will bloat without it.
12. **Never run dream mode while task is running** — only during idle periods.
13. **Coordinator does not auto-execute** — you must manually process worker inboxes.
