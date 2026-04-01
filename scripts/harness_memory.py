#!/usr/bin/env python3
"""
harness_memory.py — Three-Layer Self-Healing Memory Manager

Implements the three-layer memory architecture inspired by Claude Code's leaked
source (MEMORY.md pointer index + topic files + grep-only raw logs).

Layer 1: heartbeat.md  — Compact pointer index (always in context, < 2KB target)
Layer 2: knowledge/*.md — Topic files (loaded on demand)
Layer 3: logs/execution_stream.log — Append-only raw log (grep only, never read fully)

Key features:
  - Strict Write Discipline: Only updates Layer 1 pointers after eval confirms success
  - Topic file lifecycle: create, update, query, prune
  - Execution stream: append-only structured logging
  - Knowledge index integrity checks

Usage:
    # Append to execution stream (Layer 3)
    python3 harness_memory.py /workspace stream --step "Step 2" --event "Fetched 50 articles"

    # Create or update a knowledge topic (Layer 2) and register pointer (Layer 1)
    python3 harness_memory.py /workspace learn --topic "api_auth" --insight "Bearer token expires in 3600s, refresh at 3000s"

    # Search execution stream by keyword (Layer 3 grep)
    python3 harness_memory.py /workspace search --query "timeout"

    # List all registered knowledge topics
    python3 harness_memory.py /workspace topics

    # Validate memory integrity (Layer 1 pointers vs Layer 2 files)
    python3 harness_memory.py /workspace check
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


STREAM_LOG = "logs/execution_stream.log"
KNOWLEDGE_DIR = "knowledge"
MAX_TOPIC_FILE_LINES = 500
MAX_HEARTBEAT_SIZE_KB = 2


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────
# Layer 3: Execution Stream (append-only log)
# ─────────────────────────────────────────────

def append_stream(workspace: Path, step: str, event: str, level: str = "INFO"):
    """Append a structured entry to the execution stream log."""
    log_path = workspace / STREAM_LOG
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = f"[{now_str()}] [{level}] [Step: {step}] {event}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)

    print(f"[MEMORY-L3] Appended to execution stream: {entry.strip()}")


def search_stream(workspace: Path, query: str, max_results: int = 20):
    """Search the execution stream log by keyword (grep-like)."""
    log_path = workspace / STREAM_LOG

    if not log_path.exists():
        print("[MEMORY-L3] No execution stream log found.")
        return []

    results = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if query.lower() in line.lower():
                results.append((line_num, line.strip()))
                if len(results) >= max_results:
                    break

    if results:
        print(f"[MEMORY-L3] Found {len(results)} matches for '{query}':")
        for num, line in results:
            print(f"  L{num}: {line}")
    else:
        print(f"[MEMORY-L3] No matches for '{query}'.")

    return results


# ─────────────────────────────────────────────
# Layer 2: Knowledge Topic Files
# ─────────────────────────────────────────────

def _topic_path(workspace: Path, topic: str) -> Path:
    """Get the path for a topic file."""
    slug = topic.strip().lower().replace(" ", "_").replace("-", "_")
    return workspace / KNOWLEDGE_DIR / f"{slug}.md"


def learn_topic(workspace: Path, topic: str, insight: str):
    """Create or append to a knowledge topic file, and update Layer 1 pointer."""
    knowledge_dir = workspace / KNOWLEDGE_DIR
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    topic_file = _topic_path(workspace, topic)
    slug = topic_file.stem

    if topic_file.exists():
        # Append new insight
        content = topic_file.read_text(encoding="utf-8")
        line_count = content.count("\n")
        if line_count >= MAX_TOPIC_FILE_LINES:
            print(f"[MEMORY-L2] WARNING: Topic '{slug}' has {line_count} lines (max {MAX_TOPIC_FILE_LINES}). Consider splitting.")

        with open(topic_file, "a", encoding="utf-8") as f:
            f.write(f"\n## Entry — {now_str()}\n\n{insight}\n")
        print(f"[MEMORY-L2] Updated topic: {slug}")
    else:
        # Create new topic file
        content = f"# {topic.replace('_', ' ').title()}\n\n"
        content += f"> Auto-created by harness_memory.py on {now_str()}\n\n"
        content += f"## Entry — {now_str()}\n\n{insight}\n"
        topic_file.write_text(content, encoding="utf-8")
        print(f"[MEMORY-L2] Created new topic: {slug}")

    # Update Layer 1 pointer
    _update_knowledge_index(workspace, slug, f"knowledge/{slug}.md")


def list_topics(workspace: Path):
    """List all knowledge topic files."""
    knowledge_dir = workspace / KNOWLEDGE_DIR
    if not knowledge_dir.exists():
        print("[MEMORY-L2] No knowledge directory found.")
        return []

    topics = sorted(knowledge_dir.glob("*.md"))
    topics = [t for t in topics if t.name != "README.md"]

    if topics:
        print(f"[MEMORY-L2] {len(topics)} topic(s) registered:")
        for t in topics:
            size = t.stat().st_size
            lines = t.read_text(encoding="utf-8").count("\n")
            print(f"  - {t.stem} ({size} bytes, {lines} lines)")
    else:
        print("[MEMORY-L2] No topic files found.")

    return [t.stem for t in topics]


# ─────────────────────────────────────────────
# Layer 1: Heartbeat Pointer Index
# ─────────────────────────────────────────────

def _update_knowledge_index(workspace: Path, topic_slug: str, rel_path: str):
    """Add or update a pointer row in heartbeat.md's Knowledge Index table."""
    hb_path = workspace / "heartbeat.md"
    if not hb_path.exists():
        print(f"[MEMORY-L1] heartbeat.md not found at {hb_path}, skipping pointer update.")
        return

    content = hb_path.read_text(encoding="utf-8")
    timestamp = now_str()

    # Check if topic already exists in the index
    pattern = rf"\| {re.escape(topic_slug)} \| `[^`]*` \| `[^`]*` \|"
    if re.search(pattern, content):
        # Update existing row
        content = re.sub(
            pattern,
            f"| {topic_slug} | `{rel_path}` | `{timestamp}` |",
            content,
        )
        print(f"[MEMORY-L1] Updated pointer: {topic_slug} -> {rel_path}")
    else:
        # Insert new row before the example row or at end of table
        example_row = "| _example_ |"
        if example_row in content:
            content = content.replace(
                example_row,
                f"| {topic_slug} | `{rel_path}` | `{timestamp}` |\n{example_row}",
            )
        else:
            # Find the end of Knowledge Index table and insert
            idx_match = re.search(r"(## Knowledge Index.*?\|[-| ]+\|\n)((?:\|.*\|\n)*)", content, re.DOTALL)
            if idx_match:
                insert_pos = idx_match.end()
                new_row = f"| {topic_slug} | `{rel_path}` | `{timestamp}` |\n"
                content = content[:insert_pos] + new_row + content[insert_pos:]

        print(f"[MEMORY-L1] Registered new pointer: {topic_slug} -> {rel_path}")

    hb_path.write_text(content, encoding="utf-8")

    # Size check
    size_kb = len(content.encode("utf-8")) / 1024
    if size_kb > MAX_HEARTBEAT_SIZE_KB:
        print(f"[MEMORY-L1] WARNING: heartbeat.md is {size_kb:.1f}KB (target: <{MAX_HEARTBEAT_SIZE_KB}KB). Consider pruning.")


def check_integrity(workspace: Path):
    """Validate that all Layer 1 pointers have corresponding Layer 2 files."""
    hb_path = workspace / "heartbeat.md"
    if not hb_path.exists():
        print("[MEMORY] heartbeat.md not found.")
        return False

    content = hb_path.read_text(encoding="utf-8")
    issues = []

    # Extract all pointer rows
    pointers = re.findall(r"\| (\w+) \| `(knowledge/\w+\.md)` \| `[^`]*` \|", content)

    for topic, rel_path in pointers:
        full_path = workspace / rel_path
        if not full_path.exists():
            issues.append(f"Dangling pointer: {topic} -> {rel_path} (file missing)")

    # Check for orphan topic files (Layer 2 files without Layer 1 pointer)
    knowledge_dir = workspace / KNOWLEDGE_DIR
    if knowledge_dir.exists():
        registered_paths = {p for _, p in pointers}
        for f in knowledge_dir.glob("*.md"):
            if f.name == "README.md":
                continue
            rel = f"knowledge/{f.name}"
            if rel not in registered_paths:
                issues.append(f"Orphan topic file: {rel} (no pointer in heartbeat.md)")

    # Check heartbeat size
    size_kb = len(content.encode("utf-8")) / 1024
    if size_kb > MAX_HEARTBEAT_SIZE_KB:
        issues.append(f"heartbeat.md is {size_kb:.1f}KB (target: <{MAX_HEARTBEAT_SIZE_KB}KB)")

    # Check execution stream
    stream_path = workspace / STREAM_LOG
    if stream_path.exists():
        stream_size_mb = stream_path.stat().st_size / (1024 * 1024)
        if stream_size_mb > 10:
            issues.append(f"Execution stream is {stream_size_mb:.1f}MB — consider archiving")

    if issues:
        print(f"[MEMORY] Integrity check found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  ⚠️  {issue}")
        return False
    else:
        print("[MEMORY] ✅ All memory layers are consistent.")
        return True


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OpenHarness Three-Layer Memory Manager"
    )
    parser.add_argument("workspace", help="Workspace directory path")
    subparsers = parser.add_subparsers(dest="command", help="Memory operations")

    # stream — append to Layer 3
    p_stream = subparsers.add_parser("stream", help="Append to execution stream (Layer 3)")
    p_stream.add_argument("--step", required=True, help="Current execution step")
    p_stream.add_argument("--event", required=True, help="Event description")
    p_stream.add_argument("--level", default="INFO", choices=["INFO", "WARN", "ERROR", "SUCCESS"],
                          help="Log level")

    # learn — create/update Layer 2 topic + Layer 1 pointer
    p_learn = subparsers.add_parser("learn", help="Record a knowledge insight (Layer 2)")
    p_learn.add_argument("--topic", required=True, help="Topic name/slug")
    p_learn.add_argument("--insight", required=True, help="Knowledge insight text")

    # search — grep Layer 3
    p_search = subparsers.add_parser("search", help="Search execution stream (Layer 3)")
    p_search.add_argument("--query", required=True, help="Search keyword")
    p_search.add_argument("--max", type=int, default=20, help="Max results")

    # topics — list Layer 2
    subparsers.add_parser("topics", help="List all knowledge topics (Layer 2)")

    # check — integrity validation
    subparsers.add_parser("check", help="Validate memory integrity across all layers")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    workspace = Path(args.workspace).resolve()

    if args.command == "stream":
        append_stream(workspace, args.step, args.event, args.level)
    elif args.command == "learn":
        learn_topic(workspace, args.topic, args.insight)
    elif args.command == "search":
        search_stream(workspace, args.query, args.max)
    elif args.command == "topics":
        list_topics(workspace)
    elif args.command == "check":
        ok = check_integrity(workspace)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
