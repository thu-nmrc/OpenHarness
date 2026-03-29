# Mission Contract | Mission Contract

> This document is the "constitution" of the entire Agent framework. It clearly defines "what to do" and "what counts as done."
> The Agent reads this file first every time it starts.

## 1. Mission Name

<!-- ✏️ Fill in: A one-sentence description of your mission -->
**Name**: `[Fill in the mission name here]`

## 2. Mission Objective

<!-- ✏️ Fill in: Clear, specific, unambiguous objective description -->
**Objective**:

```
[Fill in the mission objective here, for example:
Collect the official website price changes of competitors A, B, and C every morning at 8 AM,
generate a comparison report, and send it to the specified email.]
```

## 3. Done Definition

> This is the first critical component of the Agent engineering: machine-verifiable completion criteria.
> Each item must be verifiable by the Agent itself, not subjective judgments like "looks good."

<!-- ✏️ Fill in: List all machine-verifiable "done" conditions -->

| No. | Completion Condition | Verification Method | Mandatory/Optional |
|------|---------------------|--------------------|--------------------|
| 1 | `[e.g., Report file has been generated]` | `[e.g., Check if the file exists]` | Mandatory |
| 2 | `[e.g., Report contains data of 3 competitors]` | `[e.g., Parse report to check data count]` | Mandatory |
| 3 | `[e.g., No error logs]` | `[e.g., Check log files]` | Optional |

## 4. Boundaries and Constraints

<!-- ✏️ Fill in: What the Agent cannot do, risk boundaries -->

**Allowed Operations**:
- `[e.g., Read web pages, generate files, send messages]`

**Prohibited Operations**:
- `[e.g., Do not modify production databases]`
- `[e.g., Do not send unverified content]`

**Exception Escalation Rules**:
- `[e.g., Stop execution and notify user after 3 consecutive failures]`
- `[e.g., Skip site and log if captcha encountered]`

## 5. Execution Cycle

<!-- ✏️ Fill in: Task scheduling -->

| Parameter | Value |
|-----------|-------|
| Execution Frequency | `[e.g., Every hour / Daily at 8:00 / Every Monday]` |
| Max Single Execution Duration | `[e.g., 30 minutes]` |
| Total Mission Duration | `[e.g., Continuous / Until 2026-04-01]` |
| Timezone | `[e.g., Asia/Shanghai]` |

## 6. Output Definition

<!-- ✏️ Fill in: What should be produced each execution -->

| Output | Format | Storage Location | Description |
|--------|--------|------------------|-------------|
| `[e.g., Competitor report]` | `[e.g., Markdown]` | `[e.g., /output/reports/]` | `[e.g., Overwrite or append each time]` |

---

> **Checklist**: After filling out, confirm the following:
> - [ ] Each completion condition is verifiable by the Agent itself
> - [ ] Boundaries and constraints are clear with no ambiguity
> - [ ] Exception escalation rules are defined
> - [ ] Output format and location are specified
