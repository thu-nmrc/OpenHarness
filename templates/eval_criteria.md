# Eval Criteria | Validation Standards

> This document defines the specific standards for external validation loops.
> This reflects the fifth load-bearing component of Agent engineering: validation must be externalized into a loop, preventing the executor from self-certifying completion.

## Validation Principles

1. **Separation of executor and validator**: The prompt executing the task and the prompt validating the result must be independent.
2. **Each standard must be machine-checkable**: Subjective judgments like "looks good" are not accepted.
3. **Validation failure must have clear consequences**: Retry, skip, or escalate to human intervention.

## Validation Standards List

<!-- ✏️ Fill in: Expand from the completion contract in mission.md to define specific validation logic -->

### Standard 1: [Standard Name]

| Field | Value |
|-------|-------|
| Check Content | `[e.g., Whether the output file exists]` |
| Check Method | `[e.g., Check if path /output/report.md exists and is not empty]` |
| Passing Condition | `[e.g., File exists and size > 100 bytes]` |
| Failure Consequence | `[e.g., Mark as failed, retry next round]` |

### Standard 2: [Standard Name]

| Field | Value |
|-------|-------|
| Check Content | `[e.g., Data integrity]` |
| Check Method | `[e.g., Parse JSON and check if all required fields are complete]` |
| Passing Condition | `[e.g., All required fields are non-empty]` |
| Failure Consequence | `[e.g., Mark as partial success, record missing fields]` |

### Standard 3: [Standard Name]

| Field | Value |
|-------|-------|
| Check Content | `[e.g., Content quality]` |
| Check Method | `[e.g., Use LLM to score output content quality, threshold 70 points]` |
| Passing Condition | `[e.g., Score >= 70]` |
| Failure Consequence | `[e.g., Score < 50 redo, 50-70 mark warning]` |

<!-- ✏️ Add or remove standards as needed -->

## Validation Execution Rules

| Parameter | Value |
|-----------|-------|
| Validation Timing | `[e.g., Validate immediately after each execution round]` |
| Maximum Retry Count | `[e.g., 3 times]` |
| Retry Interval | `[e.g., 5 minutes]` |
| Action After All Pass | `[e.g., Update heartbeat status to completed]` |
| Action After Partial Pass | `[e.g., Record failed items, prioritize in next round]` |
| Action After All Fail | `[e.g., Mark blocked, wait for human intervention]` |

## Quality Grading (Optional)

<!-- ✏️ Define here if output quality grading is needed -->

| Grade | Condition | Handling Method |
|-------|-----------|-----------------|
| A (Excellent) | `[All standards passed, no warnings]` | `Deliver directly` |
| B (Pass) | `[Mandatory standards passed, optional standards failed]` | `Deliver but mark improvement items` |
| C (Needs Improvement) | `[Mandatory standards failed]` | `Retry or human intervention` |
| F (Fail) | `[Core standards failed]` | `Stop and escalate` |

---

> **Filling Tips**:
> - Validation standards should correspond one-to-one with the completion contract in mission.md
> - Prefer deterministic methods such as file checks and data parsing
> - LLM scoring should only be supplementary, not the sole validation method
> - Failure consequences must be clear: retry? skip? escalate?
