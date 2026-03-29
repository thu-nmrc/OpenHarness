# Architecture | Framework Architecture Description

> This document is for Agent to reference when executing the harness framework tasks, to understand the design principles and operating mechanisms of the framework.

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Six Components Mapping](#six-components-mapping)
3. [Operating Process](#operating-process)
4. [File Responsibilities](#file-responsibilities)
5. [State Machine](#state-machine)
6. [Script Usage Quick Reference](#script-usage-quick-reference)

## Design Philosophy

This framework is built based on the core concept of Harness Engineering. The core problem that Harness Engineering solves is: how to enable AI to continuously do things right under long-term, complex, rollback-capable, and auditable conditions.

The core assumption of the framework is: each execution of Agent is a session with a limited duration, but tasks may span multiple sessions. Therefore, a "cross-session memory" mechanism is needed so that each execution can continue from the last breakpoint.

## Six Components Mapping

| Harness Engineering Load-bearing Component | Framework Implementation |
|---|---|
| Machine-verifiable completion contract | The "Completion Contract" table in mission.md + eval_criteria.md |
| Maintainable knowledge as system of record | playbook.md (execution knowledge) + progress.md (historical knowledge) |
| Provide Agent with senses and limbs | Tool list defined in playbook.md |
| Solve long-term memory loss | heartbeat.md (current state) + progress.md (historical trajectory) |
| External verification as feedback loop | eval_criteria.md + harness_eval.py |
| Constraint sandbox and entropy control | "Boundaries and Constraints" in mission.md + harness_cleanup.py |

## Operating Process

Each time the cron triggers, Agent should execute in the following order:

```
1. Run harness_boot.py → Check workspace status
2. Run harness_heartbeat.py start → Mark start of execution
3. Read mission.md → Understand goals and boundaries
4. Read heartbeat.md → Confirm where to continue from
5. Read playbook.md → Get execution steps
6. Continue executing steps in playbook from breakpoint
7. Upon completion → Run harness_heartbeat.py done
8. Run harness_eval.py → External verification
9. If all completed → harness_heartbeat.py mission_complete
10. If failed → harness_heartbeat.py fail
```

## File Responsibilities

| File | Author | Reader | Responsibility |
|------|------|------|------|
| mission.md | User | Agent | Defines "what to do" and "what counts as done" |
| playbook.md | User | Agent | Defines "how to do" steps |
| heartbeat.md | Framework scripts | Agent | Cross-session state recovery |
| progress.md | Framework scripts | Agent/User | Historical execution records |
| eval_criteria.md | User | Agent | Definition of verification criteria |
| cron_config.md | User | Framework scripts | Scheduling parameters |

## State Machine

```
idle → running → completed → idle (waiting for next trigger)
                ↘ failed → idle (waiting for retry)
                ↘ blocked (requires manual intervention)
Any state → mission_complete (task ended)
```

## Script Usage Quick Reference

```bash
# Initialize workspace
python3 harness_boot.py /workspace --init

# Check status
python3 harness_boot.py /workspace

# Mark start
python3 harness_heartbeat.py /workspace start

# Mark completion
python3 harness_heartbeat.py /workspace done --step "Step 2" --summary "Data collection completed"

# Mark failure
python3 harness_heartbeat.py /workspace fail --step "Step 1" --error "Network timeout"

# Mark blocked
python3 harness_heartbeat.py /workspace blocked --reason "API key required"

# Mark mission complete
python3 harness_heartbeat.py /workspace mission_complete

# Run verification
python3 harness_eval.py /workspace

# Run entropy control
python3 harness_cleanup.py /workspace --max-runs 50

# View cron configuration
python3 harness_setup_cron.py /workspace
```
