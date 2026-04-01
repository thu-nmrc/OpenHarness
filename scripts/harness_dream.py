#!/usr/bin/env python3
"""
harness_dream.py — KAIROS Dream Mode: Offline Memory Consolidation Engine

Inspired by Claude Code's leaked KAIROS daemon (referenced 150+ times in source),
this script performs "memory distillation" during idle periods.

Unlike memory_evolution.py (which extracts genes from progress.md), harness_dream.py
operates on the THREE-LAYER memory architecture:

  1. Reads Layer 3 (execution_stream.log) to find patterns across all recent executions
  2. Consolidates fragmented Layer 2 (knowledge/*.md) topic files
  3. Prunes stale Layer 1 (heartbeat.md) pointers
  4. Auto-updates playbook.md with distilled best practices

Design Principle (from KAIROS):
    "The agent should consolidate its memories during idle time,
     not during active task execution."

Usage:
    # Full dream cycle (recommended: run via cron during off-hours)
    python3 harness_dream.py /path/to/workspace

    # Dry run — show what would be consolidated without making changes
    python3 harness_dream.py /path/to/workspace --dry-run

    # Only consolidate knowledge topics (skip playbook update)
    python3 harness_dream.py /path/to/workspace --skip-playbook

    # Set minimum entries before a topic is considered for consolidation
    python3 harness_dream.py /path/to/workspace --min-entries 3

Integration:
    Add to cron_config.md as a secondary schedule, or call from harness_eval.py
    after a successful evaluation when the agent is about to go idle.
"""

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict


STREAM_LOG = "logs/execution_stream.log"
KNOWLEDGE_DIR = "knowledge"
DREAM_LOG = "logs/dream_journal.md"

# Patterns to extract from execution stream
ERROR_PATTERN = re.compile(r"\[ERROR\] \[Step: (.+?)\] (.+)")
SUCCESS_PATTERN = re.compile(r"\[SUCCESS\] \[Step: (.+?)\] (.+)")
WARN_PATTERN = re.compile(r"\[WARN\] \[Step: (.+?)\] (.+)")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────
# Phase 1: Analyze Execution Stream (Layer 3)
# ─────────────────────────────────────────────

def analyze_stream(workspace: Path, lookback_hours: int = 24) -> dict:
    """Analyze recent execution stream entries for patterns."""
    stream_path = workspace / STREAM_LOG
    analysis = {
        "total_entries": 0,
        "errors": [],
        "successes": [],
        "warnings": [],
        "error_steps": Counter(),
        "success_steps": Counter(),
        "recurring_errors": [],
        "effective_strategies": [],
    }

    if not stream_path.exists():
        return analysis

    cutoff = datetime.now() - timedelta(hours=lookback_hours)

    with open(stream_path, "r", encoding="utf-8") as f:
        for line in f:
            analysis["total_entries"] += 1

            # Parse timestamp
            ts_match = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", line)
            if ts_match:
                try:
                    entry_time = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S")
                    if entry_time < cutoff:
                        continue
                except ValueError:
                    pass

            # Categorize
            err = ERROR_PATTERN.search(line)
            if err:
                analysis["errors"].append({"step": err.group(1), "message": err.group(2)})
                analysis["error_steps"][err.group(1)] += 1

            suc = SUCCESS_PATTERN.search(line)
            if suc:
                analysis["successes"].append({"step": suc.group(1), "message": suc.group(2)})
                analysis["success_steps"][suc.group(1)] += 1

            warn = WARN_PATTERN.search(line)
            if warn:
                analysis["warnings"].append({"step": warn.group(1), "message": warn.group(2)})

    # Identify recurring errors (same step failing 3+ times)
    for step, count in analysis["error_steps"].items():
        if count >= 3:
            messages = [e["message"] for e in analysis["errors"] if e["step"] == step]
            analysis["recurring_errors"].append({
                "step": step,
                "count": count,
                "sample_message": messages[-1] if messages else "Unknown",
            })

    # Identify effective strategies (steps that succeeded after previous failures)
    failed_steps = set(analysis["error_steps"].keys())
    for step in analysis["success_steps"]:
        if step in failed_steps:
            messages = [s["message"] for s in analysis["successes"] if s["step"] == step]
            analysis["effective_strategies"].append({
                "step": step,
                "recovery_message": messages[-1] if messages else "Unknown",
            })

    return analysis


# ─────────────────────────────────────────────
# Phase 2: Consolidate Knowledge Topics (Layer 2)
# ─────────────────────────────────────────────

def consolidate_topics(workspace: Path, min_entries: int = 3, dry_run: bool = False) -> list:
    """Merge fragmented entries within each topic file into a consolidated summary."""
    knowledge_dir = workspace / KNOWLEDGE_DIR
    actions = []

    if not knowledge_dir.exists():
        return actions

    for topic_file in sorted(knowledge_dir.glob("*.md")):
        if topic_file.name == "README.md":
            continue

        content = topic_file.read_text(encoding="utf-8")
        entries = re.findall(r"## Entry — .+?\n\n(.+?)(?=\n## Entry —|\Z)", content, re.DOTALL)

        if len(entries) < min_entries:
            actions.append(f"SKIP {topic_file.stem}: only {len(entries)} entries (min: {min_entries})")
            continue

        if dry_run:
            actions.append(f"[DRY RUN] Would consolidate {topic_file.stem}: {len(entries)} entries")
            continue

        # Deduplicate and merge entries
        unique_insights = []
        seen = set()
        for entry in entries:
            normalized = entry.strip().lower()
            # Simple dedup: skip if >80% similar to an existing entry
            if normalized not in seen:
                seen.add(normalized)
                unique_insights.append(entry.strip())

        # Rewrite topic file with consolidated content
        topic_name = topic_file.stem.replace("_", " ").title()
        new_content = f"# {topic_name}\n\n"
        new_content += f"> Consolidated by harness_dream.py on {now_str()}\n"
        new_content += f"> Original entries: {len(entries)} → Consolidated: {len(unique_insights)}\n\n"

        new_content += "## Consolidated Knowledge\n\n"
        for i, insight in enumerate(unique_insights, 1):
            new_content += f"### Insight {i}\n\n{insight}\n\n"

        topic_file.write_text(new_content, encoding="utf-8")
        actions.append(f"CONSOLIDATED {topic_file.stem}: {len(entries)} → {len(unique_insights)} entries")

    return actions


# ─────────────────────────────────────────────
# Phase 3: Prune Stale Pointers (Layer 1)
# ─────────────────────────────────────────────

def prune_stale_pointers(workspace: Path, dry_run: bool = False) -> list:
    """Remove Layer 1 pointers whose Layer 2 files no longer exist."""
    hb_path = workspace / "heartbeat.md"
    actions = []

    if not hb_path.exists():
        return actions

    content = hb_path.read_text(encoding="utf-8")
    pointers = re.findall(r"\| (\w+) \| `(knowledge/\w+\.md)` \| `[^`]*` \|", content)

    stale = []
    for topic, rel_path in pointers:
        if not (workspace / rel_path).exists():
            stale.append((topic, rel_path))

    if not stale:
        actions.append("No stale pointers found")
        return actions

    if dry_run:
        for topic, path in stale:
            actions.append(f"[DRY RUN] Would remove stale pointer: {topic} -> {path}")
        return actions

    for topic, rel_path in stale:
        pattern = rf"\| {re.escape(topic)} \| `{re.escape(rel_path)}` \| `[^`]*` \|\n?"
        content = re.sub(pattern, "", content)
        actions.append(f"PRUNED stale pointer: {topic} -> {rel_path}")

    hb_path.write_text(content, encoding="utf-8")
    return actions


# ─────────────────────────────────────────────
# Phase 4: Update Playbook with Distilled Insights
# ─────────────────────────────────────────────

def update_playbook(workspace: Path, analysis: dict, dry_run: bool = False) -> list:
    """Inject distilled insights from dream analysis into playbook.md."""
    playbook_path = workspace / "playbook.md"
    actions = []

    if not playbook_path.exists():
        actions.append("playbook.md not found, skipping")
        return actions

    insights = []

    # Add recurring error warnings
    for err in analysis.get("recurring_errors", []):
        insights.append(
            f"**[RECURRING ERROR]** Step `{err['step']}` has failed {err['count']} times. "
            f"Last error: {err['sample_message'][:100]}"
        )

    # Add effective recovery strategies
    for strat in analysis.get("effective_strategies", []):
        insights.append(
            f"**[RECOVERY STRATEGY]** Step `{strat['step']}` recovered after failures. "
            f"Successful approach: {strat['recovery_message'][:100]}"
        )

    if not insights:
        actions.append("No new insights to inject into playbook")
        return actions

    if dry_run:
        for ins in insights:
            actions.append(f"[DRY RUN] Would add: {ins[:80]}...")
        return actions

    content = playbook_path.read_text(encoding="utf-8")

    # Remove existing dream-generated section
    marker_start = "<!-- AUTO-GENERATED: Dream Insights -->"
    marker_end = "<!-- END Dream Insights -->"
    pattern = re.compile(
        re.escape(marker_start) + r".*?" + re.escape(marker_end),
        re.DOTALL,
    )
    content = pattern.sub("", content).rstrip()

    # Build new section
    section = f"\n\n{marker_start}\n"
    section += "## Dream Insights (Auto-Distilled)\n\n"
    section += f"> Distilled by `harness_dream.py` on {now_str()}\n"
    section += "> These insights are automatically extracted from execution patterns.\n\n"

    for i, insight in enumerate(insights, 1):
        section += f"{i}. {insight}\n"

    section += f"\n{marker_end}\n"

    content += section
    playbook_path.write_text(content, encoding="utf-8")
    actions.append(f"Injected {len(insights)} dream insights into playbook.md")

    return actions


# ─────────────────────────────────────────────
# Dream Journal
# ─────────────────────────────────────────────

def write_dream_journal(workspace: Path, analysis: dict, topic_actions: list,
                        pointer_actions: list, playbook_actions: list):
    """Write a dream journal entry for auditability."""
    journal_path = workspace / DREAM_LOG
    journal_path.parent.mkdir(parents=True, exist_ok=True)

    entry = f"\n## Dream Cycle — {now_str()}\n\n"
    entry += f"### Stream Analysis\n"
    entry += f"- Total entries scanned: {analysis['total_entries']}\n"
    entry += f"- Errors (24h): {len(analysis['errors'])}\n"
    entry += f"- Successes (24h): {len(analysis['successes'])}\n"
    entry += f"- Warnings (24h): {len(analysis['warnings'])}\n"
    entry += f"- Recurring errors: {len(analysis['recurring_errors'])}\n"
    entry += f"- Recovery strategies found: {len(analysis['effective_strategies'])}\n\n"

    entry += f"### Topic Consolidation\n"
    for a in topic_actions:
        entry += f"- {a}\n"

    entry += f"\n### Pointer Pruning\n"
    for a in pointer_actions:
        entry += f"- {a}\n"

    entry += f"\n### Playbook Updates\n"
    for a in playbook_actions:
        entry += f"- {a}\n"

    entry += "\n---\n"

    with open(journal_path, "a", encoding="utf-8") as f:
        if f.tell() == 0:
            f.write("# Dream Journal\n\n> Auto-generated by harness_dream.py (KAIROS mode)\n\n---\n")
        f.write(entry)


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OpenHarness KAIROS Dream Mode — Offline Memory Consolidation"
    )
    parser.add_argument("workspace", help="Workspace directory path")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--skip-playbook", action="store_true", help="Skip playbook update")
    parser.add_argument("--min-entries", type=int, default=3, help="Min entries before topic consolidation")
    parser.add_argument("--lookback-hours", type=int, default=24, help="Hours of stream history to analyze")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    print("=" * 60)
    print("  OpenHarness KAIROS Dream Mode")
    print(f"  Time: {now_str()}")
    print("  \"Consolidating memories while the agent sleeps...\"")
    print("=" * 60)

    # Phase 1: Analyze execution stream
    print("\n🔍 Phase 1: Analyzing execution stream (Layer 3)...")
    analysis = analyze_stream(workspace, args.lookback_hours)
    print(f"   Scanned {analysis['total_entries']} entries")
    print(f"   Found {len(analysis['recurring_errors'])} recurring error(s)")
    print(f"   Found {len(analysis['effective_strategies'])} recovery strateg(ies)")

    # Phase 2: Consolidate knowledge topics
    print("\n📚 Phase 2: Consolidating knowledge topics (Layer 2)...")
    topic_actions = consolidate_topics(workspace, args.min_entries, args.dry_run)
    for a in topic_actions:
        print(f"   {a}")

    # Phase 3: Prune stale pointers
    print("\n🔗 Phase 3: Pruning stale pointers (Layer 1)...")
    pointer_actions = prune_stale_pointers(workspace, args.dry_run)
    for a in pointer_actions:
        print(f"   {a}")

    # Phase 4: Update playbook
    playbook_actions = []
    if not args.skip_playbook:
        print("\n📝 Phase 4: Updating playbook with distilled insights...")
        playbook_actions = update_playbook(workspace, analysis, args.dry_run)
        for a in playbook_actions:
            print(f"   {a}")
    else:
        print("\n📝 Phase 4: Skipped (--skip-playbook)")

    # Write dream journal
    if not args.dry_run:
        write_dream_journal(workspace, analysis, topic_actions, pointer_actions, playbook_actions)
        print(f"\n📓 Dream journal updated: {workspace / DREAM_LOG}")

    print("\n" + "=" * 60)
    print("  💤 Dream cycle complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
