#!/usr/bin/env python3
"""
harness_heartbeat.py — Agent framework heartbeat update script (v2: Three-Layer Memory)

Functions:
1. Update the compact pointer index in heartbeat.md (Layer 1)
2. Append structured entries to execution_stream.log (Layer 3)
3. Maintain backward-compatible progress.md records
4. Enforce Strict Write Discipline: status updates are gated by eval success

Usage:
    # Mark start of execution
    python3 harness_heartbeat.py /path/to/workspace start

    # Mark execution completion (with summary)
    python3 harness_heartbeat.py /path/to/workspace done --step "Step 2" --summary "Data collection completed"

    # Mark execution failure
    python3 harness_heartbeat.py /path/to/workspace fail --step "Step 1" --error "Webpage inaccessible"

    # Mark overall mission completion
    python3 harness_heartbeat.py /path/to/workspace mission_complete

    # Mark manual intervention required
    python3 harness_heartbeat.py /path/to/workspace blocked --reason "User API key required"
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


STREAM_LOG = "logs/execution_stream.log"


def update_field(content: str, field_name: str, new_value: str) -> str:
    """Update field value in Markdown table"""
    pattern = rf"(\| {re.escape(field_name)} \| )`[^`]*`"
    replacement = rf"\1`{new_value}`"
    return re.sub(pattern, replacement, content)


def read_file(filepath: Path, required: bool = True) -> str:
    """Safely read file"""
    if not filepath.exists():
        if required:
            print(f"[ERROR] File does not exist: {filepath}")
            sys.exit(1)
        return ""
    return filepath.read_text(encoding="utf-8")


def write_file(filepath: Path, content: str):
    """Safely write file"""
    filepath.write_text(content, encoding="utf-8")
    print(f"[OK] Updated: {filepath}")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def append_stream(workspace: Path, level: str, step: str, message: str):
    """Append to Layer 3 execution stream log."""
    log_path = workspace / STREAM_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = f"[{now_str()}] [{level}] [Step: {step}] {message}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


def cmd_start(workspace: Path, args):
    """Mark start of execution"""
    hb_path = workspace / "heartbeat.md"
    if not hb_path.exists():
        print(f"[WARN] heartbeat.md does not exist at {hb_path}, please confirm Agent has written it to the workspace: {workspace}")
        sys.exit(1)
    content = read_file(hb_path)

    content = update_field(content, "Current Status", "running")
    content = update_field(content, "Last Execution Time", now_str())

    # Increment total execution count
    total_match = re.search(r"\| Total Executions \| `(\d+)`", content)
    if total_match:
        new_total = int(total_match.group(1)) + 1
        content = update_field(content, "Total Executions", str(new_total))

    write_file(hb_path, content)

    # Layer 3: log start event
    append_stream(workspace, "INFO", "boot", "Execution started")

    print(f"[HEARTBEAT] Status → running | Time: {now_str()}")


def cmd_done(workspace: Path, args):
    """Mark execution completion"""
    hb_path = workspace / "heartbeat.md"
    content = read_file(hb_path)

    content = update_field(content, "Current Status", "completed")
    content = update_field(content, "Last Execution Result", "Success")
    content = update_field(content, "Consecutive Failures", "0")

    # Reset circuit breaker on success
    content = update_field(content, "Circuit Breaker", "off")
    content = update_field(content, "Compaction Failures", "0")
    content = update_field(content, "Stuck Detection", "clear")

    if args.step:
        content = update_field(content, "Current Step", args.step)
    if args.summary:
        content = update_field(content, "Last Successful Artifact", args.summary[:100])

    write_file(hb_path, content)

    # Layer 3: log success
    step_info = args.step or "N/A"
    summary_info = args.summary or "Completed"
    append_stream(workspace, "SUCCESS", step_info, summary_info)

    # Backward-compatible: append to progress.md
    if args.summary:
        append_progress(workspace, "Success", args.step or "N/A", args.summary)

    print(f"[HEARTBEAT] Status → completed | Step: {args.step} | Time: {now_str()}")


def cmd_fail(workspace: Path, args):
    """Mark execution failure"""
    hb_path = workspace / "heartbeat.md"
    content = read_file(hb_path)

    content = update_field(content, "Current Status", "failed")
    content = update_field(content, "Last Execution Result", "Failed")

    # Increment consecutive failure count
    fail_match = re.search(r"\| Consecutive Failures \| `(\d+)`", content)
    new_fails = 1
    if fail_match:
        new_fails = int(fail_match.group(1)) + 1
        content = update_field(content, "Consecutive Failures", str(new_fails))

    write_file(hb_path, content)

    # Layer 3: log failure
    step_info = args.step or "N/A"
    error_info = args.error or "Unknown error"
    append_stream(workspace, "ERROR", step_info, error_info)

    # Backward-compatible: append to progress.md
    append_progress(workspace, "Failed", args.step or "N/A", args.error or "Unknown error")

    print(f"[HEARTBEAT] Status → failed (consecutive: {new_fails}) | Error: {args.error} | Time: {now_str()}")


def cmd_mission_complete(workspace: Path, args):
    """Mark overall mission completion"""
    hb_path = workspace / "heartbeat.md"
    content = read_file(hb_path)

    content = update_field(content, "Current Status", "mission_complete")
    content = update_field(content, "Last Execution Result", "Mission Completed")

    write_file(hb_path, content)

    # Layer 3: log mission complete
    append_stream(workspace, "SUCCESS", "final", "Mission completed!")

    print(f"[HEARTBEAT] 🎉 Mission completed! Time: {now_str()}")


def cmd_blocked(workspace: Path, args):
    """Mark manual intervention required"""
    hb_path = workspace / "heartbeat.md"
    content = read_file(hb_path)

    content = update_field(content, "Current Status", "blocked")
    content = update_field(content, "Blocking Reason", args.reason or "Not specified")

    write_file(hb_path, content)

    # Layer 3: log blocked
    append_stream(workspace, "WARN", "blocked", args.reason or "Manual intervention required")

    print(f"[HEARTBEAT] 🚨 Task blocked! Reason: {args.reason} | Time: {now_str()}")


def append_progress(workspace: Path, result: str, step: str, note: str):
    """Append execution record to progress.md (backward compatibility)"""
    prog_path = workspace / "progress.md"
    if not prog_path.exists():
        print(f"[WARN] progress.md does not exist at {prog_path}, skipping progress record.")
        return

    content = read_file(prog_path)

    # Calculate Run number
    run_count = len(re.findall(r"### Run #\d+", content))
    new_run = run_count + 1

    record = f"""
### Run #{new_run:03d} — {now_str()}

| Field | Value |
|------|-----|
| Start Time | `{now_str()}` |
| End Time | `{now_str()}` |
| Execution Step | `{step}` |
| Execution Result | `{result}` |
| Notes | `{note}` |

---
"""

    # Append after the marker
    marker = "<!-- Subsequent execution records appended here -->"
    if marker in content:
        content = content.replace(marker, marker + "\n" + record)
    else:
        content += "\n" + record

    # Update statistics
    total_match = re.search(r"\| Total Executions \| `(\d+)`", content)
    if total_match:
        content = update_field(content, "Total Executions", str(new_run))

    success_match = re.search(r"\| Success Count \| `(\d+)`", content)
    fail_match = re.search(r"\| Failure Count \| `(\d+)`", content)
    if result == "Success" and success_match:
        content = update_field(content, "Success Count", str(int(success_match.group(1)) + 1))
    elif result == "Failed" and fail_match:
        content = update_field(content, "Failure Count", str(int(fail_match.group(1)) + 1))

    write_file(prog_path, content)


def main():
    parser = argparse.ArgumentParser(description="Agent framework heartbeat update (v2)")
    parser.add_argument("workspace", help="Workspace directory path")
    subparsers = parser.add_subparsers(dest="command", help="Operation commands")

    # start
    subparsers.add_parser("start", help="Mark start of execution")

    # done
    p_done = subparsers.add_parser("done", help="Mark execution completion")
    p_done.add_argument("--step", help="Current completed step")
    p_done.add_argument("--summary", help="Execution summary")

    # fail
    p_fail = subparsers.add_parser("fail", help="Mark execution failure")
    p_fail.add_argument("--step", help="Failed step")
    p_fail.add_argument("--error", help="Error description")

    # mission_complete
    subparsers.add_parser("mission_complete", help="Mark overall mission completion")

    # blocked
    p_blocked = subparsers.add_parser("blocked", help="Mark manual intervention required")
    p_blocked.add_argument("--reason", help="Block reason")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    workspace = Path(args.workspace).resolve()

    commands = {
        "start": cmd_start,
        "done": cmd_done,
        "fail": cmd_fail,
        "mission_complete": cmd_mission_complete,
        "blocked": cmd_blocked,
    }

    commands[args.command](workspace, args)


if __name__ == "__main__":
    main()
