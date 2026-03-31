#!/usr/bin/env python3
"""
memory_evolution.py — Memory Governance & Evolutionary Engine (Pillar 3)

This script transforms static execution logs into an evolutionary knowledge
base. After each successful execution cycle, it extracts "success genes"
(key insights, optimal parameters, effective strategies) and feeds them
back into the playbook for future runs.

Responsibilities:
1. Analyze high-scoring execution trajectories from progress.md
2. Extract reusable "genes" (insights) using LLM summarization
3. Store genes in a lightweight local database (SQLite + embeddings)
4. Auto-update playbook.md with evolved best practices

Usage:
    python3 memory_evolution.py /path/to/workspace [--score-threshold 0.9]

Design Principle (from Harness Engineering Pillar 3):
    "Competitive advantage is no longer the prompt — it is the trajectories
    captured by your harness. Every success and failure is training data
    for the next generation."

Integration:
    Called by harness_eval.py after a successful evaluation (score >= threshold).
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# --- Configuration ---
DEFAULT_SCORE_THRESHOLD = 0.9
GENE_DB_NAME = "memory_genes.db"
MAX_GENES_PER_PLAYBOOK = 10  # Prevent playbook bloat


class Gene:
    """Represents a reusable insight extracted from a successful execution."""

    def __init__(self, source_run: str, category: str, insight: str,
                 confidence: float, timestamp: str = ""):
        self.source_run = source_run
        self.category = category  # "strategy", "parameter", "tool_usage", "error_recovery"
        self.insight = insight
        self.confidence = confidence
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "source_run": self.source_run,
            "category": self.category,
            "insight": self.insight,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Gene":
        return cls(**data)

    def __repr__(self):
        return f"Gene({self.category}: {self.insight[:50]}... [{self.confidence:.2f}])"


class GeneDatabase:
    """Lightweight SQLite-based gene storage."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS genes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_run TEXT NOT NULL,
                    category TEXT NOT NULL,
                    insight TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    applied INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_category ON genes(category)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_confidence ON genes(confidence DESC)
            """)

    def save_gene(self, gene: Gene):
        """Save a gene to the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO genes (source_run, category, insight, confidence, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (gene.source_run, gene.category, gene.insight,
                 gene.confidence, gene.timestamp),
            )

    def get_top_genes(self, category: Optional[str] = None,
                      limit: int = MAX_GENES_PER_PLAYBOOK) -> List[Gene]:
        """Retrieve top genes by confidence, optionally filtered by category."""
        with sqlite3.connect(self.db_path) as conn:
            if category:
                rows = conn.execute(
                    "SELECT source_run, category, insight, confidence, timestamp "
                    "FROM genes WHERE category = ? ORDER BY confidence DESC LIMIT ?",
                    (category, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT source_run, category, insight, confidence, timestamp "
                    "FROM genes ORDER BY confidence DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [Gene(*row) for row in rows]

    def count(self) -> int:
        """Return total number of stored genes."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM genes").fetchone()[0]


def extract_successful_runs(progress_path: Path, score_threshold: float) -> List[Dict]:
    """
    Parse progress.md and extract runs that scored above the threshold.

    TODO: Currently uses regex heuristics. Future versions should parse
    structured evaluation scores from harness_eval.py output.
    """
    successful_runs = []

    if not progress_path.exists():
        return successful_runs

    content = progress_path.read_text(encoding="utf-8")

    # Find all Run records
    run_pattern = re.compile(
        r"### Run #(\d+) — (.+?)(?=\n### Run #|\n## Completion Condition Tracking|\Z)",
        re.DOTALL,
    )

    for match in run_pattern.finditer(content):
        run_id = match.group(1)
        run_content = match.group(0)

        # Check if the run was successful
        if re.search(r"Execution Result\s*\|\s*`?Success`?", run_content):
            successful_runs.append({
                "run_id": f"Run #{run_id}",
                "content": run_content,
                "score": 1.0,  # TODO: Parse actual evaluation score
            })

    return [r for r in successful_runs if r["score"] >= score_threshold]


def extract_genes_from_run(run_data: Dict) -> List[Gene]:
    """
    Extract reusable genes from a successful run's content.

    TODO: In production, this should use an LLM to summarize and extract
    key insights. Current implementation uses pattern matching as a
    placeholder.

    Future LLM integration example:
        gene = llm.summarize(
            prompt="Extract the single most reusable insight from this execution log.",
            content=run_data["content"],
        )
    """
    genes = []
    content = run_data["content"]
    run_id = run_data["run_id"]

    # Heuristic: Extract notes/remarks as potential genes
    notes_match = re.search(r"(?:Notes|Remarks)\s*\|\s*`(.+?)`", content)
    if notes_match:
        note = notes_match.group(1).strip()
        if len(note) > 10 and note not in ["N/A", "None", "-"]:
            genes.append(Gene(
                source_run=run_id,
                category="strategy",
                insight=note,
                confidence=run_data.get("score", 0.9),
            ))

    # Heuristic: Extract tool usage patterns
    tool_match = re.findall(r"(?:tool|using|via)[:\s]+`?(\w+)`?", content, re.IGNORECASE)
    if tool_match:
        unique_tools = list(set(t.lower() for t in tool_match))
        genes.append(Gene(
            source_run=run_id,
            category="tool_usage",
            insight=f"Effective tool combination: {', '.join(unique_tools)}",
            confidence=run_data.get("score", 0.9) * 0.8,
        ))

    return genes


def update_playbook_with_genes(playbook_path: Path, genes: List[Gene]):
    """
    Inject top genes into the playbook as a "Learned Best Practices" section.

    This section is appended at the end of the playbook and is clearly
    marked as auto-generated so the agent can distinguish it from
    human-authored instructions.
    """
    if not playbook_path.exists():
        print(f"⚠️ Playbook not found at {playbook_path}, skipping update.")
        return

    content = playbook_path.read_text(encoding="utf-8")

    # Remove existing auto-generated section if present
    marker_start = "<!-- AUTO-GENERATED: Learned Best Practices -->"
    marker_end = "<!-- END AUTO-GENERATED -->"
    pattern = re.compile(
        re.escape(marker_start) + r".*?" + re.escape(marker_end),
        re.DOTALL,
    )
    content = pattern.sub("", content).rstrip()

    if not genes:
        playbook_path.write_text(content + "\n", encoding="utf-8")
        return

    # Build the new section
    section_lines = [
        "",
        "",
        marker_start,
        "## Learned Best Practices (Auto-Evolved)",
        "",
        "> The following insights were automatically extracted from successful",
        "> execution trajectories by the Memory Evolution Engine.",
        "",
    ]

    for i, gene in enumerate(genes[:MAX_GENES_PER_PLAYBOOK], 1):
        section_lines.append(
            f"{i}. **[{gene.category}]** {gene.insight} "
            f"*(from {gene.source_run}, confidence: {gene.confidence:.2f})*"
        )

    section_lines.append("")
    section_lines.append(marker_end)
    section_lines.append("")

    content += "\n".join(section_lines)
    playbook_path.write_text(content, encoding="utf-8")
    print(f"✅ Updated playbook with {len(genes)} evolved best practices.")


def evolve(workspace: Path, score_threshold: float = DEFAULT_SCORE_THRESHOLD):
    """Main evolution pipeline."""
    progress_path = workspace / "progress.md"
    playbook_path = workspace / "playbook.md"
    db_path = workspace / GENE_DB_NAME

    print("=" * 60)
    print("  OpenHarness Memory Evolution Engine")
    print("=" * 60)

    # Step 1: Find successful runs
    successful_runs = extract_successful_runs(progress_path, score_threshold)
    print(f"\n📊 Found {len(successful_runs)} successful run(s) above threshold {score_threshold}")

    if not successful_runs:
        print("ℹ️ No high-scoring runs to learn from. Skipping evolution.")
        return

    # Step 2: Extract genes
    db = GeneDatabase(db_path)
    new_genes = []
    for run in successful_runs:
        genes = extract_genes_from_run(run)
        for gene in genes:
            db.save_gene(gene)
            new_genes.append(gene)
            print(f"  🧬 Extracted: {gene}")

    print(f"\n💾 Saved {len(new_genes)} new gene(s) to database. Total: {db.count()}")

    # Step 3: Update playbook with top genes
    top_genes = db.get_top_genes(limit=MAX_GENES_PER_PLAYBOOK)
    update_playbook_with_genes(playbook_path, top_genes)

    print("\n✅ Memory evolution complete.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="OpenHarness Memory Evolution Engine (Pillar 3)"
    )
    parser.add_argument("workspace", help="Workspace directory path")
    parser.add_argument(
        "--score-threshold", type=float, default=DEFAULT_SCORE_THRESHOLD,
        help=f"Minimum evaluation score to trigger gene extraction (default: {DEFAULT_SCORE_THRESHOLD})",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    evolve(workspace, args.score_threshold)


if __name__ == "__main__":
    main()
