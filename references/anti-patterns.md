# Anti-Patterns | Common Mistakes to Avoid

> When executing Agent framework tasks, the following anti-patterns must be avoided.

## 1. Ignoring heartbeat, starting from scratch

**Wrong**: Each time execution starts from Step 1 without reading heartbeat.md.  
**Right**: First read heartbeat.md and continue from the recorded breakpoint.

## 2. Self-declaring completion

**Wrong**: Declaring "completed" after task execution without running external validation.  
**Right**: Must run harness_eval.py or verify each item according to eval_criteria.md.

## 3. Swallowing exceptions

**Wrong**: Silently skipping errors without recording them in heartbeat.md.  
**Right**: Use harness_heartbeat.py fail to record exceptions, so the next execution knows what happened.

## 4. Infinite retries without circuit breaker

**Wrong**: Repeatedly retrying the same step on failure without escalating to humans, burning API credits.  
**Right**: The circuit breaker auto-blocks after 3 consecutive failures. Do NOT bypass it. Mark as blocked and wait for manual intervention.

## 5. Modifying mission.md

**Wrong**: Agent modifies the completion contract in mission.md during execution.  
**Right**: mission.md is the user-defined "constitution"; Agent only reads it and does not write.

## 6. progress.md infinite expansion

**Wrong**: Never cleaning progress.md, letting it grow indefinitely and crowd out context.  
**Right**: Regularly run harness_cleanup.py to compress old records.

## 7. Treating playbook as a one-time prompt

**Wrong**: Reading playbook.md only on the first execution and relying on "memory" afterwards.  
**Right**: Read playbook.md anew each time to ensure the latest version is used.

## 8. Skipping boundary checks

**Wrong**: Not reading the "Boundaries and Constraints" in mission.md and performing prohibited operations.  
**Right**: Check boundary constraints before each execution to ensure no overreach.

## 9. Dumping raw logs into heartbeat.md (Layer 1)

**Wrong**: Writing verbose execution details, error tracebacks, or full API responses into heartbeat.md.  
**Right**: heartbeat.md is a pointer index. Keep it under 2KB. Write details to knowledge topics (L2) or execution stream (L3).

## 10. Reading execution stream fully

**Wrong**: Loading the entire `execution_stream.log` into context to "understand history".  
**Right**: Layer 3 is grep-only. Use `harness_memory.py search --query "keyword"` to find specific entries.

## 11. Bypassing the circuit breaker

**Wrong**: Manually resetting the circuit breaker without investigating the root cause.  
**Right**: Investigate why 3+ consecutive failures occurred, fix the root cause, THEN reset.

## 12. Running dream mode during active execution

**Wrong**: Calling `harness_dream.py` in the middle of an active task execution.  
**Right**: Dream mode is for idle periods only. Run it via a separate cron schedule during off-hours.

## 13. Creating knowledge topics without pointers

**Wrong**: Manually creating files in `knowledge/` without registering them in heartbeat.md.  
**Right**: Always use `harness_memory.py learn` which automatically creates both the topic file and the L1 pointer.

## 14. Ignoring cache-aware read order

**Wrong**: Reading heartbeat.md (dynamic) before mission.md (static), wasting prompt cache opportunities.  
**Right**: Read in order: mission.md -> eval_criteria.md -> playbook.md -> heartbeat.md -> knowledge topics.

## 15. Multi-agent workers modifying shared files

**Wrong**: Worker agents directly editing heartbeat.md, progress.md, or other shared workspace files.  
**Right**: Workers only read/write within their own `agents/{id}/inbox/` and `agents/{id}/outbox/` directories. The coordinator handles shared state.
