#!/usr/bin/env python3
"""
harness_setup_cron.py — Agent framework scheduled task configuration script

Functions:
1. Read scheduling configuration from cron_config.md
2. Generate call parameters for the Agent schedule tool
3. Output cron configuration information that can be used directly

Usage:
    python3 harness_setup_cron.py /path/to/workspace

Note:
    This script does not directly set cron (because Agent's schedule requires tool invocation).
    Its role is to parse cron_config.md and output formatted configuration information,
    for Agent to use when calling the schedule tool in the SKILL.md workflow.
"""

import argparse
import re
import sys
from pathlib import Path


def parse_cron_config(workspace: Path) -> dict:
    """Parse configuration in cron_config.md"""
    config_path = workspace / "cron_config.md"

    if not config_path.exists():
        print(f"[ERROR] Configuration file does not exist: {config_path}")
        sys.exit(1)

    content = config_path.read_text(encoding="utf-8")

    config = {}

    # Parse main task scheduling table
    fields = {
        "Schedule Type": "schedule_type",
        "Cron Expression": "cron_expression",
        "cron Expression": "cron_expression",
        "Or: Interval Seconds": "interval_seconds",
        "Repeat": "repeat",
        "Expire": "expire",
        "Expiration Time": "expire",
        "Timezone": "timezone",
        # Legacy Chinese field names for backward compatibility
        "调度类型": "schedule_type",
        "cron表达式": "cron_expression",
        "或：间隔秒数": "interval_seconds",
        "是否重复": "repeat",
        "过期时间": "expire",
        "时区": "timezone",
    }

    for cn_name, en_name in fields.items():
        match = re.search(rf"\| {re.escape(cn_name)} \| `(.+?)`", content)
        if match:
            value = match.group(1).strip()
            if value and not value.startswith("["):
                config[en_name] = value

    # Parse Prompt template
    prompt_match = re.search(r"```\n(Read the following files.+?)```", content, re.DOTALL)
    if not prompt_match:
        # Legacy Chinese prompt pattern for backward compatibility
        prompt_match = re.search(r"```\n(读取以下文件.+?)```", content, re.DOTALL)
    if prompt_match:
        config["prompt"] = prompt_match.group(1).strip()

    return config


def read_mission_name(workspace: Path) -> str:
    """Read mission name"""
    mission_path = workspace / "mission.md"
    if not mission_path.exists():
        return "harness-task"
    content = mission_path.read_text(encoding="utf-8")
    match = re.search(r"\*\*Name\*\*[：:] ?`(.+?)`", content)
    if not match:
        # Legacy Chinese field name for backward compatibility
        match = re.search(r"\*\*名称\*\*[：:] ?`(.+?)`", content)
    return match.group(1) if match else "harness-task"


def generate_schedule_params(workspace: Path) -> dict:
    """Generate parameters for Agent schedule tool"""
    config = parse_cron_config(workspace)
    mission_name = read_mission_name(workspace)

    params = {
        "name": mission_name.replace(" ", "-").lower(),
        "type": config.get("schedule_type", "cron"),
        "repeat": config.get("repeat", "true").lower() == "true",
    }

    if params["type"] == "cron":
        params["cron"] = config.get("cron_expression", "0 0 */2 * * *")
    else:
        params["interval"] = int(config.get("interval_seconds", "7200"))

    if config.get("expire") and not config["expire"].startswith("["):
        params["expire"] = config["expire"]

    # Construct prompt
    if config.get("prompt"):
        params["prompt"] = config["prompt"]
    else:
        params["prompt"] = f"""Read the following files and execute tasks according to the Agent framework:

1. Read {workspace}/mission.md — Understand task objectives
2. Read {workspace}/heartbeat.md — Resume last state
3. Read {workspace}/progress.md — Understand historical progress
4. Read {workspace}/playbook.md — Obtain execution steps
5. Continue execution from the breakpoint recorded in heartbeat
6. After completion:
   a. Read {workspace}/eval_criteria.md for validation
   b. Update {workspace}/heartbeat.md
   c. Append records to {workspace}/progress.md
7. If all completion conditions are met, set heartbeat status to mission_complete"""

    # Construct playbook (best practices)
    params["playbook"] = f"""Agent framework execution best practices:
1. Run python3 {Path(__file__).parent}/harness_boot.py {workspace} to check status at startup
2. Call python3 {Path(__file__).parent}/harness_heartbeat.py {workspace} start to mark start
3. Continue execution from breakpoint according to playbook.md steps
4. After completion, call python3 {Path(__file__).parent}/harness_heartbeat.py {workspace} done --step "StepX" --summary "Summary"
5. On failure, call python3 {Path(__file__).parent}/harness_heartbeat.py {workspace} fail --step "StepX" --error "Error description"
6. Run python3 {Path(__file__).parent}/harness_eval.py {workspace} for validation
7. Periodically run python3 {Path(__file__).parent}/harness_cleanup.py {workspace} for entropy control"""

    return params


def main():
    parser = argparse.ArgumentParser(description="Agent framework scheduled task configuration")
    parser.add_argument("workspace", help="Workspace directory path")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    params = generate_schedule_params(workspace)

    print("=" * 60)
    print("  Agent Framework (Harness-24h) — Scheduled Task Configuration")
    print("=" * 60)

    print("\n📋 Agent Schedule tool parameters:")
    print(f"  name:    {params['name']}")
    print(f"  type:    {params['type']}")
    print(f"  repeat:  {params['repeat']}")

    if params["type"] == "cron":
        print(f"  cron:    {params['cron']}")
    else:
        print(f"  interval: {params['interval']}s")

    if params.get("expire"):
        print(f"  expire:  {params['expire']}")

    print(f"\n📝 Prompt (first 200 characters):")
    print(f"  {params['prompt'][:200]}...")

    print(f"\n📖 Playbook (first 200 characters):")
    print(f"  {params['playbook'][:200]}...")

    print("\n" + "=" * 60)
    print("Please use the schedule tool in Agent with the above parameters to set up scheduled tasks.")
    print("=" * 60)


if __name__ == "__main__":
    main()
