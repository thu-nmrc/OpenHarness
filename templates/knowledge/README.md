# Knowledge Directory (Layer 2)

> **Three-Layer Memory Architecture — Layer 2: Topic Files (On-Demand Loading)**
>
> This directory stores topic-specific knowledge files extracted from successful executions.
> Each file focuses on ONE topic and is loaded into context ONLY when the Agent encounters
> a task related to that topic.

## Rules

1. **One topic per file.** File name should be a short, descriptive slug (e.g., `api_auth_patterns.md`).
2. **Max 500 lines per file.** If a topic grows beyond this, split it into sub-topics.
3. **Pointer in heartbeat.md.** Every file here MUST have a corresponding row in `heartbeat.md > Knowledge Index`.
4. **Write discipline.** Only create/update a topic file AFTER `harness_eval.py` confirms the related execution succeeded.
5. **No raw logs.** This is distilled knowledge, not execution dumps. Raw logs belong in `logs/` (Layer 3).

## Example File Structure

```markdown
# API Authentication Patterns

## Confirmed Working Approach
- Bearer token in Authorization header
- Token refresh endpoint: POST /api/v2/auth/refresh

## Known Failure Modes
- 401 when token expires after 3600s
- Rate limit: 100 req/min per token

## Recommended Strategy
Refresh token proactively at 3000s mark to avoid mid-request failures.
```
