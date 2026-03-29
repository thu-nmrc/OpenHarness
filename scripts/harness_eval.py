#!/usr/bin/env python3
"""
harness_eval.py — Agent framework external validation script

Functions:
1. Read validation criteria from eval_criteria.md
2. Perform basic validation on outputs in the workspace directory
3. Output validation report for Agent to decide next steps

This embodies the fifth load-bearing component of the Agent engineering: validation must be externalized as a loop.

Usage:
    python3 harness_eval.py /path/to/workspace

Notes:
    This script provides basic file existence and non-empty checks.
    More complex validation logic (such as content quality assessment) should be performed by Agent itself after reading eval_criteria.md.
    The main value of this script is to provide a standardized validation entry point and report format.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def check_output_dir(workspace: Path) -> list:
    """Check files in the output directory"""
    output_dir = workspace / "output"
    results = []

    if not output_dir.exists():
        results.append({
            "check": "Output directory exists",
            "passed": False,
            "detail": f"Directory does not exist: {output_dir}",
        })
        return results

    results.append({
        "check": "Output directory exists",
        "passed": True,
        "detail": f"Directory exists: {output_dir}",
    })

    files = list(output_dir.rglob("*"))
    files = [f for f in files if f.is_file()]

    results.append({
        "check": "Output directory is not empty",
        "passed": len(files) > 0,
        "detail": f"Contains {len(files)} files",
    })

    for f in files:
        size = f.stat().st_size
        results.append({
            "check": f"File is not empty: {f.name}",
            "passed": size > 0,
            "detail": f"Size: {size} bytes",
        })

    return results


def check_heartbeat_health(workspace: Path) -> list:
    """Check heartbeat status health"""
    import re

    hb_path = workspace / "heartbeat.md"
    results = []

    if not hb_path.exists():
        results.append({
            "check": "Heartbeat file exists",
            "passed": False,
            "detail": "heartbeat.md does not exist",
        })
        return results

    content = hb_path.read_text(encoding="utf-8")

    # Check consecutive failure count
    fail_match = re.search(r"\| Consecutive Failures \| `(\d+)`", content)
    if fail_match:
        fails = int(fail_match.group(1))
        results.append({
            "check": "Consecutive failures < 3",
            "passed": fails < 3,
            "detail": f"Current consecutive failures: {fails}",
        })

    # Check if status is abnormal
    status_match = re.search(r"\| Current Status \| `(.+?)`", content)
    if status_match:
        status = status_match.group(1)
        results.append({
            "check": "Status is not blocked",
            "passed": status != "blocked",
            "detail": f"Current status: {status}",
        })

    return results


def check_progress_health(workspace: Path) -> list:
    """Check progress log health"""
    import re

    prog_path = workspace / "progress.md"
    results = []

    if not prog_path.exists():
        results.append({
            "check": "Progress file exists",
            "passed": False,
            "detail": "progress.md does not exist",
        })
        return results

    content = prog_path.read_text(encoding="utf-8")
    run_count = len(re.findall(r"### Run #\d+", content))

    results.append({
        "check": "Execution records exist",
        "passed": run_count > 0,
        "detail": f"Total {run_count} execution records",
    })

    return results


def generate_report(workspace: Path) -> dict:
    """Generate complete validation report"""
    all_checks = []
    all_checks.extend(check_output_dir(workspace))
    all_checks.extend(check_heartbeat_health(workspace))
    all_checks.extend(check_progress_health(workspace))

    passed = sum(1 for c in all_checks if c["passed"])
    failed = sum(1 for c in all_checks if not c["passed"])
    total = len(all_checks)

    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "workspace": str(workspace),
        "summary": {
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed/total*100:.0f}%" if total > 0 else "N/A",
            "overall": "PASS" if failed == 0 else "FAIL",
        },
        "checks": all_checks,
    }

    return report


def print_report(report: dict):
    """Print formatted validation report"""
    print("=" * 60)
    print("  Agent Framework (Harness-24h) — Validation Report")
    print(f"  Time: {report['timestamp']}")
    print("=" * 60)

    s = report["summary"]
    print(f"\n📊 Overview: {s['passed']}/{s['total_checks']} passed ({s['pass_rate']})")
    print(f"🏷️  Result: {'✅ PASS' if s['overall'] == 'PASS' else '❌ FAIL'}")

    print("\nDetailed checks:")
    for check in report["checks"]:
        icon = "✅" if check["passed"] else "❌"
        print(f"  {icon} {check['check']}")
        print(f"     {check['detail']}")

    print("=" * 60)

    # Also save JSON format report
    report_path = Path(report["workspace"]) / "logs" / "eval_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 Report saved: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Agent framework external validation")
    parser.add_argument("workspace", help="Workspace directory path")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    report = generate_report(workspace)
    print_report(report)

    sys.exit(0 if report["summary"]["overall"] == "PASS" else 1)


if __name__ == "__main__":
    main()
