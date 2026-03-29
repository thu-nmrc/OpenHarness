#!/usr/bin/env python3
"""
harness_heartbeat.py — Agent framework heartbeat update script

Functions:
1. Update the status field in heartbeat.md
2. Append execution records to progress.md
3. Record exception information

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
    print(f"[HEARTBEAT] Status → running | Time: {now_str()}")


def cmd_done(workspace: Path, args):
    """Mark execution completion"""
    hb_path = workspace / "heartbeat.md"
    content = read_file(hb_path)

    content = update_field(content, "Current Status", "completed")
    content = update_field(content, "Last Execution Result", "Success")
    content = update_field(content, "Consecutive Failures", "0")

    if args.step:
        content = update_field(content, "Current Step", args.step)
    if args.summary:
        # Update current execution summary
        content = re.sub(
            r"(## Current Execution Summary\n\n<!-- .+? -->\n\n)```\n.+?\n```",
            rf"\1```\n{now_str()} | {args.summary}\n```",
            content,
            flags=re.DOTALL,
        )

    write_file(hb_path, content)

    # Append to progress.md
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
    if fail_match:
        new_fails = int(fail_match.group(1)) + 1
        content = update_field(content, "Consecutive Failures", str(new_fails))

    # Record exception
    if args.error and args.step:
        error_row = f"| {now_str()} | {args.step} | {args.error} | Auto-recorded |"
        content = content.replace(
            "| - | - | No exceptions | - |",
            error_row,
        )
        # If there are already exception records, append new row
        if "No exceptions" not in content:
            # Append at the end of exception records table
            content = re.sub(
                r"(## Exception Records\n\n<!-- .+? -->\n\n\|.+?\|.+?\|.+?\|.+?\|\n\|[-| ]+\|\n)((?:\|.+?\|\n)*)",
                rf"\1\2{error_row}\n",
                content,
                flags=re.DOTALL,
            )

    write_file(hb_path, content)

    # Append to progress.md
    append_progress(workspace, "Failed", args.step or "N/A", args.error or "Unknown error")

    print(f"[HEARTBEAT] Status → failed | Error: {args.error} | Time: {now_str()}")


def cmd_mission_complete(workspace: Path, args):
    """Mark overall mission completion"""
    hb_path = workspace / "heartbeat.md"
    content = read_file(hb_path)

    content = update_field(content, "Current Status", "mission_complete")
    content = update_field(content, "Last Execution Result", "Mission Completed")

    write_file(hb_path, content)
    print(f"[HEARTBEAT] 🎉 Mission completed! Time: {now_str()}")


def cmd_blocked(workspace: Path, args):
    """Mark manual intervention required"""
    hb_path = workspace / "heartbeat.md"
    content = read_file(hb_path)

    content = update_field(content, "Current Status", "blocked")
    content = update_field(content, "Block Reason", args.reason or "Not specified")

    write_file(hb_path, content)
    print(f"[HEARTBEAT] 🚨 Task blocked! Reason: {args.reason} | Time: {now_str()}")


def append_progress(workspace: Path, result: str, step: str, note: str):
    """Append execution record to progress.md"""
    prog_path = workspace / "progress.md"
    if not prog_path.exists():
        print(f"[WARN] progress.md does not exist at {prog_path}, skipping progress record. Please confirm Agent has written it to the workspace: {workspace}")
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

    # Append after the comment "Subsequent execution records appended here"
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
    parser = argparse.ArgumentParser(description="Agent framework heartbeat update")
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
