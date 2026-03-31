# Cron Config | Scheduling Configuration

> This file defines the automatic scheduling parameters for tasks.
> The framework sets the Agent's schedule cron jobs based on this configuration.

## Main Task Scheduling

<!-- ✏️ Fill in: Task execution frequency -->

| Parameter | Value | Description |
|------|-----|------|
| Schedule Type | `cron` | `cron` (precise time) or `interval` (fixed interval) |
| Cron Expression | `0 0 */2 * * *` | 6-field format: second minute hour day month week. Example = every 2 hours |
| Or: Interval Seconds | `7200` | Fill only when schedule type is interval |
| Repeat | `true` | `true` = continuous execution, `false` = execute only once |
| Expire | `[empty or 2026-04-01 00:00:00]` | Leave empty = never expires |
| Timezone | `Asia/Shanghai` | User's timezone |

## Task Prompt Template

<!-- ✏️ Fill in: The instruction Agent receives each time cron triggers -->

```
Read the following files and execute tasks according to the driving framework:

1. Read {workspace}/mission.md — Understand the task objectives
2. Read {workspace}/heartbeat.md — Restore last state
3. Read {workspace}/progress.md — Understand historical progress
4. Read {workspace}/playbook.md — Obtain execution steps
5. Continue execution from the breakpoint recorded in heartbeat
6. After completion:
   a. Read {workspace}/eval_criteria.md for validation
   b. Update {workspace}/heartbeat.md (status, progress, exceptions)
   c. Append records to {workspace}/progress.md
7. If all completion conditions are met, set heartbeat status to mission_complete
```

## Common cron Expression Quick Reference

| Scenario | cron Expression | Description |
|------|-----------|------|
| Execute every hour | `0 0 * * * *` | On the hour every hour |
| Execute every 2 hours | `0 0 */2 * * *` | On the hour every 2 hours |
| Every day at 8 AM | `0 0 8 * * *` | Every day at 08:00 |
| Once each morning and evening | `0 0 8,20 * * *` | At 08:00 and 20:00 |
| Every hour on weekdays | `0 0 9-18 * * 1-5` | Monday to Friday 9 AM to 6 PM |
| Every 30 minutes | `0 */30 * * * *` | Every 30 minutes |
| Every 15 minutes | `0 */15 * * * *` | Every 15 minutes |
| Every 5 minutes | `0 */5 * * * *` | Every 5 minutes (minimum recommended interval) |

---

> **Notes**:
> - Agent cron uses 6-field format: second minute hour day month week (Sunday=0)
> - Minimum repeat interval recommended is 5 minutes (300 seconds)
> - Expiration time format: yyyy-MM-dd HH:mm:ss
> - File paths in the prompt need to be adjusted according to the actual working directory
