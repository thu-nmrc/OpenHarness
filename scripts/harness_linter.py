#!/usr/bin/env python3
"""
harness_linter.py — Architecture Constraint Enforcement (Pillar 2)

This script enforces mechanical architecture constraints on the agent's
workspace before execution begins. It is called automatically by
harness_boot.py at every boot cycle.

Responsibilities:
1. Validate playbook.md for directional dependency violations
2. Enforce tool whitelist limits (default max: 10 core tools)
3. Check mission.md for ambiguous or non-machine-checkable criteria
4. Report violations as blocking errors or warnings

Usage:
    python3 harness_linter.py /path/to/workspace [--strict] [--max-tools 10]

Design Principle (from Harness Engineering Pillar 2):
    "Trust requires bounding the solution space. The fewer tools, the
    higher the pass rate. Constraints are not limitations — they are
    the foundation of reliability."
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


# --- Architecture Layer Definitions ---
# Layers are ordered from lowest to highest. Higher layers may depend on
# lower layers, but NEVER the reverse.
ARCHITECTURE_LAYERS = [
    "types",      # Data types and schemas
    "config",     # Configuration and environment
    "service",    # Business logic and data processing
    "ui",         # User-facing output (reports, dashboards, emails)
]

# Default core tool whitelist. Playbooks should not exceed this set
# unless explicitly justified in mission.md.
DEFAULT_TOOL_WHITELIST = [
    "browser",
    "shell",
    "file_read",
    "file_write",
    "search",
    "schedule",
    "python",
    "api_call",
    "screenshot",
    "git",
]


class LintViolation:
    """Represents a single lint violation."""

    def __init__(self, severity: str, rule: str, message: str, file: str = "", line: int = 0):
        self.severity = severity  # "error" or "warning"
        self.rule = rule
        self.message = message
        self.file = file
        self.line = line

    def __str__(self):
        loc = f"{self.file}:{self.line}" if self.line else self.file
        icon = "❌" if self.severity == "error" else "⚠️"
        return f"{icon} [{self.severity.upper()}] {self.rule} — {self.message} ({loc})"


def check_layer_dependencies(playbook_path: Path) -> List[LintViolation]:
    """
    Check that the playbook respects directional layer dependencies.

    For example, if a step references "UI" operations (generating reports,
    sending emails) before "Service" operations (data collection, processing),
    it is a violation.

    TODO: Implement full AST-like parsing of playbook steps.
    Current implementation uses keyword heuristics.
    """
    violations = []

    if not playbook_path.exists():
        return violations

    content = playbook_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Track the highest layer seen so far
    highest_layer_seen = -1
    highest_layer_name = ""

    ui_keywords = ["report", "email", "dashboard", "notification", "send to", "publish"]
    service_keywords = ["collect", "process", "analyze", "compute", "fetch", "scrape", "parse"]

    for i, line in enumerate(lines, 1):
        lower = line.lower()

        # Detect service-layer operations
        if any(kw in lower for kw in service_keywords):
            layer_idx = ARCHITECTURE_LAYERS.index("service")
            if highest_layer_seen > layer_idx:
                violations.append(LintViolation(
                    severity="warning",
                    rule="layer-order",
                    message=f"Service-layer operation found after {highest_layer_name}-layer. "
                            f"Consider reordering steps to respect Types→Config→Service→UI flow.",
                    file="playbook.md",
                    line=i,
                ))

        # Detect UI-layer operations
        if any(kw in lower for kw in ui_keywords):
            layer_idx = ARCHITECTURE_LAYERS.index("ui")
            if highest_layer_seen < layer_idx:
                highest_layer_seen = layer_idx
                highest_layer_name = "ui"

    return violations


def check_tool_whitelist(playbook_path: Path, max_tools: int) -> List[LintViolation]:
    """
    Check that the playbook does not reference more tools than allowed.

    TODO: Parse tool references from structured playbook format.
    Current implementation uses regex heuristics.
    """
    violations = []

    if not playbook_path.exists():
        return violations

    content = playbook_path.read_text(encoding="utf-8")

    # Extract tool references (heuristic: look for tool names in backticks or after "Tool:" labels)
    tool_pattern = re.findall(r"(?:tool|using|via)[:\s]+`?(\w+)`?", content, re.IGNORECASE)
    unique_tools = set(t.lower() for t in tool_pattern)

    if len(unique_tools) > max_tools:
        violations.append(LintViolation(
            severity="warning",
            rule="tool-count",
            message=f"Playbook references {len(unique_tools)} unique tools (limit: {max_tools}). "
                    f"Fewer tools = higher reliability. Consider trimming: {unique_tools}",
            file="playbook.md",
        ))

    return violations


def check_mission_criteria(mission_path: Path) -> List[LintViolation]:
    """
    Check that mission.md completion criteria are machine-verifiable.

    TODO: Implement NLP-based ambiguity detection.
    Current implementation uses keyword heuristics for subjective language.
    """
    violations = []

    if not mission_path.exists():
        violations.append(LintViolation(
            severity="error",
            rule="mission-exists",
            message="mission.md does not exist. Cannot proceed without a task contract.",
            file="mission.md",
        ))
        return violations

    content = mission_path.read_text(encoding="utf-8")

    # Check for subjective/ambiguous language in completion criteria
    subjective_keywords = [
        "looks good", "seems correct", "reasonable", "appropriate",
        "high quality", "well written", "comprehensive enough",
    ]

    lines = content.split("\n")
    in_criteria_section = False
    for i, line in enumerate(lines, 1):
        if "Done Definition" in line or "Completion" in line:
            in_criteria_section = True
        if in_criteria_section:
            lower = line.lower()
            for kw in subjective_keywords:
                if kw in lower:
                    violations.append(LintViolation(
                        severity="error",
                        rule="subjective-criteria",
                        message=f"Subjective language detected: '{kw}'. "
                                f"Completion criteria must be machine-verifiable.",
                        file="mission.md",
                        line=i,
                    ))

    return violations


def run_lint(workspace: Path, strict: bool = False, max_tools: int = 10) -> Tuple[List[LintViolation], bool]:
    """Run all lint checks and return violations and pass/fail status."""
    all_violations = []

    playbook_path = workspace / "playbook.md"
    mission_path = workspace / "mission.md"

    all_violations.extend(check_layer_dependencies(playbook_path))
    all_violations.extend(check_tool_whitelist(playbook_path, max_tools))
    all_violations.extend(check_mission_criteria(mission_path))

    errors = [v for v in all_violations if v.severity == "error"]
    warnings = [v for v in all_violations if v.severity == "warning"]

    passed = len(errors) == 0 and (not strict or len(warnings) == 0)

    return all_violations, passed


def print_report(violations: List[LintViolation], passed: bool):
    """Print formatted lint report."""
    print("=" * 60)
    print("  OpenHarness Linter — Architecture Constraint Report")
    print("=" * 60)

    if not violations:
        print("\n✅ All checks passed. No violations found.")
    else:
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]
        print(f"\n📊 Found {len(errors)} error(s) and {len(warnings)} warning(s):\n")
        for v in violations:
            print(f"  {v}")

    print(f"\n{'✅ PASSED' if passed else '❌ FAILED'}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="OpenHarness Architecture Constraint Linter")
    parser.add_argument("workspace", help="Workspace directory path")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--max-tools", type=int, default=10, help="Maximum allowed tools in playbook")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    violations, passed = run_lint(workspace, args.strict, args.max_tools)
    print_report(violations, passed)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
