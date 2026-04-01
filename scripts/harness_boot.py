#!/usr/bin/env python3
"""
harness_boot.py — Agent framework startup bootstrap script (v2: Circuit Breaker + Cache-Aware)

Functions:
1. Initialize the workspace from templates (first run)
2. Verify all required files exist
3. Read heartbeat.md (Layer 1 pointer index) and output current status summary
4. **NEW** Circuit Breaker: auto-block after N consecutive failures to prevent runaway API costs
5. **NEW** Stuck Detection: detect and flag tasks stuck in 'running' state
6. **NEW** Cache-Aware prompt separation guidance

Usage:
    python3 harness_boot.py /path/to/workspace [--init]
    python3 harness_boot.py /path/to/workspace [--max-failures 3]
"""

import argparse
import shutil
import sys
import os
import re
from datetime import datetime
from pathlib import Path


# Framework template directory (relative to this script)
SCRIPT_DIR = Path(__file__).parent.resolve()
TEMPLATE_DIR = SCRIPT_DIR.parent / "templates"

# Required files list
REQUIRED_FILES = [
    "mission.md",
    "playbook.md",
    "heartbeat.md",
    "progress.md",
    "eval_criteria.md",
    "cron_config.md",
]

# Files copied from templates on --init
TEMPLATE_COPY_FILES = ["mission.md", "playbook.md", "eval_criteria.md", "cron_config.md"]

# Files that Agent requires user to fill (must not contain placeholders)
USER_FILL_FILES = ["mission.md", "playbook.md", "eval_criteria.md", "cron_config.md"]

# Circuit breaker defaults
DEFAULT_MAX_CONSECUTIVE_FAILURES = 3
DEFAULT_MAX_COMPACTION_FAILURES = 3


def init_workspace(workspace: Path):
    """Initialize workspace from templates"""
    workspace.mkdir(parents=True, exist_ok=True)

    # Create output directories
    (workspace / "output").mkdir(exist_ok=True)
    (workspace / "logs").mkdir(exist_ok=True)
    (workspace / "knowledge").mkdir(exist_ok=True)

    # Copy knowledge README
    knowledge_readme_src = TEMPLATE_DIR / "knowledge" / "README.md"
    knowledge_readme_dst = workspace / "knowledge" / "README.md"
    if knowledge_readme_src.exists() and not knowledge_readme_dst.exists():
        shutil.copy2(knowledge_readme_src, knowledge_readme_dst)

    copied = []
    skipped = []
    for fname in TEMPLATE_COPY_FILES:
        src = TEMPLATE_DIR / fname
        dst = workspace / fname
        if dst.exists():
            skipped.append(fname)
        elif src.exists():
            shutil.copy2(src, dst)
            copied.append(fname)
        else:
            print(f"[WARN] Template file does not exist: {src}")

    print(f"[BOOT] Workspace initialized: {workspace}")
    print(f"  Copied {len(copied)} structure templates: {', '.join(copied)}")
    if skipped:
        print(f"  Skipped {len(skipped)} existing files: {', '.join(skipped)}")
    print(f"  Output directory: {workspace / 'output'}")
    print(f"  Logs directory:   {workspace / 'logs'}")
    print(f"  Knowledge (L2):   {workspace / 'knowledge'}")
    print()
    print("[NEXT] Agent needs to complete the following:")
    print(f"  ✏️  Fill in: {workspace}/mission.md")
    print(f"  ✏️  Fill in: {workspace}/playbook.md")
    print(f"  ✏️  Fill in: {workspace}/eval_criteria.md")
    print(f"  ✏️  Fill in: {workspace}/cron_config.md")
    print(f"  ✏️  Generate: {workspace}/heartbeat.md")
    print(f"  ✏️  Generate: {workspace}/progress.md")


def _is_filled(filepath: Path) -> bool:
    """Check if the file has been filled by the user (no longer contains placeholders)"""
    if not filepath.exists():
        return False
    content = filepath.read_text(encoding="utf-8")
    return "[Fill in" not in content and "[e.g.," not in content


def validate_workspace(workspace: Path) -> dict:
    """Validate workspace integrity, return status report"""
    report = {
        "workspace": str(workspace),
        "exists": workspace.exists(),
        "files": {},
        "ready": True,
        "issues": [],
    }

    if not workspace.exists():
        report["ready"] = False
        report["issues"].append(f"Workspace does not exist: {workspace}")
        return report

    for fname in REQUIRED_FILES:
        fpath = workspace / fname
        finfo = {
            "exists": fpath.exists(),
            "filled": _is_filled(fpath) if fpath.exists() else False,
            "size": fpath.stat().st_size if fpath.exists() else 0,
        }
        report["files"][fname] = finfo

        if not finfo["exists"]:
            report["ready"] = False
            report["issues"].append(f"Missing file: {fname}")
        elif fname in USER_FILL_FILES and not finfo["filled"]:
            report["ready"] = False
            report["issues"].append(f"File not filled: {fname} (still contains placeholders)")

    return report


def read_heartbeat(workspace: Path) -> dict:
    """Read heartbeat.md (Layer 1 pointer index) and parse current status"""
    hb_path = workspace / "heartbeat.md"
    if not hb_path.exists():
        return {"status": "no_heartbeat", "message": "heartbeat.md does not exist"}

    content = hb_path.read_text(encoding="utf-8")

    # Parse key fields
    status_match = re.search(r"\| Current Status \| `(.+?)`", content)
    step_match = re.search(r"\| Current Step \| `(.+?)`", content)
    last_time_match = re.search(r"\| Last Execution Time \| `(.+?)`", content)
    fail_match = re.search(r"\| Consecutive Failures \| `(\d+)`", content)
    total_match = re.search(r"\| Total Executions \| `(\d+)`", content)
    circuit_match = re.search(r"\| Circuit Breaker \| `(.+?)`", content)
    compact_fail_match = re.search(r"\| Compaction Failures \| `(\d+)`", content)
    stuck_match = re.search(r"\| Stuck Detection \| `(.+?)`", content)

    return {
        "status": status_match.group(1) if status_match else "unknown",
        "current_step": step_match.group(1) if step_match else "unknown",
        "last_execution": last_time_match.group(1) if last_time_match else "unknown",
        "consecutive_failures": int(fail_match.group(1)) if fail_match else 0,
        "total_executions": int(total_match.group(1)) if total_match else 0,
        "circuit_breaker": circuit_match.group(1) if circuit_match else "off",
        "compaction_failures": int(compact_fail_match.group(1)) if compact_fail_match else 0,
        "stuck_detection": stuck_match.group(1) if stuck_match else "clear",
    }


def update_heartbeat_field(workspace: Path, field_name: str, new_value: str):
    """Directly update a field in heartbeat.md"""
    hb_path = workspace / "heartbeat.md"
    if not hb_path.exists():
        return
    content = hb_path.read_text(encoding="utf-8")
    pattern = rf"(\| {re.escape(field_name)} \| )`[^`]*`"
    replacement = rf"\1`{new_value}`"
    content = re.sub(pattern, replacement, content)
    hb_path.write_text(content, encoding="utf-8")


def check_circuit_breaker(workspace: Path, heartbeat: dict, max_failures: int) -> bool:
    """
    Circuit Breaker Pattern: prevent runaway API costs from infinite retry loops.
    Returns True if execution should be BLOCKED, False if safe to proceed.
    """
    # Already tripped
    if heartbeat.get("circuit_breaker") == "tripped":
        print("\n🔴 CIRCUIT BREAKER IS TRIPPED — Execution blocked.")
        print("   The task has been automatically suspended due to repeated failures.")
        print("   To reset: manually set 'Circuit Breaker' to 'off' in heartbeat.md")
        print("   and set 'Consecutive Failures' to '0'.")
        return True

    # Check consecutive failures
    consecutive = heartbeat.get("consecutive_failures", 0)
    if consecutive >= max_failures:
        print(f"\n🔴 CIRCUIT BREAKER TRIPPING — {consecutive} consecutive failures (threshold: {max_failures})")
        print("   Automatically blocking task to prevent runaway API costs.")
        update_heartbeat_field(workspace, "Circuit Breaker", "tripped")
        update_heartbeat_field(workspace, "Current Status", "blocked")
        update_heartbeat_field(workspace, "Blocking Reason", f"Circuit breaker: {consecutive} consecutive failures")
        update_heartbeat_field(workspace, "Stuck Detection", f"tripped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True

    # Check compaction failures
    compact_fails = heartbeat.get("compaction_failures", 0)
    if compact_fails >= DEFAULT_MAX_COMPACTION_FAILURES:
        print(f"\n🔴 COMPACTION CIRCUIT BREAKER — {compact_fails} compaction failures")
        print("   Disabling auto-compaction to prevent wasted API calls.")
        update_heartbeat_field(workspace, "Circuit Breaker", "tripped")
        return True

    return False


def check_stuck_detection(heartbeat: dict) -> bool:
    """
    Detect tasks stuck in 'running' state (likely from a crashed previous execution).
    Returns True if stuck detected.
    """
    if heartbeat.get("status") == "running":
        print("\n⚠️  STUCK DETECTION: Status is still 'running' from a previous execution.")
        print("   The last execution likely crashed or was interrupted.")
        print("   Resetting status to 'idle' and incrementing failure count.")
        return True
    return False


def read_mission_name(workspace: Path) -> str:
    """Read mission name from mission.md"""
    mission_path = workspace / "mission.md"
    if not mission_path.exists():
        return "[Undefined]"
    content = mission_path.read_text(encoding="utf-8")
    name_match = re.search(r"\*\*Name\*\*[：:]\s*`(.+?)`", content)
    return name_match.group(1) if name_match else "[Not filled]"


def boot_report(workspace: Path, max_failures: int):
    """Generate startup report with circuit breaker and stuck detection"""
    print("=" * 60)
    print("  OpenHarness (v2) — Startup Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Validate workspace
    validation = validate_workspace(workspace)
    mission_name = read_mission_name(workspace)
    heartbeat = read_heartbeat(workspace)

    print(f"\n📋 Mission: {mission_name}")
    print(f"📁 Workspace: {workspace}")
    print(f"💓 Status: {heartbeat.get('status', 'unknown')}")
    print(f"📍 Current Step: {heartbeat.get('current_step', 'unknown')}")
    print(f"🔄 Total Executions: {heartbeat.get('total_executions', 0)}")
    print(f"❌ Consecutive Failures: {heartbeat.get('consecutive_failures', 0)}")
    print(f"🕐 Last Execution: {heartbeat.get('last_execution', 'unknown')}")
    print(f"🔌 Circuit Breaker: {heartbeat.get('circuit_breaker', 'off')}")

    # Memory layer status
    knowledge_dir = workspace / "knowledge"
    topic_count = len(list(knowledge_dir.glob("*.md"))) - 1 if knowledge_dir.exists() else 0  # exclude README
    stream_path = workspace / "logs" / "execution_stream.log"
    stream_size = f"{stream_path.stat().st_size / 1024:.1f}KB" if stream_path.exists() else "0KB"
    hb_size = f"{(workspace / 'heartbeat.md').stat().st_size / 1024:.1f}KB" if (workspace / 'heartbeat.md').exists() else "0KB"

    print(f"\n📊 Memory Layers:")
    print(f"  L1 (heartbeat.md):       {hb_size} (target: <2KB)")
    print(f"  L2 (knowledge topics):   {topic_count} topic(s)")
    print(f"  L3 (execution stream):   {stream_size}")

    if validation["issues"]:
        print(f"\n⚠️  Found {len(validation['issues'])} issues:")
        for issue in validation["issues"]:
            print(f"  - {issue}")

    # ── Circuit Breaker Check ──
    if check_circuit_breaker(workspace, heartbeat, max_failures):
        print("\n❌ Execution BLOCKED by circuit breaker. Manual intervention required.")
        print("=" * 60)
        return False

    # ── Stuck Detection ──
    if check_stuck_detection(heartbeat):
        update_heartbeat_field(workspace, "Current Status", "idle")
        fail_count = heartbeat.get("consecutive_failures", 0) + 1
        update_heartbeat_field(workspace, "Consecutive Failures", str(fail_count))
        update_heartbeat_field(workspace, "Stuck Detection", f"recovered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Status reset to 'idle'. Consecutive failures: {fail_count}")

    if heartbeat.get("status") == "mission_complete":
        print("\n🎉 Mission completed! No further execution needed.")
        print("=" * 60)
        return False

    if validation["ready"]:
        print("\n✅ Workspace is ready, execution can start.")
    else:
        print("\n❌ Workspace is not ready, please resolve the above issues first.")

    # ── Cache-Aware Guidance ──
    print("\n💡 Cache-Aware Tip: Keep mission.md and eval_criteria.md at the TOP of")
    print("   your LLM prompt (static content first) to maximize prompt cache hits.")

    print("=" * 60)
    return validation["ready"]


def main():
    parser = argparse.ArgumentParser(description="OpenHarness Startup Bootstrap (v2)")
    parser.add_argument("workspace", help="Path to workspace directory")
    parser.add_argument("--init", action="store_true", help="Initialize workspace for the first time")
    parser.add_argument("--max-failures", type=int, default=DEFAULT_MAX_CONSECUTIVE_FAILURES,
                        help=f"Circuit breaker threshold (default: {DEFAULT_MAX_CONSECUTIVE_FAILURES})")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    if args.init:
        init_workspace(workspace)
    else:
        ready = boot_report(workspace, args.max_failures)
        sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()
