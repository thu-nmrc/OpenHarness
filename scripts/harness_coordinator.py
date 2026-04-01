#!/usr/bin/env python3
"""
harness_coordinator.py — Multi-Agent Coordinator (File-System IPC)

Inspired by Claude Code's leaked multi-agent orchestration architecture,
which uses natural-language prompt rules + XML protocol for inter-process
communication. This implementation uses a simpler file-system-based
inbox/outbox pattern suitable for open-source LLM agents.

Architecture:
    Coordinator (this script) ──┬── Worker 1 (separate agent session)
                                ├── Worker 2
                                └── Worker N

Communication Protocol:
    - Coordinator writes task files to  {workspace}/agents/{agent_id}/inbox/
    - Worker reads inbox, executes, writes result to outbox/
    - Coordinator polls outbox/ for results
    - All messages use a simple XML-like Markdown format

Usage:
    # Initialize multi-agent workspace
    python3 harness_coordinator.py /workspace init --agents 3

    # Dispatch a subtask to a specific agent
    python3 harness_coordinator.py /workspace dispatch --agent worker-1 \
        --task "Scrape the top 10 articles from site X" --step "Step 2.1"

    # Dispatch to any available agent (auto-assign)
    python3 harness_coordinator.py /workspace dispatch --task "Analyze dataset" --step "Step 3"

    # Check status of all agents
    python3 harness_coordinator.py /workspace status

    # Collect results from all agents
    python3 harness_coordinator.py /workspace collect

    # Clean up completed tasks
    python3 harness_coordinator.py /workspace cleanup
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


AGENTS_DIR = "agents"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def task_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


# ─────────────────────────────────────────────
# Init
# ─────────────────────────────────────────────

def cmd_init(workspace: Path, args):
    """Initialize multi-agent workspace structure."""
    agents_dir = workspace / AGENTS_DIR
    agents_dir.mkdir(parents=True, exist_ok=True)

    num_agents = args.agents
    created = []

    for i in range(1, num_agents + 1):
        agent_id = f"worker-{i}"
        agent_dir = agents_dir / agent_id
        (agent_dir / "inbox").mkdir(parents=True, exist_ok=True)
        (agent_dir / "outbox").mkdir(parents=True, exist_ok=True)

        # Write agent manifest
        manifest = {
            "agent_id": agent_id,
            "created_at": now_str(),
            "status": "idle",
            "current_task": None,
            "completed_tasks": 0,
        }
        manifest_path = agent_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        created.append(agent_id)

    # Write coordinator config
    config = {
        "coordinator_version": "1.0",
        "created_at": now_str(),
        "agents": created,
        "protocol": "file-system-ipc",
        "message_format": "markdown-xml",
    }
    config_path = agents_dir / "coordinator_config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    print(f"[COORDINATOR] Initialized {num_agents} agent(s):")
    for a in created:
        print(f"  - {a}")
    print(f"[COORDINATOR] Config: {config_path}")


# ─────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────

def _find_available_agent(workspace: Path) -> str:
    """Find an idle agent to assign a task to."""
    agents_dir = workspace / AGENTS_DIR
    if not agents_dir.exists():
        return None

    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name.startswith("."):
            continue
        manifest_path = agent_dir / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("status") == "idle":
                return manifest["agent_id"]

    return None


def cmd_dispatch(workspace: Path, args):
    """Dispatch a subtask to an agent."""
    agent_id = args.agent
    if not agent_id:
        agent_id = _find_available_agent(workspace)
        if not agent_id:
            print("[COORDINATOR] ERROR: No available agents. All are busy or none initialized.")
            sys.exit(1)
        print(f"[COORDINATOR] Auto-assigned to: {agent_id}")

    agent_dir = workspace / AGENTS_DIR / agent_id
    if not agent_dir.exists():
        print(f"[COORDINATOR] ERROR: Agent '{agent_id}' not found.")
        sys.exit(1)

    tid = task_id()
    task_file = agent_dir / "inbox" / f"task_{tid}.md"

    # Write task in XML-like Markdown format (inspired by Claude Code's protocol)
    task_content = f"""<!-- COORDINATOR TASK -->
<task>
  <id>{tid}</id>
  <dispatched_at>{now_str()}</dispatched_at>
  <parent_step>{args.step or 'unspecified'}</parent_step>
  <priority>{args.priority or 'normal'}</priority>
</task>

## Task Description

{args.task}

## Expected Output

Write your result to `outbox/result_{tid}.md` using this format:

```
<!-- WORKER RESULT -->
<result>
  <task_id>{tid}</task_id>
  <completed_at>[timestamp]</completed_at>
  <status>success|failed</status>
  <summary>[one-line summary]</summary>
</result>

## Result Details

[Your detailed output here]
```

## Constraints

- Stay within the scope of this subtask
- Do NOT modify files outside your agent directory
- Report failures immediately instead of retrying indefinitely
"""

    task_file.write_text(task_content, encoding="utf-8")

    # Update agent manifest
    manifest_path = agent_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "busy"
    manifest["current_task"] = tid
    manifest["last_dispatched"] = now_str()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[COORDINATOR] Dispatched task {tid} to {agent_id}")
    print(f"  Task file: {task_file}")
    print(f"  Step: {args.step or 'unspecified'}")


# ─────────────────────────────────────────────
# Status
# ─────────────────────────────────────────────

def cmd_status(workspace: Path, args):
    """Show status of all agents."""
    agents_dir = workspace / AGENTS_DIR

    if not agents_dir.exists():
        print("[COORDINATOR] No agents directory found. Run 'init' first.")
        return

    print("=" * 60)
    print("  OpenHarness Multi-Agent Status")
    print(f"  Time: {now_str()}")
    print("=" * 60)

    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name.startswith("."):
            continue

        manifest_path = agent_dir / "manifest.json"
        if not manifest_path.exists():
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        inbox_count = len(list((agent_dir / "inbox").glob("task_*.md")))
        outbox_count = len(list((agent_dir / "outbox").glob("result_*.md")))

        status_icon = {
            "idle": "🟢",
            "busy": "🟡",
            "failed": "🔴",
            "completed": "✅",
        }.get(manifest.get("status", "unknown"), "⚪")

        print(f"\n{status_icon} {manifest['agent_id']}")
        print(f"   Status: {manifest.get('status', 'unknown')}")
        print(f"   Current task: {manifest.get('current_task', 'None')}")
        print(f"   Inbox: {inbox_count} task(s) | Outbox: {outbox_count} result(s)")
        print(f"   Completed: {manifest.get('completed_tasks', 0)}")

    print("\n" + "=" * 60)


# ─────────────────────────────────────────────
# Collect
# ─────────────────────────────────────────────

def cmd_collect(workspace: Path, args):
    """Collect results from all agent outboxes."""
    agents_dir = workspace / AGENTS_DIR
    results = []

    if not agents_dir.exists():
        print("[COORDINATOR] No agents directory found.")
        return

    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name.startswith("."):
            continue

        outbox = agent_dir / "outbox"
        for result_file in sorted(outbox.glob("result_*.md")):
            content = result_file.read_text(encoding="utf-8")

            # Parse result metadata
            task_id_match = re.search(r"<task_id>(.+?)</task_id>", content)
            status_match = re.search(r"<status>(.+?)</status>", content)
            summary_match = re.search(r"<summary>(.+?)</summary>", content)

            result = {
                "agent": agent_dir.name,
                "file": str(result_file),
                "task_id": task_id_match.group(1) if task_id_match else "unknown",
                "status": status_match.group(1) if status_match else "unknown",
                "summary": summary_match.group(1) if summary_match else "No summary",
            }
            results.append(result)

            # Update agent manifest
            manifest_path = agent_dir / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["status"] = "idle"
                manifest["current_task"] = None
                manifest["completed_tasks"] = manifest.get("completed_tasks", 0) + 1
                manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if results:
        print(f"[COORDINATOR] Collected {len(results)} result(s):")
        for r in results:
            icon = "✅" if r["status"] == "success" else "❌"
            print(f"  {icon} [{r['agent']}] Task {r['task_id']}: {r['summary']}")
    else:
        print("[COORDINATOR] No results to collect.")

    return results


# ─────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────

def cmd_cleanup(workspace: Path, args):
    """Archive completed tasks and results."""
    agents_dir = workspace / AGENTS_DIR
    archive_dir = workspace / "logs" / "agent_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived = 0

    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir() or agent_dir.name.startswith("."):
            continue

        # Archive processed results
        for result_file in (agent_dir / "outbox").glob("result_*.md"):
            dest = archive_dir / f"{agent_dir.name}_{result_file.name}"
            result_file.rename(dest)
            archived += 1

        # Archive dispatched tasks that have results
        for task_file in (agent_dir / "inbox").glob("task_*.md"):
            tid = re.search(r"task_(.+?)\.md", task_file.name)
            if tid:
                result_exists = (archive_dir / f"{agent_dir.name}_result_{tid.group(1)}.md").exists()
                if result_exists:
                    dest = archive_dir / f"{agent_dir.name}_{task_file.name}"
                    task_file.rename(dest)
                    archived += 1

    print(f"[COORDINATOR] Archived {archived} file(s) to {archive_dir}")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OpenHarness Multi-Agent Coordinator"
    )
    parser.add_argument("workspace", help="Workspace directory path")
    subparsers = parser.add_subparsers(dest="command", help="Coordinator commands")

    # init
    p_init = subparsers.add_parser("init", help="Initialize multi-agent workspace")
    p_init.add_argument("--agents", type=int, default=3, help="Number of worker agents")

    # dispatch
    p_dispatch = subparsers.add_parser("dispatch", help="Dispatch a subtask")
    p_dispatch.add_argument("--agent", help="Target agent ID (auto-assign if omitted)")
    p_dispatch.add_argument("--task", required=True, help="Task description")
    p_dispatch.add_argument("--step", help="Parent step reference")
    p_dispatch.add_argument("--priority", default="normal", choices=["low", "normal", "high", "critical"])

    # status
    subparsers.add_parser("status", help="Show all agent statuses")

    # collect
    subparsers.add_parser("collect", help="Collect results from agents")

    # cleanup
    subparsers.add_parser("cleanup", help="Archive completed tasks")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    workspace = Path(args.workspace).resolve()

    commands = {
        "init": cmd_init,
        "dispatch": cmd_dispatch,
        "status": cmd_status,
        "collect": cmd_collect,
        "cleanup": cmd_cleanup,
    }

    commands[args.command](workspace, args)


if __name__ == "__main__":
    main()
