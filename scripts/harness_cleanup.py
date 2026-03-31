#!/usr/bin/env python3
"""
harness_cleanup.py — Agent framework entropy control script

Functions:
1. Compress overly long progress.md (keep the most recent N entries, archive old records)
2. Clean temporary files and expired logs
3. Check status consistency
4. Output cleanup report

This represents the sixth load-bearing component of the Agent project: constraints, sandboxing, and entropy control must be mechanized.

Usage:
    python3 harness_cleanup.py /path/to/workspace [--max-runs 50] [--dry-run]
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def compress_progress(workspace: Path, max_runs: int, dry_run: bool) -> dict:
    """Compress overly long progress.md"""
    prog_path = workspace / "progress.md"
    result = {"action": "compress_progress", "changes": []}

    if not prog_path.exists():
        result["changes"].append("progress.md does not exist, skipping")
        return result

    content = prog_path.read_text(encoding="utf-8")

    # Find all Run records
    runs = list(re.finditer(r"### Run #(\d+) — (.+?)(?=\n### Run #|\n## Completion Condition Tracking|\Z)", content, re.DOTALL))

    if len(runs) <= max_runs:
        result["changes"].append(f"Current {len(runs)} records do not exceed the limit {max_runs}, no compression needed")
        return result

    # Old records to archive
    to_archive = runs[:-max_runs]
    to_keep = runs[-max_runs:]

    if dry_run:
        result["changes"].append(f"[DRY RUN] Will archive {len(to_archive)} old records, keep the most recent {len(to_keep)}")
        return result

    # Archive old records
    archive_dir = workspace / "logs" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_file = archive_dir / f"progress_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    archive_content = f"# Progress Archive\n\nArchive Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nArchived Records: {len(to_archive)}\n\n"
    for run in to_archive:
        archive_content += run.group(0) + "\n"

    archive_file.write_text(archive_content, encoding="utf-8")
    result["changes"].append(f"Archived {len(to_archive)} old records to {archive_file}")

    # Remove old records from progress.md
    # Keep header (before first Run) and tail (after Completion Criteria Tracking)
    header_end = runs[0].start() if runs else len(content)
    header = content[:header_end]

    kept_content = ""
    for run in to_keep:
        kept_content += run.group(0) + "\n"

    # Find tail (Completion Condition Tracking and after)
    tail_match = re.search(r"## Completion Condition Tracking", content)
    tail = content[tail_match.start():] if tail_match else ""

    new_content = header + "<!-- Subsequent execution records appended here -->\n\n" + kept_content + "\n" + tail
    prog_path.write_text(new_content, encoding="utf-8")
    result["changes"].append(f"progress.md compressed, kept the most recent {len(to_keep)} records")

    return result


def clean_temp_files(workspace: Path, dry_run: bool) -> dict:
    """Clean temporary files"""
    result = {"action": "clean_temp_files", "changes": []}

    # Clean common temporary files
    patterns = ["*.tmp", "*.bak", "*.swp", ".DS_Store", "Thumbs.db"]
    cleaned = 0

    for pattern in patterns:
        for f in workspace.rglob(pattern):
            if dry_run:
                result["changes"].append(f"[DRY RUN] Will delete: {f}")
            else:
                f.unlink()
                result["changes"].append(f"Deleted: {f}")
            cleaned += 1

    if cleaned == 0:
        result["changes"].append("No temporary files to clean")

    return result


def check_consistency(workspace: Path) -> dict:
    """Check status consistency"""
    result = {"action": "check_consistency", "issues": []}

    hb_path = workspace / "heartbeat.md"
    prog_path = workspace / "progress.md"

    if not hb_path.exists() or not prog_path.exists():
        result["issues"].append("Core files missing, cannot check consistency")
        return result

    hb_content = hb_path.read_text(encoding="utf-8")
    prog_content = prog_path.read_text(encoding="utf-8")

    # Check if total execution count in heartbeat matches record count in progress
    hb_total = re.search(r"\| Total Executions \| `(\d+)`", hb_content)
    prog_runs = len(re.findall(r"### Run #\d+", prog_content))

    if hb_total:
        hb_count = int(hb_total.group(1))
        if hb_count != prog_runs:
            result["issues"].append(
                f"Execution count mismatch: heartbeat={hb_count}, progress={prog_runs}"
            )

    # Check if heartbeat status is reasonable
    status_match = re.search(r"\| Current Status \| `(.+?)`", hb_content)
    if status_match:
        status = status_match.group(1)
        if status == "running":
            result["issues"].append(
                "heartbeat status is still running, last execution may have been interrupted abnormally"
            )

    if not result["issues"]:
        result["issues"].append("Status consistency check passed")

    return result


def print_cleanup_report(results: list):
    """Print cleanup report"""
    print("=" * 60)
    print("  Agent Framework (Harness-24h) — Entropy Control Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    for r in results:
        print(f"\n🔧 {r['action']}:")
        items = r.get("changes", r.get("issues", []))
        for item in items:
            print(f"  - {item}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Agent framework entropy control")
    parser.add_argument("workspace", help="Workspace directory path")
    parser.add_argument("--max-runs", type=int, default=50, help="Maximum number of records to keep in progress.md")
    parser.add_argument("--dry-run", action="store_true", help="Only show actions to be performed, do not execute")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    results = []
    results.append(compress_progress(workspace, args.max_runs, args.dry_run))
    results.append(clean_temp_files(workspace, args.dry_run))
    results.append(check_consistency(workspace))

    print_cleanup_report(results)


if __name__ == "__main__":
    main()
