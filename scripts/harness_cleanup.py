#!/usr/bin/env python3
"""
harness_cleanup.py — Agent framework entropy control script (v2: AutoCompact + Stream Archive)

Functions:
1. Compress overly long progress.md (keep the most recent N entries, archive old records)
2. Archive oversized execution_stream.log (Layer 3) with rotation
3. Clean temporary files and expired logs
4. Check status consistency across all three memory layers
5. **NEW** AutoCompact with failure tracking — prevents runaway compaction loops

Usage:
    python3 harness_cleanup.py /path/to/workspace [--max-runs 50] [--max-stream-mb 10] [--dry-run]
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


STREAM_LOG = "logs/execution_stream.log"


def update_heartbeat_field(workspace: Path, field_name: str, new_value: str):
    """Update a field in heartbeat.md"""
    hb_path = workspace / "heartbeat.md"
    if not hb_path.exists():
        return
    content = hb_path.read_text(encoding="utf-8")
    pattern = rf"(\| {re.escape(field_name)} \| )`[^`]*`"
    replacement = rf"\1`{new_value}`"
    content = re.sub(pattern, replacement, content)
    hb_path.write_text(content, encoding="utf-8")


def compress_progress(workspace: Path, max_runs: int, dry_run: bool) -> dict:
    """Compress overly long progress.md"""
    prog_path = workspace / "progress.md"
    result = {"action": "compress_progress", "changes": []}

    if not prog_path.exists():
        result["changes"].append("progress.md does not exist, skipping")
        return result

    content = prog_path.read_text(encoding="utf-8")
    runs = list(re.finditer(
        r"### Run #(\d+) — (.+?)(?=\n### Run #|\n## Completion Condition Tracking|\Z)",
        content, re.DOTALL
    ))

    if len(runs) <= max_runs:
        result["changes"].append(f"Current {len(runs)} records do not exceed the limit {max_runs}, no compression needed")
        return result

    to_archive = runs[:-max_runs]
    to_keep = runs[-max_runs:]

    if dry_run:
        result["changes"].append(f"[DRY RUN] Will archive {len(to_archive)} old records, keep the most recent {len(to_keep)}")
        return result

    try:
        archive_dir = workspace / "logs" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_file = archive_dir / f"progress_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        archive_content = f"# Progress Archive\n\nArchive Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nArchived Records: {len(to_archive)}\n\n"
        for run in to_archive:
            archive_content += run.group(0) + "\n"

        archive_file.write_text(archive_content, encoding="utf-8")
        result["changes"].append(f"Archived {len(to_archive)} old records to {archive_file}")

        # Rebuild progress.md
        header_end = runs[0].start() if runs else len(content)
        header = content[:header_end]

        kept_content = ""
        for run in to_keep:
            kept_content += run.group(0) + "\n"

        tail_match = re.search(r"## Completion Condition Tracking", content)
        tail = content[tail_match.start():] if tail_match else ""

        new_content = header + "<!-- Subsequent execution records appended here -->\n\n" + kept_content + "\n" + tail
        prog_path.write_text(new_content, encoding="utf-8")
        result["changes"].append(f"progress.md compressed, kept the most recent {len(to_keep)} records")

        # Reset compaction failure counter on success
        update_heartbeat_field(workspace, "Compaction Failures", "0")

    except Exception as e:
        result["changes"].append(f"COMPACTION FAILED: {e}")
        # Increment compaction failure counter
        hb_path = workspace / "heartbeat.md"
        if hb_path.exists():
            hb_content = hb_path.read_text(encoding="utf-8")
            match = re.search(r"\| Compaction Failures \| `(\d+)`", hb_content)
            current = int(match.group(1)) if match else 0
            update_heartbeat_field(workspace, "Compaction Failures", str(current + 1))
            result["changes"].append(f"Compaction failure count incremented to {current + 1}")

    return result


def archive_stream(workspace: Path, max_stream_mb: float, dry_run: bool) -> dict:
    """Archive oversized execution stream log (Layer 3 rotation)."""
    result = {"action": "archive_execution_stream", "changes": []}
    stream_path = workspace / STREAM_LOG

    if not stream_path.exists():
        result["changes"].append("No execution stream log found")
        return result

    size_mb = stream_path.stat().st_size / (1024 * 1024)
    if size_mb <= max_stream_mb:
        result["changes"].append(f"Execution stream is {size_mb:.2f}MB (limit: {max_stream_mb}MB), no rotation needed")
        return result

    if dry_run:
        result["changes"].append(f"[DRY RUN] Will rotate execution stream ({size_mb:.2f}MB > {max_stream_mb}MB)")
        return result

    archive_dir = workspace / "logs" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"execution_stream_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    archive_path = archive_dir / archive_name

    shutil.move(str(stream_path), str(archive_path))
    # Create fresh empty log
    stream_path.write_text(f"# Execution Stream — Rotated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", encoding="utf-8")

    result["changes"].append(f"Rotated {size_mb:.2f}MB stream log to {archive_path}")
    return result


def clean_temp_files(workspace: Path, dry_run: bool) -> dict:
    """Clean temporary files"""
    result = {"action": "clean_temp_files", "changes": []}

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
    """Check status consistency across all three memory layers"""
    result = {"action": "check_consistency", "issues": []}

    hb_path = workspace / "heartbeat.md"
    prog_path = workspace / "progress.md"

    if not hb_path.exists() or not prog_path.exists():
        result["issues"].append("Core files missing, cannot check consistency")
        return result

    hb_content = hb_path.read_text(encoding="utf-8")
    prog_content = prog_path.read_text(encoding="utf-8")

    # Check execution count consistency
    hb_total = re.search(r"\| Total Executions \| `(\d+)`", hb_content)
    prog_runs = len(re.findall(r"### Run #\d+", prog_content))

    if hb_total:
        hb_count = int(hb_total.group(1))
        if hb_count != prog_runs:
            result["issues"].append(
                f"Execution count mismatch: heartbeat={hb_count}, progress={prog_runs}"
            )

    # Check heartbeat status
    status_match = re.search(r"\| Current Status \| `(.+?)`", hb_content)
    if status_match:
        status = status_match.group(1)
        if status == "running":
            result["issues"].append(
                "heartbeat status is still 'running', last execution may have been interrupted"
            )

    # Check heartbeat size (Layer 1 should be compact)
    hb_size_kb = len(hb_content.encode("utf-8")) / 1024
    if hb_size_kb > 2:
        result["issues"].append(
            f"heartbeat.md is {hb_size_kb:.1f}KB (target: <2KB) — consider pruning Knowledge Index"
        )

    # Check knowledge index integrity
    pointers = re.findall(r"\| (\w+) \| `(knowledge/\w+\.md)` \| `[^`]*` \|", hb_content)
    for topic, rel_path in pointers:
        if not (workspace / rel_path).exists():
            result["issues"].append(f"Dangling pointer: {topic} -> {rel_path}")

    # Check for orphan topic files
    knowledge_dir = workspace / "knowledge"
    if knowledge_dir.exists():
        registered_paths = {p for _, p in pointers}
        for f in knowledge_dir.glob("*.md"):
            if f.name == "README.md":
                continue
            rel = f"knowledge/{f.name}"
            if rel not in registered_paths:
                result["issues"].append(f"Orphan topic file: {rel} (no pointer in heartbeat.md)")

    if not result["issues"]:
        result["issues"].append("All consistency checks passed ✅")

    return result


def print_cleanup_report(results: list):
    """Print cleanup report"""
    print("=" * 60)
    print("  OpenHarness (v2) — Entropy Control Report")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    for r in results:
        print(f"\n🔧 {r['action']}:")
        items = r.get("changes", r.get("issues", []))
        for item in items:
            print(f"  - {item}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="OpenHarness entropy control (v2)")
    parser.add_argument("workspace", help="Workspace directory path")
    parser.add_argument("--max-runs", type=int, default=50, help="Maximum records to keep in progress.md")
    parser.add_argument("--max-stream-mb", type=float, default=10.0, help="Maximum execution stream size in MB before rotation")
    parser.add_argument("--dry-run", action="store_true", help="Only show actions, do not execute")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    results = []
    results.append(compress_progress(workspace, args.max_runs, args.dry_run))
    results.append(archive_stream(workspace, args.max_stream_mb, args.dry_run))
    results.append(clean_temp_files(workspace, args.dry_run))
    results.append(check_consistency(workspace))

    print_cleanup_report(results)


if __name__ == "__main__":
    main()
